import io
import time
import asyncio
import aiohttp
import numpy as np
import soundfile as sf
import json
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, cli, WorkerOptions
from livekit.agents.tts import TTS, ChunkedStream, TTSCapabilities
from livekit.agents.tts.tts import AudioEmitter
from livekit.plugins import silero, openai

load_dotenv()

def get_session_config():
    try:
        with open("/tmp/session_config.json") as f:
            return json.load(f)
    except:
        return {"voice": "af_heart"}

class KokoroStream(ChunkedStream):
    def __init__(self, tts_instance, text: str, conn_options):
        super().__init__(tts=tts_instance, input_text=text, conn_options=conn_options)
        self._text = text
        self._tts_instance = tts_instance

    async def _run(self, output_emitter: AudioEmitter) -> None:
        t0 = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8002/v1/audio/speech",
                json={"input": self._text, "model": "kokoro",
                      "voice": self._tts_instance.voice},
            ) as resp:
                audio_bytes = await resp.read()
        t1 = time.time()
        print(f"[LATENCY] TTS Kokoro: {t1-t0:.3f}s for {len(self._text)} chars")

        buf = io.BytesIO(audio_bytes)
        audio_data, _ = sf.read(buf, dtype="float32")
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        pcm = (audio_data * 32767).astype(np.int16).tobytes()

        output_emitter.initialize(
            request_id="kokoro", sample_rate=24000,
            num_channels=1, mime_type="audio/pcm",
        )
        output_emitter.push(pcm)
        output_emitter.flush()
        output_emitter.end_input()
        print(f"[LATENCY] TTS total (incl push): {time.time()-t0:.3f}s")

class KokoroTTS(TTS):
    def __init__(self, voice: str = "af_heart"):
        super().__init__(
            capabilities=TTSCapabilities(streaming=False),
            sample_rate=24000, num_channels=1,
        )
        self.voice = voice

    def synthesize(self, text: str, *, conn_options=None, **kwargs) -> KokoroStream:
        return KokoroStream(self, text, conn_options=conn_options)

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    config = get_session_config()
    voice = config.get("voice", "af_heart")

    t_pipeline_start = {}

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
        tts=KokoroTTS(voice=voice),
    )

    @session.on("user_input_transcribed")
    def on_user_transcript(ev):
        if ev.is_final:
            t = time.time()
            t_pipeline_start['stt_done'] = t
            print(f"[LATENCY] STT done: transcript='{ev.transcript}'")
            asyncio.ensure_future(
                ctx.room.local_participant.publish_data(
                    f"You: {ev.transcript}".encode(), reliable=True))

    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        msg = ev.item
        if hasattr(msg, 'role') and msg.role == "assistant":
            text = getattr(msg, 'text_content', None) or str(getattr(msg, 'content', ''))
            if text:
                stt_done = t_pipeline_start.get('stt_done', 0)
                if stt_done:
                    print(f"[LATENCY] LLM done: {time.time()-stt_done:.3f}s after STT")
                asyncio.ensure_future(
                    ctx.room.local_participant.publish_data(
                        f"Agent: {text}".encode(), reliable=True))

    await session.start(
        room=ctx.room,
        agent=Agent(instructions="""
            You are a helpful voice assistant.
            Keep responses concise and conversational.
            Avoid markdown, bullet points, or special characters.
        """)
    )
    await session.generate_reply(
        instructions="Greet the user and ask how you can help."
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
