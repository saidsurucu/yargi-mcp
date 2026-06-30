# uyusmazlik_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

# The Uyuşmazlık Mahkemesi search site was rebuilt as an ASP.NET WebForms app.
# It now offers only a single free-text search with a scope selector; the old
# Bölüm / Uyuşmazlık Türü / Karar Sonucu / Esas-Karar year filters no longer exist.

UyusmazlikSearchScope = Literal["All", "EsasNo", "KararNo"]


class UyusmazlikSearchRequest(BaseModel):
    """Model for the Uyuşmazlık Mahkemesi search request."""
    icerik: str = Field("", description="Search text (txtSearch).")
    search_scope: UyusmazlikSearchScope = Field(
        "All",
        description="Search scope: 'All' (full text), 'EsasNo' (by case number), 'KararNo' (by decision number).",
    )
    case_sensitive: bool = Field(False, description="Whether the search is case sensitive (chkCaseSensitive).")
    page_number: int = Field(1, ge=1, description="Result page number (GridView pager).")


class UyusmazlikApiDecisionEntry(BaseModel):
    """A single decision row parsed from the Uyuşmazlık GridView results."""
    esas_sayisi: Optional[str] = Field(None, description="Case number (Esas No).")
    karar_sayisi: Optional[str] = Field(None, description="Decision number (Karar No).")
    karar_tarihi: Optional[str] = Field(None, description="Decision date (DD/MM/YYYY).")
    document_url: HttpUrl = Field(..., description="Full URL to the decision PDF document.")


class UyusmazlikSearchResponse(BaseModel):
    """Response model for Uyuşmazlık Mahkemesi search results."""
    decisions: List[UyusmazlikApiDecisionEntry]
    total_records_found: Optional[int] = Field(None, description="Total number of records found, if reported.")


class UyusmazlikDocumentMarkdown(BaseModel):
    """Model for an Uyuşmazlık decision document, containing Markdown content."""
    source_url: HttpUrl
    markdown_content: Optional[str] = Field(None, description="The decision PDF content converted to Markdown.")
