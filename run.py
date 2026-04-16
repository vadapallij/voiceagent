import uvicorn
from frontend import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000,
                ssl_keyfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.key",
                ssl_certfile="/home/ubuntu/voiceagent/daring-bohr.tail0f0633.ts.net.crt")
