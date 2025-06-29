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

    issuer = os.environ["CLERK_ISSUER"]                     # e.g. https://cool-app.clerk.accounts.dev
    auth = BearerAuthProvider(
        jwks_uri=f"{issuer}/.well-known/jwks.json",         # Clerk JWKS pattern
        issuer=issuer,
        audience=os.environ["CLERK_PUBLISHABLE_KEY"],       # PK appears in aud claim
        required_scopes=["yargi.read"],
    )
    return FastMCP(
        name="Yargı MCP – PROD", 
        auth=auth,
        instructions="MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK, Sayistay, Rekabet) with JWT authentication.",
        dependencies=["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
    )