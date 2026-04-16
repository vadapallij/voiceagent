import os
import subprocess
import tempfile
import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

SADTALKER_DIR = os.path.expanduser("~/SadTalker")
SADTALKER_PYTHON = os.path.join(SADTALKER_DIR, "sadtalker_env/bin/python3")
RESULTS_DIR = os.path.join(SADTALKER_DIR, "results")

class GenerateRequest(BaseModel):
    audio_path: str
    image_path: str

@app.post("/generate")
async def generate(req: GenerateRequest):
    cmd = [
        SADTALKER_PYTHON, "inference.py",
        "--driven_audio", req.audio_path,
        "--source_image", req.image_path,
        "--result_dir", RESULTS_DIR,
        "--still",
        "--preprocess", "crop",
        "--size", "256",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=SADTALKER_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode() + stderr.decode()

    # Find generated video path
    for line in output.split("\n"):
        if "The generated video is named:" in line:
            video_path = line.split("named:")[-1].strip()
            if os.path.exists(video_path):
                return JSONResponse({"video_path": video_path})

    return JSONResponse({"error": output}, status_code=500)

@app.get("/video")
async def get_video(path: str):
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4")
    return JSONResponse({"error": "not found"}, status_code=404)

app.mount("/static", StaticFiles(directory=os.path.expanduser("~/voiceagent/static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
