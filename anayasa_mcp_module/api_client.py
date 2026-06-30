# anayasa_mcp_module/api_client.py
# Low-level client for the new Anayasa Mahkemesi "Kararlar Bilgi Bankası" (KBB) JSON API.
#
# Both the Norm Denetimi host (normkararlarbilgibankasi.anayasa.gov.tr) and the
# Bireysel Başvuru host (kararlarbilgibankasi.anayasa.gov.tr) share the SAME
# backend, exposed at POST /api/core/public/search. The request differs only by
# the "kararTipi" discriminator:
#
#   {"kararTipi": "NormDenetimi", "query": "mülkiyet", "page": 1, "size": 10}
#     -> {"total": N, "page": 1, "data": [...summary records...], "page_size": 10}
#
#   {"kararTipi": "NormDenetimi", "id": "<uuid>", "page": 1, "size": 1}
#     -> data[0] additionally includes "icerik" = full decision HTML
#
# The previous HTML-scraping endpoints (/Ara, /ND/.., /BB/..) were retired when
# the sites were rebuilt as a single-page app; they now return HTTP 404.

import base64
import html as html_module
import io
import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote

import httpx
from bs4 import BeautifulSoup
from markitdown import MarkItDown

logger = logging.getLogger(__name__)

# Markdown pagination chunk size (characters), shared across AYM document tools.
DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000


def strip_html_text(value: Optional[str]) -> str:
    """Return plain text from a possibly-HTML field (e.g. kararKonusu)."""
    if not value:
        return ""
    text = BeautifulSoup(html_module.unescape(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def convert_icerik_to_markdown(icerik_html: Optional[str]) -> Optional[str]:
    """Convert the "icerik" decision HTML returned by the KBB API to Markdown.

    The icerik field is a self-contained HTML fragment (the rendered decision
    body). Scripts/styles are stripped before handing it to MarkItDown.
    """
    if not icerik_html:
        return None

    processed_html = html_module.unescape(icerik_html)
    soup = BeautifulSoup(processed_html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    body = soup.find("body")
    html_fragment = str(body) if body else str(soup)
    if not html_fragment.strip().lower().startswith(("<html", "<!doctype")):
        html_fragment = f'<html><head><meta charset="UTF-8"></head><body>{html_fragment}</body></html>'

    try:
        html_stream = io.BytesIO(html_fragment.encode("utf-8"))
        conversion_result = MarkItDown().convert(html_stream)
        return conversion_result.text_content
    except Exception as e:  # pragma: no cover - defensive
        logger.error("AnayasaApiClient: MarkItDown conversion error: %s", e)
        return None

# kararTipi discriminator values accepted by the API.
KARAR_TIPI_NORM = "NormDenetimi"
KARAR_TIPI_BIREYSEL = "BireyselBasvuru"

NORM_HOST = "https://normkararlarbilgibankasi.anayasa.gov.tr"
BIREYSEL_HOST = "https://kararlarbilgibankasi.anayasa.gov.tr"
SEARCH_PATH = "/api/core/public/search"

# Map kararTipi -> the host whose SPA can display the decision (cosmetic only;
# either host's API answers for any kararTipi).
_HOST_FOR_TIPI = {
    KARAR_TIPI_NORM: NORM_HOST,
    KARAR_TIPI_BIREYSEL: BIREYSEL_HOST,
}


def encode_document_token(uuid: str) -> str:
    """Encode a raw decision UUID into the base64url token the SPA uses in its URLs.

    The SPA addresses decisions as base64url("kbb:" + uuid) (no padding).
    """
    raw = f"kbb:{uuid}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_document_token(token: str) -> Optional[str]:
    """Decode a base64url SPA token back into the raw decision UUID.

    Returns None if the token is not a valid "kbb:<uuid>" token.
    """
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception:
        return None
    if decoded.startswith("kbb:"):
        return decoded[len("kbb:"):]
    return None


def build_document_url(karar_tipi: str, uuid: str) -> str:
    """Build a clickable SPA URL for a decision, used as its document_url."""
    host = _HOST_FOR_TIPI.get(karar_tipi, BIREYSEL_HOST)
    token = encode_document_token(uuid)
    return f"{host}/kbb/pages/search/{karar_tipi}?id={quote(token)}&type={karar_tipi}"


def parse_document_url(document_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract (karar_tipi, uuid) from a document URL.

    Handles the new SPA URLs (?id=<token>&type=<kararTipi>) and is lenient about
    older /ND/ and /BB/ style paths so historical references still resolve.
    Returns (None, None) if neither the type nor id can be determined.
    """
    parsed = urlparse(document_url)
    qs = parse_qs(parsed.query)

    karar_tipi = None
    type_param = qs.get("type", [None])[0]
    path = parsed.path or ""
    if type_param in (KARAR_TIPI_NORM, KARAR_TIPI_BIREYSEL):
        karar_tipi = type_param
    elif "/ND/" in path or "NormDenetimi" in path:
        karar_tipi = KARAR_TIPI_NORM
    elif "/BB/" in path or "BireyselBasvuru" in path:
        karar_tipi = KARAR_TIPI_BIREYSEL

    uuid = None
    id_param = qs.get("id", [None])[0]
    if id_param:
        # The id may be the raw uuid or the base64url SPA token.
        uuid = decode_document_token(id_param) or id_param

    return karar_tipi, uuid


class AnayasaApiClient:
    """Thin async wrapper around the KBB /api/core/public/search endpoint."""

    def __init__(self, request_timeout: float = 60.0):
        self.http_client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            timeout=request_timeout,
            verify=True,
            follow_redirects=True,
        )

    def _search_url(self, karar_tipi: str) -> str:
        host = _HOST_FOR_TIPI.get(karar_tipi, BIREYSEL_HOST)
        return f"{host}{SEARCH_PATH}"

    async def search(
        self,
        karar_tipi: str,
        query: str = "",
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """Run a list search and return the parsed JSON envelope.

        Envelope shape: {"total": int, "page": int, "data": [..], "page_size": int}.
        """
        body: Dict[str, Any] = {"kararTipi": karar_tipi, "page": page, "size": size}
        if query:
            body["query"] = query
        logger.info("AnayasaApiClient: search kararTipi=%s query=%r page=%s size=%s",
                    karar_tipi, query, page, size)
        response = await self.http_client.post(self._search_url(karar_tipi), json=body)
        response.raise_for_status()
        return response.json()

    async def get_decision(self, karar_tipi: str, uuid: str) -> Optional[Dict[str, Any]]:
        """Fetch a single decision record (including the "icerik" HTML) by UUID."""
        body = {"kararTipi": karar_tipi, "id": uuid, "page": 1, "size": 1}
        logger.info("AnayasaApiClient: get_decision kararTipi=%s id=%s", karar_tipi, uuid)
        response = await self.http_client.post(self._search_url(karar_tipi), json=body)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or []
        return data[0] if data else None

    async def close(self):
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("AnayasaApiClient: HTTP client session closed.")
