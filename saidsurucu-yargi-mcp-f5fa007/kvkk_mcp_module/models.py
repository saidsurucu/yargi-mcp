# kvkk_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any

class KvkkSearchRequest(BaseModel):
    """Model for KVKK (Personal Data Protection Authority) search request via Brave API."""
    keywords: str = Field(..., description="""
        Keywords to search for in KVKK decisions. 
        The search will automatically include 'site:kvkk.gov.tr "karar özeti"' to target KVKK decision summaries.
        Examples: "açık rıza", "veri güvenliği", "kişisel veri işleme"
    """)
    page: int = Field(1, ge=1, le=50, description="Page number for search results (1-50).")
    pageSize: int = Field(10, ge=1, le=10, description="Number of results per page (1-10).")

class KvkkDecisionSummary(BaseModel):
    """Model for a single KVKK decision summary from Brave search results."""
    title: Optional[str] = Field(None, description="Decision title from search results.")
    url: Optional[HttpUrl] = Field(None, description="URL to the KVKK decision page.")
    description: Optional[str] = Field(None, description="Brief description or snippet from search results.")
    decision_id: Optional[str] = Field(None, description="Value")
    publication_date: Optional[str] = Field(None, description="Value")
    decision_number: Optional[str] = Field(None, description="Value")

class KvkkSearchResult(BaseModel):
    """Model for the overall search result for KVKK decisions."""
    decisions: List[KvkkDecisionSummary] = Field(default_factory=list, description="List of KVKK decisions found.")
    total_results: Optional[int] = Field(None, description="Value")
    page: int = Field(1, description="Current page number of results.")
    pageSize: int = Field(10, description="Number of results per page.")
    query: Optional[str] = Field(None, description="The actual search query sent to Brave API.")

class KvkkDocumentMarkdown(BaseModel):
    """Model for KVKK decision document content converted to paginated Markdown."""
    source_url: HttpUrl = Field(description="URL of the original KVKK decision page.")
    title: Optional[str] = Field(None, description="Title of the KVKK decision.")
    decision_date: Optional[str] = Field(None, description="Decision date (Karar Tarihi).")
    decision_number: Optional[str] = Field(None, description="Decision number (Karar No).")
    subject_summary: Optional[str] = Field(None, description="Subject summary (Konu Özeti).")
    markdown_chunk: Optional[str] = Field(None, description="A 5,000 character chunk of the Markdown content.")
    current_page: int = Field(description="The current page number of the markdown chunk (1-indexed).")
    total_pages: int = Field(description="Total number of pages for the full markdown content.")
    is_paginated: bool = Field(description="True if the full markdown content is split into multiple pages.")
    error_message: Optional[str] = Field(None, description="Value")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }