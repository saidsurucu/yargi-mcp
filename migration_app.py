"""
Migration stub for the deprecated Yargı MCP endpoint.

Exposes a single tool that informs the MCP client the server has moved
and the user must update their configuration.

Entrypoint variable `app` is a FastMCP instance so it works with
Dokploy's FastMCP build pipeline (`fastmcp inspect`, `fastmcp run`).

Run with:
    fastmcp run migration_app.py:app --transport http --port 8000
"""

from starlette.responses import JSONResponse
from fastmcp import FastMCP

NEW_URL = "https://yargimcp.surucu.dev/mcp"

app = FastMCP(
    name="Yargı MCP (taşındı / moved)",
    instructions=(
        f"Bu Yargı MCP endpoint'i kullanımdan kaldırıldı. "
        f"Sunucu yeni adrese taşındı: {NEW_URL}. "
        f"Kullanıcıya MCP istemci ayarlarındaki sunucu URL'sini güncellemesini söyle."
    ),
)


@app.tool(
    description=(
        "DEPRECATED ENDPOINT — Yargı MCP sunucusu yeni adrese taşındı. "
        "Bu endpoint'teki eski araçlar (Yargıtay, Danıştay, Anayasa Mahkemesi, "
        "KVKK, BDDK, Rekabet Kurumu, Sayıştay, KİK, Emsal, Uyuşmazlık, GİB, "
        "Sigorta Tahkim, Bedesten vb.) artık burada çalışmıyor. "
        "Bu aracı çağırarak yeni sunucu adresini ve migrasyon talimatını al, "
        "ardından kullanıcıya MCP istemci (Claude Desktop, 5ire, ChatGPT vb.) "
        "ayarlarındaki sunucu URL'sini güncellemesi gerektiğini açıkça söyle."
    )
)
def migration_notice() -> dict:
    """Yargı MCP sunucusunun yeni adresini ve migrasyon talimatını döner."""
    return {
        "status": "moved",
        "new_url": NEW_URL,
        "message": (
            f"Yargı MCP sunucusu yeni adrese taşındı: {NEW_URL}\n\n"
            f"Lütfen MCP istemcinin (Claude Desktop, 5ire, ChatGPT vb.) "
            f"ayarlarındaki sunucu URL'sini yukarıdaki yeni adresle güncelleyin. "
            f"Mevcut endpoint artık kullanım dışıdır ve sadece bu uyarıyı döner."
        ),
    }


@app.custom_route("/health", methods=["GET"])
async def health(request):
    """Health check endpoint for monitoring services."""
    return JSONResponse({"status": "deprecated", "new_url": NEW_URL})
