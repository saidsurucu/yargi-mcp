# gib_mcp_module/models.py

from pydantic import BaseModel, Field
from typing import List, Optional


class GibSearchRequest(BaseModel):
    """
    Request model for searching GİB özelgeler (Turkish Revenue Administration tax rulings).

    GİB (Gelir İdaresi Başkanlığı) publishes official tax-ruling letters
    ("özelge") responding to taxpayer questions on VAT, income tax,
    corporate tax, stamp duty, and other tax matters. 18,000+ rulings
    are searchable via the public gib.gov.tr API.
    """
    keywords: str = Field("", description="Keywords searched across title, kanunNo and description (Turkish)")
    ozelgeNo: str = Field("", description="Exact özelge reference number (e.g., 'E-40247694-130-15524')")
    kanunNo: str = Field("", description="Law number filter, e.g. '3065' for KDV")
    kanunId: int = Field(0, description="Optional numeric law ID filter (0=ignore)")
    ozelgeStartDate: str = Field("", description="Start date YYYY-MM-DD or full ISO 8601")
    ozelgeEndDate: str = Field("", description="End date YYYY-MM-DD or full ISO 8601")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    pageSize: int = Field(10, ge=1, le=50, description="Results per page (1-50)")


class GibOzelgeSummary(BaseModel):
    """Summary of a single GİB özelge from search results (no full HTML)."""
    id: int = Field(..., description="Numeric özelge ID for document retrieval")
    ozelgeNo: Optional[str] = Field(None, description="Official ruling reference number")
    ozelgeTarih: Optional[str] = Field(None, description="Ruling date (ISO datetime)")
    title: Optional[str] = Field(None, description="Subject/title of the ruling")
    kanunNo: Optional[str] = Field(None, description="Law number (e.g., '3065')")
    kanunTitle: Optional[str] = Field(None, description="Law title (e.g., 'KATMA DEĞER VERGİSİ KANUNU')")
    siteLink: Optional[str] = Field(None, description="Direct URL to the ruling on gib.gov.tr")


class GibSearchResult(BaseModel):
    """Response model for GİB özelge search results."""
    ozelgeler: List[GibOzelgeSummary] = Field(default_factory=list, description="Matching özelge summaries")
    total_results: int = Field(0, description="Total number of matching özelgeler across all pages")
    total_pages: int = Field(0, description="Total number of pages for this query")
    current_page: int = Field(1, description="Current page (1-indexed)")
    page_size: int = Field(10, description="Results per page")


class GibDocumentMarkdown(BaseModel):
    """
    GİB özelge document converted to paginated Markdown.

    Long rulings are split into 5000-character chunks; request successive
    pages via page_number to read the full text.
    """
    ozelge_id: int = Field(..., description="Numeric özelge ID")
    ozelge_no: Optional[str] = Field(None, description="Official ruling reference number")
    title: Optional[str] = Field(None, description="Subject/title of the ruling")
    ozelge_tarih: Optional[str] = Field(None, description="Ruling date (ISO datetime)")
    kanun_title: Optional[str] = Field(None, description="Related law title")
    kanun_no: Optional[str] = Field(None, description="Related law number")
    site_link: Optional[str] = Field(None, description="Direct URL to the ruling on gib.gov.tr")
    markdown_chunk: Optional[str] = Field(None, description="Current 5000-character Markdown chunk")
    current_page: int = Field(1, description="Current page number (1-indexed)")
    total_pages: int = Field(0, description="Total pages for the full Markdown content")
    is_paginated: bool = Field(False, description="True if split across multiple pages")
    error_message: Optional[str] = Field(None, description="Populated when retrieval failed")
