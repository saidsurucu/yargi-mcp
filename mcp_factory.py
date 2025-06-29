import os
from functools import lru_cache
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider

@lru_cache
def create_app() -> FastMCP:
    """Return a FastMCP instance; Clerk JWT validation when ENABLE_AUTH=true."""
    if os.getenv("ENABLE_AUTH", "false").lower() != "true":
        return FastMCP(
            name="Yargı MCP – DEV",
            instructions="MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK, Sayistay, Rekabet).",
            dependencies=["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
        )

    # Public key'i environment variable'dan al, yoksa None
    public_key_pem = os.environ.get("CLERK_PUBLIC_KEY")
    
    if public_key_pem:
        # Eğer public key varsa, onu kullan (production)
        auth = BearerAuthProvider(
            public_key=public_key_pem,
            # issuer, audience ve required_scopes kontrollerini yapmıyoruz
        )
    else:
        # Public key yoksa JWKS endpoint kullan (development/fallback)
        clerk_issuer = os.environ.get("CLERK_ISSUER", "https://clerk.accounts.dev")
        auth = BearerAuthProvider(
            jwks_uri=f"{clerk_issuer}/.well-known/jwks.json",
        )
    return FastMCP(
        name="Yargı MCP – PROD", 
        auth=auth,
        instructions="MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK, Sayistay, Rekabet) with JWT authentication.",
        dependencies=["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
    )