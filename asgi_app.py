from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# MCPApp ekleniyor
from mcp_app import MCPApp  

app = FastAPI(
    title="Yargıtay MCP Main API",
    description="JWT + MCP entegrasyonlu ana FastAPI uygulaması",
    version="1.0.0"
)

# MCP alt uygulamasını mount et
mcp_app = MCPApp()
app.mount("/mcp", mcp_app.app)

# (Varsa diğer router importlarınız)
# from routers import xyz

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basit health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Yargıtay MCP API aktif",
        "docs_url": "/docs",
        "mcp_api": "/mcp"
    }

# Dev token alma örneği
@app.get("/dev-token")
async def dev_token():
    return {"token": "FAKE-JWT-TOKEN"}

# Secure endpoint örneği
@app.get("/secure-data")
async def secure_data():
    return {"data": "Bu alan JWT ile korunuyor"}
