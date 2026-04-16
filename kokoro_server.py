import io
import numpy as np
import soundfile as sf
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from kokoro import KPipeline

app = FastAPI()
pipeline = KPipeline(lang_code='a')

class TTSRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: str = "af_heart"
    speed: float = 1.0

@app.post("/v1/audio/speech")
async def synthesize(req: TTSRequest):
    audio_chunks = []
    for _, _, audio in pipeline(req.input, voice=req.voice, speed=req.speed):
        audio_chunks.append(audio)
    audio_data = np.concatenate(audio_chunks).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio_data, 24000, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return Response(content=buf.read(), media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
