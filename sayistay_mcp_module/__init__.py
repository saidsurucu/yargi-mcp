# sayistay_mcp_module/__init__.py

"""
Sayıştay (Turkish Court of Accounts) MCP Module

This module provides access to three types of Sayıştay decisions:
- Genel Kurul (General Assembly) decisions
- Temyiz Kurulu (Appeals Board) decisions  
- Daire (Chamber) decisions

The module handles ASP.NET WebForms authentication with CSRF tokens
and DataTables-based pagination for comprehensive decision search.
"""

from .client import SayistayApiClient
from .models import (
    # Genel Kurul models
    GenelKurulSearchRequest,
    GenelKurulSearchResponse,
    GenelKurulDecision,
    
    # Temyiz Kurulu models
    TemyizKuruluSearchRequest, 
    TemyizKuruluSearchResponse,
    TemyizKuruluDecision,
    
    # Daire models
    DaireSearchRequest,
    DaireSearchResponse,
    DaireDecision,
    
    # Document models
    SayistayDocumentMarkdown
)
from .enums import (
    DaireEnum,
    KamuIdaresiTuruEnum,
    WebKararKonusuEnum
)

__all__ = [
    "SayistayApiClient",
    "GenelKurulSearchRequest",
    "GenelKurulSearchResponse", 
    "GenelKurulDecision",
    "TemyizKuruluSearchRequest",
    "TemyizKuruluSearchResponse",
    "TemyizKuruluDecision",
    "DaireSearchRequest",
    "DaireSearchResponse",
    "DaireDecision",
    "SayistayDocumentMarkdown",
    "DaireEnum",
    "KamuIdaresiTuruEnum",
    "WebKararKonusuEnum"
]