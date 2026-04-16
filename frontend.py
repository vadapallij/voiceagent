import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from livekit.api import AccessToken, VideoGrants
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "devsecret_minimum32chars_xxxxxxxxxxx")
PUBLIC_IP = "100.124.21.88"

app.mount("/static", StaticFiles(directory="/home/ubuntu/voiceagent/static"), name="static")

AVATARS = ["happy.png", "people_0.png", "art_0.png", "full_body_1.png"]
VOICES = ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael"]

@app.get("/token")
async def get_token(room: str = "voice-room", username: str = "user"):
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(username)
    token.with_name(username)
    token.with_grants(VideoGrants(room_join=True, room=room))
    return JSONResponse({"token": token.to_jwt(), "url": f"wss://daring-bohr.tail0f0633.ts.net:3000"})

@app.get("/", response_class=HTMLResponse)
async def index():
    avatar_html = ""
    for av in AVATARS:
        name = av.replace(".png","").replace(".jpeg","")
        avatar_html += f'<div class="avatar-card" onclick="selectAvatar(\'{av}\', this)"><img src="/static/avatars/{av}"><span>{name}</span></div>\n'

    voice_options = ""
    for v in VOICES:
        voice_options += f'<option value="{v}">{v}</option>\n'

    return f"""
<!DOCTYPE html>
<html>
<head>
  <title>Voice Agent</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@1.15.0/dist/livekit-client.umd.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: sans-serif; background: #0f0f1a; color: white; min-height: 100vh; padding: 20px; }}
    h1 {{ text-align: center; margin-bottom: 24px; font-size: 1.8rem; color: #4ecca3; }}
    .setup-panel {{ max-width: 800px; margin: 0 auto; }}
    .section-label {{ font-size: 0.9rem; opacity: 0.6; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
    .avatar-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
    .avatar-card {{ border: 2px solid #333; border-radius: 8px; padding: 8px; cursor: pointer; text-align: center; transition: all 0.2s; }}
    .avatar-card:hover {{ border-color: #4ecca3; }}
    .avatar-card.selected {{ border-color: #4ecca3; background: #1a2a2a; }}
    .avatar-card img {{ width: 100%; height: 120px; object-fit: cover; border-radius: 4px; }}
    .avatar-card span {{ font-size: 0.75rem; opacity: 0.7; display: block; margin-top: 4px; }}
    .voice-row {{ display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }}
    select {{ background: #1a1a2e; color: white; border: 1px solid #333; padding: 10px 16px; border-radius: 6px; font-size: 1rem; cursor: pointer; }}
    select:focus {{ outline: none; border-color: #4ecca3; }}
    #startBtn {{ display: block; width: 100%; padding: 14px; background: #4ecca3; color: #0f0f1a; font-size: 1.1rem; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin-bottom: 24px; }}
    #startBtn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    #stopBtn {{ display: none; width: 100%; padding: 14px; background: #e94560; color: white; font-size: 1.1rem; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin-bottom: 24px; }}
    .session-panel {{ display: none; max-width: 800px; margin: 0 auto; }}
    .session-layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .avatar-display {{ background: #1a1a2e; border-radius: 12px; overflow: hidden; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; }}
    .avatar-display video {{ width: 100%; height: 100%; object-fit: cover; }}
    .avatar-display img {{ width: 100%; height: 100%; object-fit: cover; }}
    .transcript-box {{ background: #1a1a2e; border-radius: 12px; padding: 16px; height: 100%; min-height: 250px; overflow-y: auto; }}
    .transcript-box p {{ margin-bottom: 10px; line-height: 1.5; }}
    .transcript-box .you {{ color: #7eb8f7; }}
    .transcript-box .agent {{ color: #4ecca3; }}
    #status {{ text-align: center; opacity: 0.6; font-size: 0.9rem; margin-bottom: 16px; }}
    .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #4ecca3; margin: 0 2px; animation: bounce 1s infinite; }}
    .dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .dot:nth-child(3) {{ animation-delay: 0.4s; }}
    @keyframes bounce {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}} }}
    #dots {{ display: none; text-align: center; margin-bottom: 10px; }}
  </style>
</head>
<body>
  <h1>🎙️ Voice Agent</h1>

  <div class="setup-panel" id="setupPanel">
    <div class="section-label">Choose Avatar</div>
    <div class="avatar-grid">{avatar_html}</div>

    <div class="section-label">Choose Voice</div>
    <div class="voice-row">
      <select id="voiceSelect">{voice_options}</select>
    </div>

    <button id="startBtn" onclick="startSession()" disabled>Select an avatar to start</button>
  </div>

  <div class="session-panel" id="sessionPanel">
    <div id="status">Connecting...</div>
    <div id="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
    <div class="session-layout">
      <div class="avatar-display" id="avatarDisplay">
        <img id="avatarImg" src="">
      </div>
      <div class="transcript-box" id="transcriptBox">
        <p style="opacity:0.4">Conversation will appear here...</p>
      </div>
    </div>
    <button id="stopBtn" onclick="stopSession()">Disconnect</button>
  </div>

  <script>
    let room = null;
    let selectedAvatar = null;
    let selectedVoice = 'af_heart';

    function selectAvatar(name, el) {{
      document.querySelectorAll('.avatar-card').forEach(c => c.classList.remove('selected'));
      el.classList.add('selected');
      selectedAvatar = name;
      document.getElementById('startBtn').disabled = false;
      document.getElementById('startBtn').textContent = 'Start Session';
    }}

    document.getElementById('voiceSelect').addEventListener('change', e => {{
      selectedVoice = e.target.value;
    }});

    async function startSession() {{
      const roomName = 'voice-' + Date.now();
      const res = await fetch('/token?room=' + roomName + '&username=user');
      const {{ token, url }} = await res.json();

      // Tell agent which avatar and voice to use
      await fetch('/session-config', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ avatar: selectedAvatar, voice: selectedVoice, room: roomName }})
      }});

      room = new LivekitClient.Room();

      room.on(LivekitClient.RoomEvent.Connected, () => {{
        document.getElementById('status').textContent = 'Connected — start speaking!';
        document.getElementById('stopBtn').style.display = 'block';
        document.getElementById('avatarImg').src = '/static/avatars/' + selectedAvatar;
      }});

      room.on(LivekitClient.RoomEvent.Disconnected, () => {{
        document.getElementById('setupPanel').style.display = 'block';
        document.getElementById('sessionPanel').style.display = 'none';
      }});

      room.on(LivekitClient.RoomEvent.ActiveSpeakersChanged, (speakers) => {{
        document.getElementById('dots').style.display = speakers.length > 0 ? 'block' : 'none';
      }});

      room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {{
        if (track.kind === 'audio') {{
          const el = track.attach();
          document.body.appendChild(el);
          el.play();
        }}
        if (track.kind === 'video') {{
          const videoEl = track.attach();
          videoEl.style.width = '100%';
          videoEl.style.height = '100%';
          videoEl.style.objectFit = 'cover';
          const display = document.getElementById('avatarDisplay');
          display.innerHTML = '';
          display.appendChild(videoEl);
          videoEl.play();
        }}
      }});

      room.on(LivekitClient.RoomEvent.DataReceived, (data) => {{
        const text = new TextDecoder().decode(data);
        const box = document.getElementById('transcriptBox');
        if (box.querySelector('p[style]')) box.innerHTML = '';
        const p = document.createElement('p');
        if (text.startsWith('You:')) p.className = 'you';
        else if (text.startsWith('Agent:')) p.className = 'agent';
        p.textContent = text;
        box.appendChild(p);
        box.scrollTop = box.scrollHeight;
      }});

      await room.connect(url, token);
      await room.localParticipant.setMicrophoneEnabled(true);

      document.getElementById('setupPanel').style.display = 'none';
      document.getElementById('sessionPanel').style.display = 'block';
    }}

    async function stopSession() {{
      if (room) await room.disconnect();
    }}
  </script>
</body>
</html>
"""

@app.post("/session-config")
async def session_config(config: dict):
    # Write config for agent to pick up
    import json
    with open("/tmp/session_config.json", "w") as f:
        json.dump(config, f)
    return JSONResponse({"ok": True})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000,
                ssl_keyfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.key",
                ssl_certfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.crt")

import asyncio
import websockets
from fastapi import WebSocket

LIVEKIT_WS = "ws://100.124.21.88:7880"

@app.websocket("/rtc")
async def ws_proxy(client_ws: WebSocket):
    await client_ws.accept()
    query = client_ws.scope.get("query_string", b"").decode()
    target = f"{LIVEKIT_WS}/rtc?{query}"
    async with websockets.connect(target) as server_ws:
        async def c2s():
            try:
                async for msg in client_ws.iter_bytes():
                    await server_ws.send(msg)
            except Exception:
                pass
        async def s2c():
            try:
                async for msg in server_ws:
                    await client_ws.send_bytes(msg if isinstance(msg, bytes) else msg.encode())
            except Exception:
                pass
        await asyncio.gather(c2s(), s2c())
