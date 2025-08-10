# mcp_app.py
from fastapi import FastAPI
from yargitay_mcp_module.client import YargitayOfficialApiClient
from yargitay_mcp_module.models import YargitayDetailedSearchRequest

class MCPApp:
    def __init__(self):
        self.app = FastAPI(
            title="Yargıtay MCP API",
            description="Yargıtay karar arama ve doküman indirme",
            version="1.0.0"
        )
        self.client = YargitayOfficialApiClient()

        # Karar arama endpointi
        @self.app.post("/search")
        async def search_decisions(request: YargitayDetailedSearchRequest):
            return await self.client.search_detailed_decisions(request)

        # Karar metni (Markdown) endpointi
        @self.app.get("/document/{id}")
        async def get_document(id: str):
            return await self.client.get_decision_document_as_markdown(id)

        # Kapatma sırasında HTTPX oturumunu kapat
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self.client.close_client_session()
