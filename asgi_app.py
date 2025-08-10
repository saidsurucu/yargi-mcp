from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from yargitay_mcp_module import MCPApp   # ✅ Doğru paket adı
import os, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

app = FastAPI(
    title="Yargıtay MCP API",
    description="Web UI + JWT Auth + MCP API",
    version="1.1.0"
)

# MCP API mount
mcp_app = MCPApp()
app.mount("/mcp", mcp_app.app)

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {
        "message": "Yargıtay MCP API aktif",
        "docs_url": "/docs",
        "mcp_api": "/mcp"
    }

@app.get("/dev-token")
def dev_token():
    payload = {
        "sub": "test-user",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "scope": "yargi.read yargi.search"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token}

@app.get("/secure-data")
def secure_data(user=Depends(verify_token)):
    return {"message": "Giriş başarılı!", "decoded": user}
