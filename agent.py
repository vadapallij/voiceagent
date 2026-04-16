import io
import aiohttp
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, cli, WorkerOptions
from livekit.agents.tts import TTS, ChunkedStream, TTSCapabilities
from livekit.agents.tts.tts import AudioEmitter
from livekit.plugins import silero, openai

load_dotenv()

class KokoroStream(ChunkedStream):
    def __init__(self, tts_instance, text: str, conn_options):
        super().__init__(tts=tts_instance, input_text=text, conn_options=conn_options)
        self._text = text

    async def _run(self, output_emitter: AudioEmitter) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8002/v1/audio/speech",
                json={"input": self._text, "model": "kokoro", "voice": "af_heart"},
            ) as resp:
                audio_bytes = await resp.read()

        buf = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(buf, dtype="float32")

        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)

        pcm = (audio_data * 32767).astype(np.int16).tobytes()

        output_emitter.initialize(
            request_id="kokoro",
            sample_rate=24000,
            num_channels=1,
            mime_type="audio/pcm",
        )
        output_emitter.push(pcm)
        output_emitter.flush()
        output_emitter.end_input()

class KokoroTTS(TTS):
    def __init__(self):
        super().__init__(
            capabilities=TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )

    def synthesize(self, text: str, *, conn_options=None, **kwargs) -> KokoroStream:
        return KokoroStream(self, text, conn_options=conn_options)

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(
            base_url="http://localhost:8001/v1",
            model="Systran/faster-whisper-medium",
            api_key="dummy",
        ),
        llm=openai.LLM(
            base_url="http://localhost:8000/v1",
            model="Qwen/Qwen2.5-14B-Instruct",
            api_key="dummy",
        ),
        tts=KokoroTTS(),
    )

    await session.start(
        room=ctx.room,
        agent=Agent(instructions="""
            You are a helpful voice assistant.
            Keep responses concise and conversational.
            Avoid markdown, bullet points, or special characters.
        """)
    )

    # listen for transcripts
    @session.on("user_speech_committed")
    def on_user_speech(ev):
        import asyncio
        asyncio.ensure_future(ctx.room.local_participant.publish_data(
            f"You: {ev.user_transcript}".encode(), reliable=True
        ))

    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        import asyncio
        asyncio.ensure_future(ctx.room.local_participant.publish_data(
            f"Agent: {ev.agent_transcript}".encode(), reliable=True
        ))

    await session.generate_reply(
        instructions="Greet the user and ask how you can help."
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
# Add this before cli.run_app - already handled above
