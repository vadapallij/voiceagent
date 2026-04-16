import os
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from livekit.api import AccessToken, VideoGrants
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "devsecret_minimum32chars_xxxxxxxxxxx")
LIVEKIT_WS = "ws://100.124.21.88:7880"
PUBLIC_HTTPS = "wss://daring-bohr.tail0f0633.ts.net:3000"

@app.get("/token")
async def get_token(room: str = "voice-room", username: str = "user"):
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(username)
    token.with_name(username)
    token.with_grants(VideoGrants(room_join=True, room=room))
    return JSONResponse({"token": token.to_jwt(), "url": PUBLIC_HTTPS})

@app.websocket("/rtc")
async def ws_proxy(client_ws: WebSocket):
    await client_ws.accept()
    query = client_ws.scope.get("query_string", b"").decode()
    target = f"{LIVEKIT_WS}/rtc?{query}"
    async with websockets.connect(target) as server_ws:
        async def client_to_server():
            try:
                async for msg in client_ws.iter_bytes():
                    await server_ws.send(msg)
            except Exception:
                pass

        async def server_to_client():
            try:
                async for msg in server_ws:
                    await client_ws.send_bytes(msg if isinstance(msg, bytes) else msg.encode())
            except Exception:
                pass

        await asyncio.gather(client_to_server(), server_to_client())

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Voice Agent</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@1.15.0/dist/livekit-client.umd.min.js"></script>
  <style>
    body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #1a1a2e; color: white; }
    h1 { font-size: 2rem; margin-bottom: 2rem; }
    button { padding: 1rem 2rem; font-size: 1.2rem; border: none; border-radius: 8px; cursor: pointer; margin: 0.5rem; }
    #connectBtn { background: #4ecca3; color: #1a1a2e; font-weight: bold; }
    #disconnectBtn { background: #e94560; color: white; display: none; }
    #status { margin-top: 1rem; font-size: 1rem; opacity: 0.7; }
    #transcript { margin-top: 2rem; max-width: 600px; text-align: center; font-size: 1.1rem; min-height: 60px; }
    .dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #4ecca3; margin: 0 3px; animation: bounce 1s infinite; }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }
    #dots { display: none; }
  </style>
</head>
<body>
  <h1>🎙️ Voice Agent</h1>
  <button id="connectBtn" onclick="connect()">Connect</button>
  <button id="disconnectBtn" onclick="disconnect()">Disconnect</button>
  <div id="status">Not connected</div>
  <div id="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
  <div id="transcript"></div>
  <script>
    let room = null;
    async function connect() {
      const res = await fetch('/token?room=voice-room&username=user');
      const { token, url } = await res.json();
      room = new LivekitClient.Room();
      room.on(LivekitClient.RoomEvent.Connected, () => {
        document.getElementById('status').textContent = 'Connected — start speaking!';
        document.getElementById('connectBtn').style.display = 'none';
        document.getElementById('disconnectBtn').style.display = 'inline-block';
      });
      room.on(LivekitClient.RoomEvent.Disconnected, () => {
        document.getElementById('status').textContent = 'Disconnected';
        document.getElementById('connectBtn').style.display = 'inline-block';
        document.getElementById('disconnectBtn').style.display = 'none';
        document.getElementById('dots').style.display = 'none';
      });
      room.on(LivekitClient.RoomEvent.ActiveSpeakersChanged, (speakers) => {
        document.getElementById('dots').style.display = speakers.length > 0 ? 'block' : 'none';
      });
      room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === "audio") {
          const audioEl = track.attach();
          document.body.appendChild(audioEl);
          audioEl.play();
        }
      });
      room.on(LivekitClient.RoomEvent.DataReceived, (data) => {
        document.getElementById('transcript').textContent = new TextDecoder().decode(data);
      });
      await room.connect(url, token);
      await room.localParticipant.setMicrophoneEnabled(true);
    }
    async function disconnect() {
      if (room) await room.disconnect();
    }
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000,
                ssl_keyfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.key",
                ssl_certfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.crt")
