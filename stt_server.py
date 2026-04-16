import io
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import soundfile as sf
import numpy as np
from typing import Optional

app = FastAPI()

print("Loading Whisper model on CPU...")
whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
print("Whisper ready.")

@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    contents = await file.read()
    audio_buf = io.BytesIO(contents)

    try:
        audio_data, sample_rate = sf.read(audio_buf)
    except Exception:
        audio_data = np.frombuffer(contents, dtype=np.int16).astype(np.float32) / 32768.0

    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)

    # CRITICAL: must be float32 for Silero VAD
    audio_data = audio_data.astype(np.float32)

    segments, info = whisper_model.transcribe(
        audio_data,
        language=language,
        beam_size=5,
        vad_filter=False,  # disable VAD in whisper, LiveKit handles it
    )

    transcript = " ".join([seg.text for seg in segments]).strip()
    return JSONResponse({"text": transcript})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
