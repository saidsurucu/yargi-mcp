# bddk_mcp_module/models.py

from pydantic import BaseModel, Field
from typing import List, Optional

class BddkSearchRequest(BaseModel):
    """
    Request model for searching BDDK decisions via Tavily API.
    
    BDDK (Bankacılık Düzenleme ve Denetleme Kurumu) is Turkey's Banking
    Regulation and Supervision Agency responsible for banking licenses,
    electronic money institutions, and financial regulations.
    """
    keywords: str = Field(..., description="Search keywords in Turkish")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    pageSize: int = Field(10, ge=1, le=50, description="Results per page (1-50)")

class BddkDecisionSummary(BaseModel):
    """Summary of a BDDK decision from search results."""
    title: str = Field(..., description="Decision title")
    document_id: str = Field(..., description="BDDK document ID (e.g., '310')")
    content: str = Field(..., description="Decision summary/excerpt")

class BddkSearchResult(BaseModel):
    """Response model for BDDK decision search results."""
    decisions: List[BddkDecisionSummary] = Field(
        default_factory=list, 
        description="List of matching BDDK decisions"
    )
    total_results: int = Field(0, description="Total number of results")
    page: int = Field(1, description="Current page number")
    pageSize: int = Field(10, description="Results per page")

class BddkDocumentMarkdown(BaseModel):
    """
    BDDK decision document converted to Markdown format.
    
    Supports paginated content for long documents (5000 chars per page).
    """
    document_id: str = Field(..., description="BDDK document ID")
    markdown_content: str = Field("", description="Document content in Markdown")
    page_number: int = Field(1, description="Current page number")
    total_pages: int = Field(1, description="Total number of pages")