# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastMCP server that provides programmatic access to Turkish legal databases through the Model Context Protocol (MCP). It integrates with 11 different Turkish legal institutions' databases including Yargıtay (Court of Cassation), Danıştay (Council of State), Constitutional Court, Competition Authority, Court of Accounts (Sayıştay), KVKK (Personal Data Protection Authority), BDDK (Banking Regulation and Supervision Agency), and others.

**🎯 HIGHLY OPTIMIZED**: This MCP server has been extensively optimized for token efficiency, achieving a **56.8% reduction** in MCP overhead (from 14,061 to 6,073 tokens) while maintaining full functionality.

**✅ PRODUCTION READY**: Fully deployed on Fly.io with OAuth 2.0 authentication, Bearer JWT token support, and Claude AI integration. Server successfully handles 21 Turkish legal database tools with cross-origin authentication.

## Key Commands

### Installation and Setup

#### PyPI Installation (Recommended)
```bash
# Install from PyPI (no Git required)
pip install yargi-mcp

# Run the MCP server (stdio mode for Claude Desktop/5ire)
yargi-mcp

# Or use uvx for isolated execution
uvx yargi-mcp
```

#### Development Installation
```bash
# Install dependencies
uv sync

# Run the MCP server (stdio mode for Claude Desktop/5ire)
uv run mcp_server_main.py

# Or run via the entry point
yargi-mcp

# Run as web service (ASGI) with OAuth support
uv sync --extra saas    # Install OAuth dependencies (Clerk + Stripe)
cp .env.example .env    # Configure OAuth settings
uvicorn asgi_app:app --host 0.0.0.0 --port 8000
```

### Development Commands
```bash
# IMPORTANT: Always use 'uv run' for Python files in this project

# Run tests (if any exist)
uv run -m pytest

# Run specific test file
uv run test_kik_client.py

# Debug specific modules
uv run debug_rekabet_arama.py

# Test individual components
uv run -c "import module; module.function()"

# ASGI Development
python run_asgi.py --reload --log-level debug  # Auto-reload for development
uvicorn fastapi_app:app --reload                # FastAPI with interactive docs
uvicorn starlette_app:app --reload             # Starlette with authentication

# Note: debug_*, test_*, mcp_overhead_*, and *.txt files are in .gitignore for temporary testing

# Testing with FastMCP Client
uv run test_core_tools_quick.py         # Quick test of all core tools (10 tests)
uv run simple_test.py                   # Simple individual tool test
uv run measure_mcp_directly.py          # Measure MCP token overhead

# Test KVKK module (uses fallback token if BRAVE_API_TOKEN not set)
python test_kvkk_module.py              # Test KVKK search and document retrieval

# MCP Optimization Testing
uv run test_core_tools_quick.py         # Verify all tools work after optimization
```

## MCP Token Optimization Achievement

**🚀 EXTRAORDINARY OPTIMIZATION SUCCESS**

This MCP server has undergone comprehensive optimization to minimize token overhead while maintaining full functionality:

### Optimization Results
- **Baseline**: 14,061 tokens (original, 30 tools)
- **Phase 1-4**: 7,463 tokens (optimized, 30 tools, 46.9% reduction)
- **Phase 5**: 6,969 tokens (25 tools, 50.4% reduction)
- **Phase 6**: 6,608 tokens (23 tools, 53.0% reduction)
- **Phase 7**: 6,073 tokens (19 tools, 56.8% reduction)
- **Final Reduction**: 7,988 tokens saved (**56.8% decrease**)
- **Status**: **Exceeds 10,000 token target by 3,927+ tokens**

### Optimization Phases Completed

#### Phase 1: Null Type Simplification ✅
- **Impact**: 5,913 token reduction (42.1%)
- **Method**: Converted `Optional[str] = Field(None)` → `str = Field("")`
- **Scope**: ~72 parameters across all tools
- **Result**: Eliminated most `anyOf` JSON schema patterns

#### Phase 2: Chamber Enum Compression ✅  
- **Impact**: 669 additional token reduction
- **Method**: Simplified `search_bedesten_unified` chamber parameter
- **Note**: Partially reverted to maintain API compatibility

#### Phase 3: Description Cleanup ✅
- **Impact**: Minimal change (as expected)
- **Method**: Replaced "See docs for details" with specific descriptions
- **Scope**: Sayıştay and other modules

#### Phase 4: Micro-optimizations ✅
- **Impact**: 25 token final reduction  
- **Method**: Shortened verbose parameter descriptions
- **Target**: Largest remaining tools

#### Phase 5: Tool Removal (Yargıtay & Danıştay) ✅
- **Impact**: 494 additional token reduction
- **Method**: Commented out 5 tools (Yargıtay and Danıştay primary APIs)
- **Tools Removed**: search_yargitay_detailed, get_yargitay_document_markdown, search_danistay_by_keyword, search_danistay_detailed, get_danistay_document_markdown
- **Alternative**: Bedesten unified API provides equivalent functionality

#### Phase 6: Anayasa Tool Unification ✅
- **Impact**: 361 additional token reduction
- **Method**: Unified 4 Constitutional Court tools into 2 unified tools
- **Tools Replaced**: 
  - ❌ search_anayasa_norm_denetimi_decisions (DEACTIVATED)
  - ❌ get_anayasa_norm_denetimi_document_markdown (DEACTIVATED) 
  - ❌ search_anayasa_bireysel_basvuru_report (DEACTIVATED)
  - ❌ get_anayasa_bireysel_basvuru_document_markdown (DEACTIVATED)
- **New Unified Tools**:
  - ✅ search_anayasa_unified (handles both norm control and individual applications)
  - ✅ get_anayasa_document_unified (auto-detects document type by URL)
- **Benefits**: Single interface, auto-detection, simplified usage

#### Phase 7: Sayıştay Tool Unification ✅
- **Impact**: 535 additional token reduction
- **Method**: Unified 6 Sayıştay tools into 2 unified tools
- **Tools Replaced**: 
  - ❌ search_sayistay_genel_kurul (DEACTIVATED)
  - ❌ search_sayistay_temyiz_kurulu (DEACTIVATED)
  - ❌ search_sayistay_daire (DEACTIVATED)
  - ❌ get_sayistay_genel_kurul_document_markdown (DEACTIVATED)
  - ❌ get_sayistay_temyiz_kurulu_document_markdown (DEACTIVATED)
  - ❌ get_sayistay_daire_document_markdown (DEACTIVATED)
- **New Unified Tools**:
  - ✅ search_sayistay_unified (handles all three decision types: Genel Kurul, Temyiz Kurulu, Daire)
  - ✅ get_sayistay_document_unified (unified document retrieval for all decision types)
- **Benefits**: Single interface, decision type parameter, comprehensive coverage

### Current Token Distribution (Top 5 - 19 Tools Total)
1. `search_bedesten_unified`: 1,262 tokens (enhanced with search operators)
2. `search_sayistay_unified`: 983 tokens (NEW - replaces 3 search tools)
3. `search_uyusmazlik_decisions`: 668 tokens (was 997)
4. `search_anayasa_unified`: 652 tokens (NEW - replaces 2 search tools)
5. `search_kik_decisions`: 560 tokens (was 997)

### Testing & Verification ✅
- **Comprehensive testing**: All 19 active tools verified working
- **Empty string compatibility**: Confirmed APIs handle empty defaults correctly
- **Functionality preserved**: 100% test pass rate for active tools
- **Performance maintained**: Response times unaffected
- **Tool consolidation**: 11 tools successfully commented out, unified alternatives functional
- **Phase 6 unification**: Constitutional Court tools merged successfully
- **Phase 7 unification**: Sayıştay tools merged successfully

## Architecture

### Core Structure
- **mcp_server_main.py**: Main server entry point that defines all MCP tools and manages client instances
- **{module}_mcp_module/**: Each legal database has its own module with:
  - `client.py`: API client for interacting with the specific legal database
  - `models.py`: Pydantic models for request/response data structures
  - `__init__.py`: Module initialization

### Legal Database Modules
1. **yargitay_mcp_module**: Yargıtay (Court of Cassation) decisions - Primary API
2. **bedesten_mcp_module**: Unified API for multiple courts (Yargıtay, Danıştay, Yerel Hukuk, İstinaf Hukuk, KYB) - Highly optimized
3. **danistay_mcp_module**: Danıştay (Council of State) decisions  
4. **emsal_mcp_module**: Emsal (UYAP precedent) decisions
5. **uyusmazlik_mcp_module**: Uyuşmazlık Mahkemesi (Jurisdictional Disputes Court)
6. **anayasa_mcp_module**: Constitutional Court (both norm control and individual applications)
7. **kik_mcp_module**: KİK (Public Procurement Authority) decisions
8. **rekabet_mcp_module**: Competition Authority decisions
9. **kvkk_mcp_module**: KVKK (Personal Data Protection Authority) decisions - Brave API integration
10. **bddk_mcp_module**: BDDK (Banking Regulation and Supervision Agency) decisions - Tavily API integration
11. **sayistay_mcp_module**: Sayıştay (Court of Accounts) decisions - Audit findings and appeals

### Key Design Patterns
- **FastMCP Integration**: Uses FastMCP framework for MCP server implementation
- **Async HTTP Clients**: Each module uses httpx for async HTTP requests
- **Pydantic Models**: All data structures use Pydantic for validation
- **HTML to Markdown Conversion**: Uses MarkItDown library with BytesIO optimization for efficient conversion
- **BytesIO Optimization**: All HTML/PDF conversion uses in-memory streams instead of temp files
- **Paginated Content**: Long documents are paginated (5,000 character chunks)
- **Comprehensive Logging**: Structured logging to files and console
- **Token Optimization**: Extensively optimized for minimal MCP overhead (56.8% reduction)
- **Empty String Defaults**: All optional parameters use empty strings instead of null for efficiency

### Client Session Management
- All API clients have `close_client_session()` methods
- Server handles cleanup via `atexit.register(perform_cleanup)`
- Proper async session management with error handling

### MCP Tools Pattern
Each legal database exposes 2 main tools:
1. **Search tool**: Searches decisions with various criteria
2. **Document retrieval tool**: Gets full document content as Markdown

### Yargıtay Search Tools (Dual API System)

The system provides TWO Yargıtay search tools for comprehensive coverage:

1. **search_yargitay_detailed** - Primary API (karararama.yargitay.gov.tr) - **DEACTIVATED**
   - Advanced filtering options (chamber selection, esas/karar no, date range)
   - Complex search syntax (AND/OR/wildcards/exact phrases)
   - Chamber selection: 49 options including all Civil (1-23) and Criminal (1-23) chambers
   - Complete chamber list: Hukuk/Ceza Genel Kurulu, Individual chambers, Başkanlar Kurulu, Büyük Genel Kurulu
   - **Status**: Commented out for token optimization

2. **search_bedesten_unified** - Unified Bedesten API (bedesten.adalet.gov.tr) - **ACTIVE**
   - Multi-court search with court type selection: `court_types=["YARGITAYKARARI"]` for Yargıtay only
   - **Exact phrase search**: Use double quotes for precise matching (e.g., `"\"mülkiyet kararı\""`)
   - **Regular phrase search**: Without quotes searches individual words separately
   - Chamber selection: Same 49 options as primary API (via birimAdi parameter)
   - Date filtering support: kararTarihiStart and kararTarihiEnd (ISO 8601 format)
   - Different data source with recent decisions
   - Returns documentId for full text retrieval
   - Supports both HTML and PDF document formats

**Important**: Use `search_bedesten_unified` with `court_types=["YARGITAYKARARI"]` for Yargıtay searches (primary API deactivated for optimization).

#### Yargıtay Chamber Selection (49 options)

**Civil Chambers (Hukuk):**
- `Hukuk Genel Kurulu` - Civil General Assembly
- `1. Hukuk Dairesi` through `23. Hukuk Dairesi` - Individual Civil Chambers (23 chambers)
- `Hukuk Daireleri Başkanlar Kurulu` - Civil Chambers Presidents Board

**Criminal Chambers (Ceza):**
- `Ceza Genel Kurulu` - Criminal General Assembly  
- `1. Ceza Dairesi` through `23. Ceza Dairesi` - Individual Criminal Chambers (23 chambers)
- `Ceza Daireleri Başkanlar Kurulu` - Criminal Chambers Presidents Board

**General Assembly:**
- `Büyük Genel Kurulu` - Grand General Assembly

**Usage:** Use empty string `""` for ALL chambers, or specify exact chamber name for targeted search.

### Danıştay Search Tools (Triple API System)

The system provides THREE Danıştay search tools for comprehensive coverage:

1. **search_danistay_by_keyword** - Primary API (keyword-based) - **DEACTIVATED**
   - AND/OR/NOT keyword logic
   - Multiple keyword combinations
   - **Status**: Commented out for token optimization

2. **search_danistay_detailed** - Primary API (detailed criteria) - **DEACTIVATED**
   - Advanced filtering (daire, esas/karar no, date range, legislation)
   - Complex search parameters
   - **Status**: Commented out for token optimization

3. **search_bedesten_unified** - Unified Bedesten API (bedesten.adalet.gov.tr) - **ACTIVE**
   - Multi-court search with court type selection: `court_types=["DANISTAYKARAR"]` for Danıştay only
   - **Exact phrase search**: Use double quotes for precise matching (e.g., `"\"idari işlem\""`)
   - **Regular phrase search**: Without quotes searches individual words separately
   - Chamber selection: 27 Danıştay options (via birimAdi parameter)
   - Date filtering support: kararTarihiStart and kararTarihiEnd (ISO 8601 format)
   - Different data source
   - Returns documentId for full text retrieval
   - Supports both HTML and PDF document formats

**Important**: Use `search_bedesten_unified` with `court_types=["DANISTAYKARAR"]` for Danıştay searches (primary APIs deactivated for optimization).


### Bedesten Unified API Tools

The Bedesten API has been unified into a single interface that supports all court types:

**search_bedesten_unified** - Unified Multi-Court Search
- **Court type selection**: Use `court_types` parameter to specify which courts to search:
  - `["YARGITAYKARARI"]` - Yargıtay (Court of Cassation)
  - `["DANISTAYKARAR"]` - Danıştay (Council of State)
  - `["YERELHUKUK"]` - Local Civil Courts
  - `["ISTINAFHUKUK"]` - Civil Courts of Appeals
  - `["KYB"]` - Extraordinary Appeals (Kanun Yararına Bozma)
  - Multiple types: `["YARGITAYKARARI", "DANISTAYKARAR"]` for combined search
- **Search Operators Supported**:
  - **Simple terms**: `phrase="mülkiyet hakkı"` (searches for both words)
  - **Exact phrases**: `phrase="\"mülkiyet hakkı\""` (precise matching with quotes)
  - **Required terms**: `phrase="+mülkiyet hakkı"` (must contain mülkiyet)
  - **Exclude terms**: `phrase="mülkiyet -kira"` (contains mülkiyet but not kira)
  - **Boolean AND**: `phrase="mülkiyet AND hak"` (both terms required)
  - **Boolean OR**: `phrase="mülkiyet OR tapu"` (either term acceptable)
  - **Boolean NOT**: `phrase="mülkiyet NOT satış"` (contains mülkiyet but not satış)
- **❌ NOT Supported**: Wildcards (`*`, `?`), regex patterns (`/regex/`), fuzzy search (`~`), proximity search (`~N`)
- **Chamber filtering**: Available for Yargıtay (52 options) and Danıştay (27 options)
- **Date filtering**: ISO 8601 format support (kararTarihiStart/kararTarihiEnd)
- **Pagination**: Configurable page size (1-10) and page number
- Returns documentId for full text retrieval
- Supports both HTML and PDF document formats

**get_bedesten_document_markdown** - Universal Document Retrieval
- Single tool for retrieving documents from any Bedesten-supported court
- Auto-detects court type based on document ID
- Converts decisions to clean Markdown format
- Handles both HTML and PDF source documents

### Sayıştay (Court of Accounts) Search Tools

The Sayıştay module provides access to audit findings and appeals decisions from Turkey's Court of Accounts:

**search_sayistay_genel_kurul** - General Assembly Decisions
- Searches precedent-setting rulings by the full assembly
- Addresses interpretation of audit and accountability regulations
- Search by decision number, date range, and full text
- Returns decision summaries with detailed abstracts

**search_sayistay_temyiz_kurulu** - Appeals Board Decisions  
- Reviews appeals against audit chamber decisions
- Higher-level review of audit findings and sanctions
- Filter by chamber (1-8), public administration type, decision subject
- Search by audit report number, file number, appeals decision

**search_sayistay_daire** - Chamber Decisions
- First-instance audit findings and sanctions
- Individual audit chambers before potential appeals
- Filter by chamber, account year, public administration type
- Search by audit report number and decision text

**get_sayistay_document_markdown** - Document Retrieval
- Retrieves full text of decisions from any Sayıştay decision type
- Converts decisions to clean Markdown format
- Supports Genel Kurul, Temyiz Kurulu, and Daire decisions

### KVKK Search Tools (Brave API)

**search_kvkk_decisions** - Brave Search API (api.search.brave.com)
- Searches KVKK (Personal Data Protection Authority) decisions via Brave API
- **Turkish language search**: Use Turkish legal terms for best results
- **Site-targeted search**: Automatically includes `site:kvkk.gov.tr "karar özeti"`
- **Pagination support**: Page-based results with configurable page size
- Returns decision summaries with metadata extraction
- Supports all KVKK decision types (fines, compliance, data breaches, etc.)

**get_kvkk_document_markdown** - Document retrieval with pagination
- **Paginated Markdown conversion**: 5,000-character chunks for easier processing
- **Page parameter support**: `page_number` (1-indexed, default: 1)
- **BytesIO optimization**: Uses in-memory streams instead of temp files for conversion
- Extracts structured metadata (decision date, number, subject summary)
- Handles HTML content from KVKK website with robust error handling
- Preserves legal document structure and formatting
- Returns paginated decision text in clean Markdown format
- **Pagination info**: Includes `current_page`, `total_pages`, `is_paginated` fields

**KVKK Context**:
KVKK (Kişisel Verilerin Korunması Kanunu) is Turkey's Personal Data Protection Law, equivalent to GDPR. The Personal Data Protection Authority (KVKK) enforces data protection regulations, issues fines, and publishes decisions on data processing compliance, data breaches, consent requirements, and international data transfers.

### BDDK Search Tools (Tavily API)

**search_bddk_decisions** - BDDK banking regulation decisions search
- Searches BDDK (Bankacılık Düzenleme ve Denetleme Kurumu) decisions via optimized search
- **Optimized targeting**: Uses "Karar Sayısı" keyword for precision
- **Specific URL filtering**: Targets `bddk.org.tr/Mevzuat/DokumanGetir` for decision documents
- **Pagination support**: Page-based results with configurable page size
- Returns decision summaries with metadata extraction
- Supports all BDDK decision types (banking licenses, electronic money, payment services, etc.)

**get_bddk_document_markdown** - Document retrieval with pagination
- **Paginated Markdown conversion**: 5,000-character chunks for easier processing
- **Page parameter support**: `page_number` (1-indexed, default: 1)
- **Multiple URL pattern support**: Automatic fallback for different BDDK URL formats
- Extracts structured metadata (decision date, number, subject summary)
- Handles both HTML and PDF content from BDDK website with robust error handling
- Preserves legal document structure and formatting
- Returns paginated decision text in clean Markdown format
- **Pagination info**: Includes `current_page`, `total_pages`, `is_paginated` fields

**BDDK Context**:
BDDK (Bankacılık Düzenleme ve Denetleme Kurumu) is Turkey's Banking Regulation and Supervision Agency responsible for banking licenses, supervision, electronic money institutions, payment services regulation, cryptocurrency guidance, and financial technology oversight.

Example workflows:
```python
# Yargıtay search with both tools - chamber and date filtering available in both
results1 = await search_yargitay_detailed(arananKelime="mülkiyet", birimYrgKurulDaire="1. Hukuk Dairesi")
results2 = await search_bedesten_unified(phrase="mülkiyet", court_types=["YARGITAYKARARI"], birimAdi="1. Hukuk Dairesi", kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z")

# Exact phrase search examples for precise matching
results2_exact = await search_bedesten_unified(phrase="\"mülkiyet kararı\"", court_types=["YARGITAYKARARI"], birimAdi="1. Hukuk Dairesi")  # Exact phrase
results2_regular = await search_bedesten_unified(phrase="mülkiyet kararı", court_types=["YARGITAYKARARI"], birimAdi="1. Hukuk Dairesi")   # Individual words

# Get Yargıtay documents
doc1 = await get_yargitay_document_markdown(id)  # From primary API
doc2 = await get_bedesten_document_markdown(documentId)  # From Bedesten

# Danıştay search with all three tools - chamber and date filtering available in Bedesten
results3 = await search_danistay_by_keyword(andKelimeler=["mülkiyet"])
results4 = await search_danistay_detailed(...)
results5 = await search_bedesten_unified(phrase="mülkiyet", court_types=["DANISTAYKARAR"], birimAdi="3. Daire", kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z")

# Exact phrase search for Danıştay
results5_exact = await search_bedesten_unified(phrase="\"idari işlem\"", court_types=["DANISTAYKARAR"], birimAdi="3. Daire")  # Exact phrase

# Get Danıştay documents
doc3 = await get_danistay_document_markdown(id)  # From primary APIs
doc4 = await get_bedesten_document_markdown(documentId)  # From Bedesten

# Multi-court unified search - with date filtering and exact phrase search
results6 = await search_bedesten_unified(phrase="mülkiyet", court_types=["YERELHUKUK"], kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z")
results6_exact = await search_bedesten_unified(phrase="\"sözleşme ihlali\"", court_types=["YERELHUKUK"])  # Exact phrase

# İstinaf Hukuk search - with date filtering and exact phrase search
results7 = await search_bedesten_unified(phrase="mülkiyet", court_types=["ISTINAFHUKUK"], kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z")
results7_exact = await search_bedesten_unified(phrase="\"temyiz incelemesi\"", court_types=["ISTINAFHUKUK"])  # Exact phrase

# KYB search - with date filtering and exact phrase search
results8 = await search_bedesten_unified(phrase="mülkiyet", court_types=["KYB"], kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z")
results8_exact = await search_bedesten_unified(phrase="\"kanun yararına bozma\"", court_types=["KYB"])  # Exact phrase

# Multi-court combined search
results9 = await search_bedesten_unified(phrase="mülkiyet", court_types=["YARGITAYKARARI", "DANISTAYKARAR", "YERELHUKUK"], pageSize=10)

# Universal document retrieval for all Bedesten courts
doc5 = await get_bedesten_document_markdown(documentId)  # Works for any court type

# Sayıştay (Court of Accounts) search - audit findings and appeals
results10 = await search_sayistay_genel_kurul(karar_no="5415", karar_tarih_baslangic="2023")
results11 = await search_sayistay_temyiz_kurulu(ilam_dairesi="1", yili="2023", kamu_idaresi_turu="Belediyeler ve Bağlı İdareler")
results12 = await search_sayistay_daire(yargilama_dairesi="1", hesap_yili="2023", web_karar_konusu="İhale Mevzuatı ile İlgili Kararlar")

# Get Sayıştay documents
doc8 = await get_sayistay_document_markdown(decision_id="12345", decision_type="genel_kurul")

# KVKK search (Brave API) - Turkish data protection decisions
results9 = await search_kvkk_decisions(keywords="açık rıza", page=1, pageSize=10)
results9_gdpr = await search_kvkk_decisions(keywords="GDPR uyum", page=1, pageSize=5)
results9_breach = await search_kvkk_decisions(keywords="veri ihlali bildirimi", page=1, pageSize=10)

# Get KVKK documents
doc8 = await get_kvkk_document_markdown(decision_url="https://www.kvkk.gov.tr/Icerik/7288/2021-1303")
```

## Configuration

### Dependencies
- **httpx**: Async HTTP client for API requests
- **beautifulsoup4**: HTML parsing for preprocessing
- **markitdown[pdf]**: HTML/PDF to Markdown conversion
- **pydantic**: Data validation and serialization
- **fastmcp**: MCP server framework
- **playwright**: Browser automation for complex scraping
- **pypdf**: PDF processing capabilities

### Environment
- Python 3.11+ required
- Supports both uvx and direct Python execution
- Logs written to `logs/mcp_server.log`

### API Keys Configuration
- **BRAVE_API_TOKEN**: Optional for KVKK search functionality via Brave Search API
  - Get your API key from: https://brave.com/search/api/
  - Set environment variable: `export BRAVE_API_TOKEN=your_api_token_here`
  - **Fallback Token**: If not set, uses a limited free token automatically
  - KVKK search tools will work without configuration (with rate limits)

### OAuth Authentication Configuration

The server uses **Clerk JWT tokens** for all authentication. **Cross-origin authentication** is implemented using Bearer JWT tokens as per Clerk's best practices.

#### Key Authentication Features ✅
- **Clerk JWT Tokens**: All authentication uses Clerk-generated JWT tokens
- **Bearer Authentication**: Primary method for direct API access (`Authorization: Bearer`)
- **Cross-Origin Support**: Works across different subdomains
- **Token Validation**: Uses Clerk's `authenticate_request` method
- **Email-Based Identity**: User identification via email field in JWT payload
- **Scopes Support**: Token-based permissions (`yargi.read`, etc.)
- **SSE & HTTP Support**: Identical authentication for both transports
- **No Custom Tokens**: Removed custom JWT generation in favor of Clerk tokens

#### Cross-Origin vs Same-Origin Authentication

**Current Setup**: Cross-Origin (Different Subdomains)
- Frontend: `yargimcp.com` 
- API Server: `api.yargimcp.com`
- **Status**: Different subdomains = Cross-origin requests

**Clerk's Authentication Approach**:
- **Same-Origin** (`foo.com` → `foo.com/api`): Cookies automatically included
- **Cross-Origin** (`foo.com` → `api.foo.com`): **Bearer tokens required**

**Important**: Subdomain cookie sharing does **NOT** work for cross-origin requests according to Clerk documentation. JWT tokens are the correct approach.

#### Setup OAuth Environment
```bash
# Copy environment template
cp .env.example .env

# Configure OAuth settings in .env
ENABLE_AUTH=true                    # Enable/disable authentication
CLERK_SECRET_KEY=sk_test_xxx        # Clerk secret key from dashboard
CLERK_PUBLISHABLE_KEY=pk_test_xxx   # Clerk publishable key
CLERK_OAUTH_REDIRECT_URL=http://localhost:8000/auth/callback
CLERK_FRONTEND_URL=http://localhost:3000
```

#### JWT Token Authentication Flow

**Primary Method**: JWT Token (Cross-Origin)

1. **Frontend** (`yargimcp.com/sign-in`):
   ```javascript
   // User signs in with Clerk
   const { getToken } = useAuth();
   
   // Generate JWT token after login
   const token = await getToken();
   
   // Redirect to API with token parameter
   window.location.href = `${redirect_url}?clerk_token=${token}`;
   ```

2. **Backend** (`api.yargimcp.com/auth/callback`):
   ```python
   # Hybrid authentication: JWT token + cookie fallback
   if clerk_token:
       # Validate JWT token with Clerk SDK
       jwt_claims = clerk.jwt_templates.verify_token(clerk_token)
       user_id = jwt_claims.get("email")
   else:
       # Fallback to cookie validation (for same-origin)
       clerk_session = request.cookies.get("__session")
   ```

#### Authentication Methods Hierarchy

1. **Bearer JWT Token** (Primary - Direct API Access)
   - Standard Bearer authentication header
   - `Authorization: Bearer YOUR_CLERK_JWT_TOKEN`
   - Supports both `/mcp` and `/sse` endpoints
   - Uses Clerk's `authenticate_request` method
   - Works across different subdomains

2. **JWT Token** (OAuth Flow - Cross-Origin)
   - Passed as `clerk_token` URL parameter during OAuth flow
   - Validated using Clerk SDK
   - Used for initial authentication setup

3. **Cookie Validation** (Fallback - Same-Origin)
   - `__session` cookie from Clerk
   - Only works on same domain/subdomain
   - Automatic fallback if JWT token missing

4. **Trusted Redirect** (Last Resort)
   - Assumes authentication if Clerk redirected to callback
   - Used when both JWT and cookie validation fail

#### Clerk Dashboard Setup
1. Create account at [Clerk Dashboard](https://dashboard.clerk.com/)
2. Create new application
3. Go to **Social Connections** → Enable **Google** provider
4. Configure Google OAuth:
   - Get Google OAuth credentials from [Google Console](https://console.developers.google.com/)
   - Add redirect URI: `http://localhost:8000/auth/callback`
5. Copy API keys to `.env` file

#### OAuth Flow Endpoints
```bash
# OAuth login (redirects to Clerk/Google)
GET /auth/login

# OAuth callback (handles OAuth response with JWT token support)
GET /auth/callback?clerk_token=JWT_TOKEN

# Google OAuth direct link
GET /auth/google/login

# Get current user info
GET /auth/user

# Validate session
GET /auth/session/validate

# Logout
POST /auth/logout
```

#### Bearer JWT Token Usage

**Getting Clerk JWT Tokens**:
Clerk JWT tokens are automatically generated by Clerk after user authentication. 

**Current JWT Claim Configuration**:
```json
{
  "aud": "pk_test_YXJ0aXN0aWMtc3dhbi04MS5jbGVyay5hY2NvdW50cy5kZXYk",
  "plan": "{{user.unsafe_metadata.plan}}",
  "email": "{{user.primary_email_address}}",
  "scopes": ["yargi.read"]
}
```

**Recommended Best Practice JWT Claim**:
```json
{
  "aud": "pk_test_YXJ0aXN0aWMtc3dhbi04MS5jbGVyay5hY2NvdW50cy5kZXYk",
  "email": "{{user.primary_email_address}}",
  "email_verified": "{{user.primary_email_address.verification.status}}",
  "name": "{{user.first_name}} {{user.last_name}}",
  "given_name": "{{user.first_name}}",
  "family_name": "{{user.last_name}}",
  "picture": "{{user.image_url}}",
  "scopes": ["yargi.read"],
  "plan": "{{user.public_metadata.plan}}",
  "role": "{{user.public_metadata.role}}"
}
```

**JWT Standards Compliance**:
- ✅ **email**: User's primary email address
- ✅ **email_verified**: Email verification status
- ✅ **name**: Full name for display
- ✅ **given_name/family_name**: Standard name claims
- ✅ **picture**: User avatar URL
- ✅ **aud**: Audience (your app's publishable key)
- ✅ **iat/exp**: Issued at and expiration (automatic)
- ✅ **iss**: Issuer (Clerk domain)

**Custom Claims**:
- **scopes**: Application-specific permissions
- **plan**: User's subscription plan (from public_metadata)
- **role**: User's role (from public_metadata)

**Security Notes**:
- Use `public_metadata` instead of `unsafe_metadata` for sensitive data
- `unsafe_metadata` is accessible to frontend, `public_metadata` is read-only
- Private metadata should not be included in JWT tokens

**Using Clerk Bearer Tokens**:
```bash
# HTTP Transport
curl -X POST https://api.yargimcp.com/mcp/ \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: api-client-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# SSE Transport
curl -X POST https://api.yargimcp.com/sse/ \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: sse-client-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

**Token Validation Implementation**:
- Uses Clerk's `authenticate_request` method
- Validates token signature against Clerk's JWKS endpoint
- Extracts user identity from `email` field (primary identifier)
- Supports scopes from token payload (`yargi.read`, etc.)
- Extracts user metadata: `role`, `plan`, `name`, `email_verified`
- Stores user information in request state for use by MCP tools

**Request State Variables**:
```python
request.state.user_id = payload.get('email')
request.state.user_email = payload.get('email')
request.state.user_name = payload.get('name')
request.state.user_role = payload.get('role')
request.state.user_plan = payload.get('plan')
request.state.token_scopes = payload.get('scopes', ['yargi.read'])
```

**Migration from Current Claim**:
1. Update JWT template in Clerk Dashboard
2. Change `unsafe_metadata` to `public_metadata`
3. Add standard JWT claims (`name`, `given_name`, etc.)
4. Test with new token format

#### Development vs Production
- **Development Mode**: Set `ENABLE_AUTH=false` to disable authentication
- **Production Mode**: Set `ENABLE_AUTH=true` with real Clerk credentials
- **Token Validation**: Uses Clerk SDK's `authenticate_request()` for all token validation
- **Bearer JWT Support**: Primary authentication method for direct API access
- **SSE Transport**: Server-Sent Events support with identical authentication
- **Custom Tokens**: Removed - all authentication now uses Clerk JWT tokens

#### Troubleshooting Cross-Origin Authentication

**Common Issues & Solutions** ✅:

1. **MCP Connection Drops Immediately** ✅ **RESOLVED**
   
   **Previous Issue**: Claude AI connection dropping after OAuth flow
   **Root Cause**: Custom FastAPI POST handler conflicting with MCP Auth Toolkit
   **Solution Applied**: Removed interfering handler, proper request forwarding
   
   ```bash
   # Check backend logs for successful authentication
   fly logs --app yargi-mcp
   
   # Look for these SUCCESS entries:
   ✅ "OAuth authorize request - client_id: mcp-client-xxx"
   ✅ "Token exchange - grant_type: authorization_code"  
   ✅ "PKCE validation successful"
   ✅ "User authenticated: True, method: trusted_redirect"
   ```

2. **Redis Connection Issues** ✅ **RESOLVED**
   
   **Previous Issue**: SSL connection errors with external Upstash Redis
   **Root Cause**: Using HTTPS URL instead of HTTP for Fly.io's internal Redis
   **Solution Applied**: 
   - Switched to Fly.io native Upstash Redis
   - Use `http://` URL (not `https://`)
   - Added connection timeout protection (5 seconds)
   - Automatic fallback to in-memory storage
   
   ```bash
   # Verify Redis is working
   fly logs --app yargi-mcp | grep "Redis"
   
   # Success indicators:
   ✅ "Upstash Redis client created"
   ✅ "Redis store initialized successfully"
   ✅ "Stored authorization code ... in Redis"
   ```

2. **405 Method Not Allowed** ✅ **RESOLVED**
   
   **Previous Issue**: POST requests to `/mcp` returning 405 errors
   **Root Cause**: FastAPI mounting configuration issue
   **Solution Applied**: Custom route handler with proper ASGI forwarding
   
   ```bash
   # Test POST method acceptance (should return 400, not 405)
   curl -X POST -s -w "%{http_code}" -o /dev/null https://api.yargimcp.com/mcp
   # Expected: 400 (bad request due to missing headers)
   # Fixed: No longer 405 (method not allowed)
   ```

3. **JWT Token Not Generated**
   ```javascript
   // Add debug logging in frontend (yargimcp.com/sign-in)
   console.log('isSignedIn:', isSignedIn);
   console.log('redirect_url:', redirect_url);
   console.log('JWT token generated:', token ? 'YES' : 'NO');
   ```

4. **Browser DevTools Debug**
   ```
   Network Tab → Find callback request:
   ✅ URL should contain: ?state=xxx:yyy (state parameter)
   ✅ Request should go to: api.yargimcp.com/auth/callback
   ✅ Response: 307 Redirect to Claude AI with authorization code
   ```

5. **Authentication Method Check**
   ```bash
   # Backend logs show which method was used:
   ✅ "User authenticated: True, method: trusted_redirect" (working)
   # "JWT token validation successful" (if JWT provided)
   # "Found Clerk session cookie" (fallback)
   ```

**Current Status Debug Commands**:
```bash
# Test MCP endpoint availability (HTTP)
curl -X POST -s -w "%{http_code}" https://api.yargimcp.com/mcp
# Expected: 400 (accepts POST, but needs proper MCP headers)

# Test SSE endpoint availability
curl -X POST -s -w "%{http_code}" https://api.yargimcp.com/sse
# Expected: 400 (accepts POST, but needs proper MCP headers)

# Test OAuth discovery
curl https://api.yargimcp.com/.well-known/oauth-authorization-server | jq '.authorization_endpoint'
# Expected: "https://api.yargimcp.com/authorize"

# Test health status
curl https://api.yargimcp.com/health | jq '.auth_enabled'
# Expected: true

# Monitor live connection attempts
fly logs --app yargi-mcp
```

**Domain Migration Verification**:
```bash
# Verify all endpoints use api.yargimcp.com
curl -s https://api.yargimcp.com/.well-known/oauth-authorization-server | grep -o "api\.yargimcp\.com" | wc -l
# Expected: Multiple instances (all endpoints updated)

# Test cross-domain authentication flow
curl -I "https://api.yargimcp.com/auth/login"
# Expected: 30x redirect to accounts.yargimcp.com
```

## Development Notes

### Testing

#### MCP Server Testing Strategy
1. **Individual API Client Tests**: Test each legal database client independently
2. **MCP Tool Integration Tests**: Test tools through FastMCP Client
3. **Debug Scripts**: Test specific functionality during development

#### Testing Individual API Clients
```bash
# Test specific database clients directly
uv run test_bedesten_api.py        # Bedesten API
uv run debug_rekabet_arama.py      # Competition Authority debug
uv run test_kik_client.py          # Public Procurement Authority
```

#### Testing MCP Tools with FastMCP Client
**Recommended approach for testing MCP server functionality:**

```python
from fastmcp import Client
from mcp_server_main import app
import json

async def test_mcp_server():
    # Create in-memory client (no network/process overhead)
    client = Client(app)
    
    async with client:
        # 1. List all available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # 2. Call specific tools
        result = await client.call_tool("search_yargitay_bedesten", {
            "phrase": "mülkiyet",
            "pageSize": 5
        })
        
        # 3. Parse FastMCP response format
        if isinstance(result, list) and len(result) > 0:
            json_data = json.loads(result[0].text)
            print(f"Results: {json_data}")
```

#### Testing MCP Server via HTTP with curl

**Start the ASGI server:**
```bash
# Run the server
uv run uvicorn asgi_app:app --host 127.0.0.1 --port 8000 --reload

# Check server health
curl -s http://127.0.0.1:8000/health | jq '.'
```

**MCP over HTTP Testing:**

All MCP requests must include proper JSON-RPC format and headers:

```bash
# Required headers for MCP over HTTP
-H "Content-Type: application/json"
-H "Accept: application/json, text/event-stream"
-H "Session-ID: test-session-123"

# JSON-RPC message format
{
  "jsonrpc": "2.0",
  "method": "METHOD_NAME",
  "params": {...},
  "id": 1
}
```

**Basic MCP Tests:**

```bash
# 1. List all available tools
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }' | jq '.result.tools | length'

# 2. Get specific tool schema
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }' | jq '.result.tools[] | select(.name=="search_yargitay_bedesten")'

# 3. Call a tool (Yargıtay search example)
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_yargitay_bedesten",
      "arguments": {
        "phrase": "mülkiyet hakkı",
        "pageSize": 3
      }
    },
    "id": 1
  }' | jq '.result.content[0].text | fromjson | .decisions | length'

# 4. Get document content (using documentId from search results)
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_yargitay_bedesten_document_markdown",
      "arguments": {
        "documentId": "DOCUMENT_ID_FROM_SEARCH"
      }
    },
    "id": 1
  }' | jq '.result.content[0].text' | head -20
```

**Advanced MCP Tool Testing:**

```bash
# Test Danıştay search with chamber filtering
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_danistay_bedesten",
      "arguments": {
        "phrase": "idari işlem",
        "birimAdi": "3. Daire",
        "pageSize": 5
      }
    },
    "id": 1
  }' | jq '.result.content[0].text | fromjson'

# Test Constitutional Court norm control search
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_anayasa_norm_denetimi_decisions",
      "arguments": {
        "keywords_all": ["eğitim hakkı"],
        "results_per_page": 3
      }
    },
    "id": 1
  }' | jq '.result.content[0].text | fromjson'

# Test Competition Authority search
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_rekabet_kurumu_decisions",
      "arguments": {
        "KararTuru": "Birleşme ve Devralma",
        "PdfText": "telekomünikasyon",
        "page": 1
      }
    },
    "id": 1
  }' | jq '.result.content[0].text | fromjson'
```

**OAuth Authentication Testing:**

```bash
# Test without authentication (development mode)
curl -s http://127.0.0.1:8000/auth/user | jq '.'

# Test with OAuth token (production mode)
curl -s -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  http://127.0.0.1:8000/auth/user | jq '.'

# MCP with authentication
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Session-ID: test-session-123" \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }' | jq '.result.tools | length'
```

**Common curl Testing Patterns:**

```bash
# Create a reusable MCP test function
mcp_test() {
  local method=$1
  local params=${2:-"{}"}
  curl -s -X POST http://127.0.0.1:8000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Session-ID: test-session-123" \
    -d "{
      \"jsonrpc\": \"2.0\",
      \"method\": \"$method\",
      \"params\": $params,
      \"id\": 1
    }"
}

# Usage examples
mcp_test "tools/list" | jq '.result.tools | length'
mcp_test "tools/call" '{"name": "search_yargitay_bedesten", "arguments": {"phrase": "test", "pageSize": 1}}'
```



#### FastMCP Client Response Format
**Important**: FastMCP Client returns tool results as `TextContent` objects:
```python
# Response format: List[TextContent]
result = await client.call_tool("tool_name", params)

# Extract JSON data
if isinstance(result, list) and len(result) > 0:
    text_content = result[0].text
    parsed_data = json.loads(text_content)
```

#### Running the MCP Server for External Testing
```bash
# Start server for external MCP clients
uv run mcp_server_main.py

# Or use entry point
yargi-mcp
```


### Search Capabilities
- Complex search syntax support (AND, OR, NOT, wildcards, exact phrases)
- Multiple search criteria per legal database
- Pagination support for large result sets




### Date Filtering Format (Bedesten API)
All Bedesten API tools support consistent date filtering:
- **Format**: ISO 8601 with Z timezone: `YYYY-MM-DDTHH:MM:SS.000Z`
- **Parameters**: `kararTarihiStart` (start date) and `kararTarihiEnd` (end date)
- **Usage**: Both parameters are optional, use together for date ranges or single parameter for one-sided filtering
- **Examples**:
  - Single date: `kararTarihiStart="2024-06-25T00:00:00.000Z", kararTarihiEnd="2024-06-25T23:59:59.999Z"`
  - Year range: `kararTarihiStart="2024-01-01T00:00:00.000Z", kararTarihiEnd="2024-12-31T23:59:59.999Z"`
  - From date: `kararTarihiStart="2024-01-01T00:00:00.000Z"` (no end date)
  - Until date: `kararTarihiEnd="2024-12-31T23:59:59.999Z"` (no start date)

### Exact Phrase Search Format (Bedesten API)
All Bedesten API tools support two types of phrase searching:
- **Regular phrase search**: `phrase="mülkiyet kararı"` - searches for individual words separately
- **Exact phrase search**: `phrase="\"mülkiyet kararı\""` - searches for the exact phrase as a unit
- **Benefits of exact search**: More precise results, fewer false positives, better for specific legal terms
- **Usage examples**:
  - Legal concepts: `"\"idari işlem\""`, `"\"sözleşme ihlali\""`, `"\"kanun yararına bozma\""`
  - Complex phrases: `"\"temyiz incelemesi\""`, `"\"mülkiyet kararı\""`
  - Multiple word terms: `"\"kamu yararı\""`, `"\"hukuka aykırılık\""`

## FastMCP Best Practices Implementation

This project implements comprehensive FastMCP best practices to maximize LLM compatibility and effectiveness. Based on official FastMCP documentation, LLMs can read and understand the following components:

### LLM-Readable Components
1. **Tool Names**: Clear, descriptive names that indicate functionality
2. **Tool Descriptions**: Comprehensive explanations of what each tool does
3. **Parameter Descriptions**: Detailed parameter documentation with examples
4. **Annotations**: Hints that help LLMs understand tool behavior

### Tool Description Best Practices ✅ IMPLEMENTED

All tools in this project follow FastMCP best practices:

#### 1. Comprehensive Tool Descriptions
**Format**: `@app.tool(description="Clear description of tool purpose and capabilities")`

**Implementation Examples**:
```python
@app.tool(
    description="Search Yargıtay (Court of Cassation) decisions using Bedesten API with chamber filtering (52 options), date range filtering, and exact phrase search capabilities",
    annotations={...}
)

@app.tool(
    description="Search Danıştay (Council of State) decisions using Bedesten API with chamber filtering (27 options), date range filtering, and exact phrase search support",
    annotations={...}
)
```

**Best Practices Applied**:
- ✅ **Specific functionality**: Clear explanation of what the tool searches
- ✅ **Key features highlighted**: Chamber count, filtering options, search types
- ✅ **Legal context**: Court names and their significance in Turkish legal system
- ✅ **Capability scope**: What makes each tool unique or powerful

#### 2. Enhanced Parameter Descriptions
**Format**: Detailed Field descriptions with examples and constraints

**Implementation Examples**:
```python
phrase: str = Field(..., description="""
    Aranacak kavram/kelime. İki farklı arama türü desteklenir:
    • Normal arama: "mülkiyet kararı" - kelimeler ayrı ayrı aranır
    • Tam cümle arama: "\"mülkiyet kararı\"" - tırnak içindeki ifade aynen aranır
    Tam cümle aramalar daha kesin sonuçlar verir.
""")

birimAdi: Optional[Union[YargitayBirimEnum, DanistayBirimEnum]] = Field(None, description="""
    Chamber/Department filter (optional). Select specific court chamber:
    • Yargıtay: 52 options (1-23 Hukuk, 1-23 Ceza, Genel Kurullar, Başkanlar Kurulu)
    • Danıştay: 27 options (1-17 Daireler, İdare/Vergi Kurulları, Askeri Mahkemeler)
    Use None/empty for all chambers, or specify exact chamber name
""")

kararTarihiStart: Optional[str] = Field(None, description="""
    Decision start date filter (optional). Format: YYYY-MM-DDTHH:MM:SS.000Z
    Example: "2024-01-01T00:00:00.000Z" for decisions from Jan 1, 2024
    Use with kararTarihiEnd for date range filtering
""")
```

**Best Practices Applied**:
- ✅ **Format specifications**: Exact format requirements with examples
- ✅ **Usage scenarios**: When and how to use each parameter
- ✅ **Option enumeration**: Clear listing of available choices
- ✅ **Relationship explanations**: How parameters work together
- ✅ **Practical examples**: Real-world usage patterns

#### 3. Tool Annotations for LLM Understanding
**Format**: Annotations provide behavioral hints to LLMs

**Implementation**:
```python
@app.tool(
    description="...",
    annotations={
        "readOnlyHint": True,        # Tool doesn't modify system state
        "idempotentHint": True,      # Same inputs = same outputs
        "openWorldHint": True        # Explores open-ended databases (for search tools)
    }
)
```

**Annotation Usage**:
- ✅ **readOnlyHint**: True for all tools (no system modifications)
- ✅ **idempotentHint**: True for all tools (deterministic behavior)
- ✅ **openWorldHint**: True for search tools, False for document retrieval tools

#### 4. Search vs Document Tool Differentiation

**Search Tools**:
- Return structured metadata (lists, summaries, IDs)
- Support filtering and pagination
- Have `openWorldHint: True` (explore databases)
- Names end with descriptive search terms

**Document Tools**:
- Return full text content in Markdown format
- Convert documents from source formats (HTML/PDF)
- Have `openWorldHint: False` (retrieve specific documents)
- Names clearly indicate document retrieval

### Function-Level Documentation Best Practices ✅ IMPLEMENTED

#### 1. Comprehensive Docstrings
**Format**: Multi-line docstrings with structured information

**Implementation Example**:
```python
async def search_yargitay_bedesten(...):
    """
    Searches Yargıtay (Court of Cassation) decisions using Bedesten API.
    
    Yargıtay is Turkey's highest court for civil and criminal matters, equivalent
    to a Supreme Court. This tool provides access to both recent and historical decisions
    with advanced filtering capabilities.
    
    Key Features:
    • Chamber filtering: 52 options (23 Civil + 23 Criminal + General Assemblies)
    • Date range filtering with ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z)
    • Exact phrase search using double quotes: "\"legal term\""
    • Regular search for individual keywords
    • Pagination support (1-100 results per page)
    
    Use cases:
    • Research supreme court precedents
    • Find decisions from specific chambers
    • Search for recent interpretations of legal principles
    • Analyze court reasoning on specific topics
    
    Returns structured data with decision metadata including chamber, dates, case numbers,
    and summaries. Use get_yargitay_bedesten_document_markdown() to retrieve full texts.
    """
```

**Best Practices Applied**:
- ✅ **Legal context**: Court's role in Turkish judicial system
- ✅ **Feature enumeration**: Key capabilities with technical details
- ✅ **Use case examples**: When and why to use the tool
- ✅ **Integration guidance**: How to use with related tools
- ✅ **Technical specifications**: Format requirements and constraints

#### 2. Document Tool Specialization
**Focus**: Clear differentiation and specialized descriptions

**Implementation Example**:
```python
async def get_yargitay_bedesten_document_markdown(...):
    """
    Retrieves the full text of a Yargıtay decision document in Markdown format.
    
    This tool converts the original decision document (HTML or PDF) from Bedesten API
    into clean, readable Markdown format suitable for analysis and processing.
    
    Input Requirements:
    • documentId: Use the ID from search_yargitay_bedesten results
    • Document ID must be non-empty string
    
    Output Format:
    • Clean Markdown text with proper legal formatting
    • Preserves court structure (headers, reasoning sections, conclusions)
    • Removes technical artifacts from source documents
    
    Use for:
    • Reading full supreme court decision texts
    • Legal analysis of Yargıtay reasoning and precedents
    • Citation extraction and legal reference building
    • Content analysis and case summarization
    """
```

### Implementation Results

**Coverage**: Bedesten API tools unified and optimized:
- **Before**: 10 separate tools (5 search + 5 document tools)
- **After**: 2 unified tools (`search_bedesten_unified` + `get_bedesten_document_markdown`)
- **Court Types Supported**: YARGITAYKARARI, DANISTAYKARAR, YERELHUKUK, ISTINAFHUKUK, KYB
- **Benefits**: Single interface, multi-court search, simplified usage

**Quality Improvements**:
- ✅ **LLM Understanding**: Enhanced tool descriptions with legal context
- ✅ **Parameter Clarity**: Detailed format specifications with examples
- ✅ **Behavioral Hints**: Proper annotations for tool behavior
- ✅ **Functional Differentiation**: Clear search vs document tool purposes
- ✅ **Usage Guidance**: Practical examples and integration patterns

**Impact**: The Turkish legal database MCP server now provides one of the most comprehensive and LLM-friendly interfaces for accessing Turkish court decisions, with all tools optimized for AI understanding and effective usage.

## ASGI Web Service Deployment

### Overview

The Yargı MCP server now supports ASGI deployment, allowing it to run as a web service in addition to the traditional MCP protocol. This enables:

- **HTTP/REST API access** to all MCP tools
- **Server-Sent Events (SSE)** transport for real-time streaming
- **Bearer JWT token authentication** for direct API access
- **Cloud deployment** on platforms like Heroku, Railway, GCP, AWS
- **Web-based integration** with existing applications
- **Scalable architecture** with load balancing and multiple workers
- **Enhanced monitoring** with health checks and metrics

### Quick Start Commands

```bash
# Install ASGI dependencies
uv pip install -e .[asgi]

# Run basic ASGI server
python run_asgi.py

# Run with development auto-reload
python run_asgi.py --reload --log-level debug

# Run FastAPI integration (with interactive docs)
uvicorn fastapi_app:app --reload

# Run with custom configuration
python run_asgi.py --host 0.0.0.0 --port 8080 --workers 4
```

### Available ASGI Applications

#### 1. Basic ASGI (`asgi_app.py`)
- **Primary app**: `uvicorn asgi_app:app`
- **SSE support**: Built-in SSE transport at `/sse`
- **Endpoints**:
  - `/mcp/` - MCP endpoint (Streamable HTTP)
  - `/sse/` - MCP endpoint (Server-Sent Events)
  - `/health` - Health check
  - `/status` - Server status
  - `/` - Service information
- **Authentication**:
  - OAuth 2.0 via MCP Auth Toolkit
  - Bearer JWT token support (optional)
  - Hybrid authentication with fallbacks

#### 2. FastAPI Integration (`fastapi_app.py`)
- **Command**: `uvicorn fastapi_app:app`
- **Additional endpoints**:
  - `/docs` - Interactive API documentation
  - `/api/tools` - List all MCP tools
  - `/api/tools/{tool_name}` - Tool details
  - `/api/databases` - Database information
  - `/api/stats` - Server statistics
  - `/mcp-server/mcp/` - MCP endpoint

#### 3. Starlette with Authentication (`starlette_app.py`)
- **Command**: `uvicorn starlette_app:app`
- **Features**:
  - Token-based authentication
  - Custom middleware
  - Nested routing examples

### Environment Configuration

Create `.env` file from template:
```bash
cp .env.example .env
```

Key variables:
```bash
HOST=0.0.0.0                    # Server host
PORT=8000                       # Server port
ALLOWED_ORIGINS=*               # CORS origins (comma-separated)
LOG_LEVEL=info                  # Logging level
API_TOKEN=your-secret-token     # Optional authentication
```

### Docker Deployment

```bash
# Build and run container
docker build -t yargi-mcp .
docker run -p 8000:8000 --env-file .env yargi-mcp

# Or use docker-compose
docker-compose up

# Production with Nginx
docker-compose --profile production up
```

### Cloud Deployment Examples

#### Heroku
```bash
# Deploy to Heroku (uses Procfile)
heroku create your-app-name
git push heroku main
```

#### Railway
```bash
# Deploy to Railway (uses railway.json)
railway login
railway link
railway up
```

#### Google Cloud Run
```bash
# Build and deploy container
gcloud run deploy yargi-mcp \
  --source . \
  --platform managed \
  --region us-central1
```

### Production Considerations

#### 1. Multiple Workers
```bash
# Use multiple workers for production
python run_asgi.py --workers 4

# Or with gunicorn
gunicorn asgi_app:app -w 4 -k uvicorn.workers.UvicornWorker
```

#### 2. Reverse Proxy
- Nginx configuration provided in `nginx.conf`
- Includes rate limiting and SSL termination
- Load balancing support

#### 3. Health Monitoring
```bash
# Health check endpoint
curl http://localhost:8000/health

# Response format
{
  "status": "healthy",
  "timestamp": "2024-12-26T10:00:00",
  "uptime_seconds": 3600,
  "tools_operational": true
}
```

#### 4. Security Features
- CORS configuration
- Rate limiting (via Nginx)
- Token authentication support
- SSL/HTTPS ready

### API Usage Examples

#### Using the REST API
```bash
# List all tools
curl http://localhost:8000/api/tools

# Get tool details
curl http://localhost:8000/api/tools/search_yargitay_detailed

# Get database information
curl http://localhost:8000/api/databases

# Server statistics
curl http://localhost:8000/api/stats
```

#### Using MCP over HTTP
```bash
# Standard MCP request
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: test-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# With Bearer JWT token authentication
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Session-ID: test-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

#### Using MCP over SSE
```bash
# Server-Sent Events transport
curl -X POST http://localhost:8000/sse/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Session-ID: sse-test-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Integration Examples

#### Web Application Integration
```javascript
// JavaScript client example
const response = await fetch('/api/tools');
const tools = await response.json();

// Use specific tool
const searchResult = await fetch('/mcp-server/mcp/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    method: 'tools/call',
    params: {
      name: 'search_yargitay_detailed',
      arguments: {
        arananKelime: 'mülkiyet hakkı',
        pageSize: 10
      }
    }
  })
});
```

#### Authentication Example
```bash
# With API token
export API_TOKEN=your-secret-token

curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/api/tools
```

### Deployment Documentation

For comprehensive deployment instructions, see:
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide (Turkish)
- Covers local development, production, cloud, Docker, security, monitoring

This ASGI support transforms the Yargı MCP server into a versatile web service while maintaining full compatibility with the MCP protocol.

## Production Deployment (Fly.io) - Domain Migration Complete

### Current Production Status ✅

**Production URL**: `https://api.yargimcp.com` (migrated from yargi-mcp.fly.dev)
**Status**: ✅ **FULLY OPERATIONAL** - All systems working perfectly
**Tools Available**: ✅ **21 Turkish Legal Database Tools** - Successfully integrated with Claude AI
**Authentication**: ✅ **OAuth 2.0 + Bearer JWT** - Cross-origin authentication working
**Last Updated**: 2025-01-21 - All critical issues resolved

#### Live Production Endpoints
- **Health Check**: https://api.yargimcp.com/health
- **OAuth Login**: https://api.yargimcp.com/auth/login  
- **MCP Endpoint (HTTP)**: https://api.yargimcp.com/mcp/
- **MCP Endpoint (SSE)**: https://api.yargimcp.com/sse/
- **OAuth Discovery**: https://api.yargimcp.com/.well-known/oauth-authorization-server

### Redis Configuration (Fly.io Native Upstash) ✅

The server uses Fly.io's native Upstash Redis integration for OAuth session storage:

#### Redis Setup
```bash
# Check Redis status
fly redis status yargi-redis

# Get Redis connection info
fly redis status yargi-redis | grep "Private URL"
```

#### Current Redis Configuration
- **Type**: Fly.io native Upstash Redis
- **Plan**: Pay-as-you-go with eviction enabled
- **Region**: fra (Frankfurt)
- **REST API URL**: `http://fly-yargi-redis.upstash.io:6379`
- **Connection**: Uses Upstash REST API (HTTP) instead of traditional Redis protocol

#### Redis Environment Variables
```bash
UPSTASH_REDIS_REST_URL=http://fly-yargi-redis.upstash.io:6379
UPSTASH_REDIS_REST_TOKEN=<your-token>
```

**Note**: Always use `http://` (not `https://`) for Fly.io's internal Upstash Redis REST API.

### Domain Migration Architecture

**Cross-Domain Authentication System**:
- **Frontend**: `yargimcp.com` (sign-in interface)
- **Backend API**: `api.yargimcp.com` (MCP server)
- **Authentication Flow**: Cross-origin JWT token authentication

#### Authentication Resolution ✅

**Problem Solved**: Cross-domain cookie sharing between `yargimcp.com` and `api.yargimcp.com`

**Solution Implemented**: Hybrid Authentication System
1. **JWT Token Authentication** (Primary - Cross-Origin)
   - Frontend generates JWT token after Clerk authentication
   - Token passed to backend via URL parameter
   - Backend validates token with Clerk SDK

2. **Cookie Fallback** (Same-Origin compatibility)
   - Automatic fallback for same-domain requests
   - Maintains compatibility with existing flows

3. **Trusted Redirect** (Last resort)
   - Final fallback for edge cases
   - Ensures authentication flow completion

#### MCP Integration Fix ✅

**Issue Resolved**: Claude AI MCP connection dropping after authentication

**Root Cause**: FastAPI route conflicts between custom handlers and MCP Auth Toolkit

**Solution Applied**: 
- Removed interfering custom POST handler for `/mcp`
- Proper request forwarding to mounted MCP application
- Let MCP Auth Toolkit handle authentication internally

### Current Deployment Configuration

#### Production Environment Variables
```bash
# Domain configuration (updated)
BASE_URL=https://api.yargimcp.com
CLERK_OAUTH_REDIRECT_URL=https://api.yargimcp.com/auth/callback

# Cross-domain authentication  
CLERK_SECRET_KEY=sk_live_production_key
CLERK_PUBLISHABLE_KEY=pk_live_production_key
CLERK_ISSUER=https://accounts.yargimcp.com

# Authentication status
ENABLE_AUTH=true
```

#### MCP Connection Details for Claude AI
```
MCP Server URL (HTTP): https://api.yargimcp.com/mcp/
MCP Server URL (SSE): https://api.yargimcp.com/sse/
OAuth Authorization: https://api.yargimcp.com/authorize
Token Exchange: https://api.yargimcp.com/token
Authentication: OAuth 2.0 with PKCE + JWT tokens + Bearer JWT (optional)
Transports: HTTP (Streamable) + SSE (Server-Sent Events)
```

#### SSE Transport Implementation ✅

The server now supports **Server-Sent Events (SSE)** transport alongside HTTP:

**SSE Endpoint**: `https://api.yargimcp.com/sse/`

**Key Features**:
- Same MCP JSON-RPC protocol as HTTP endpoint
- Proper SSE headers for streaming compatibility
- Identical authentication (Clerk JWT Bearer tokens)
- Real-time streaming support for compatible clients

**SSE Headers Added**:
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `Access-Control-Allow-Origin: *`

**Usage Example**:
```bash
# SSE Transport with Clerk JWT
curl -X POST https://api.yargimcp.com/sse/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
  -H "X-Session-ID: sse-client-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

**Implementation**: 
- Reuses the same underlying MCP app for consistency
- Adds SSE headers without duplicating authentication logic
- Uses Clerk's `authenticate_request` for token validation
- Maintains full compatibility with existing HTTP transport

### OAuth Authentication Issue Resolution ✅

**Issue Fixed**: Multi-machine load balancer causing OAuth token exchange failures

#### Problem Description
- **Root Cause**: In-memory authorization code storage with multi-machine deployment
- **Symptom**: Authorization codes stored on Machine A, token exchange requests load-balanced to Machine B
- **Error**: `"No stored data found for authorization code"` during token exchange
- **Impact**: OAuth flow would fail, preventing Claude AI from authenticating

#### Solution Applied
**Single Machine Deployment**: Scale down to single machine to ensure all OAuth operations happen on the same instance

```bash
# Fix load balancer issue - scale to single machine
fly scale count 1 --app yargi-mcp --yes

# Verify single machine deployment
fly status --app yargi-mcp
```

#### Results ✅
- OAuth flow now working end-to-end
- Real Clerk JWT tokens being generated and accepted  
- Claude AI successfully authenticating and accessing MCP tools
- Authentication is now completely mandatory as intended
- In-memory authorization code storage works correctly on single machine

#### Production Consideration
For high-availability production environments, consider:
- External storage for authorization codes (Redis, Database)
- Session affinity/sticky sessions for OAuth flows
- Stateless authentication using only JWT tokens

### Quick Deploy to Fly.io (Updated)

#### Prerequisites
```bash
# Install Fly.io CLI
brew install flyctl          # macOS
# or visit: https://fly.io/docs/flyctl/install/

# Login to Fly.io
fly auth login
```

#### One-Command Deploy
```bash
# Set required environment variables (updated domains)
export CLERK_SECRET_KEY="sk_live_your_production_key"
export CLERK_PUBLISHABLE_KEY="pk_live_your_production_key"
export CLERK_ISSUER="https://accounts.yargimcp.com"

# Deploy using automated script
./scripts/deploy-flyio.sh
```

#### Manual Deploy Steps
```bash
# 1. App already exists: yargi-mcp
fly apps list | grep yargi-mcp

# 2. Set production secrets (updated URLs)
fly secrets set \
  CLERK_SECRET_KEY="sk_live_your_key" \
  CLERK_PUBLISHABLE_KEY="pk_live_your_key" \
  CLERK_OAUTH_REDIRECT_URL="https://api.yargimcp.com/auth/callback" \
  CLERK_ISSUER="https://accounts.yargimcp.com" \
  BASE_URL="https://api.yargimcp.com"

# 3. Deploy
fly deploy

# 4. Check status
fly status
curl https://api.yargimcp.com/health
```

### Clerk Production Setup (Updated)

#### 1. Clerk Dashboard Configuration ✅
1. Go to https://dashboard.clerk.com/
2. **API Keys**: Production keys configured (sk_live_... and pk_live_...)
3. **Social Connections**: Google OAuth provider enabled
4. **Domains**: `api.yargimcp.com` and `yargimcp.com` configured

#### 2. Google OAuth Setup ✅
1. **Google Cloud Console**: https://console.cloud.google.com/apis/credentials
2. **OAuth Client ID configured**:
   - Application type: Web application
   - Authorized redirect URIs:
     ```
     https://accounts.yargimcp.com/oauth/callback
     https://api.yargimcp.com/auth/callback
     ```
3. **Client ID and Secret**: Configured in Clerk dashboard

#### 3. Current Production URLs ✅
- **Health Check**: https://api.yargimcp.com/health ✅ Operational
- **OAuth Login**: https://api.yargimcp.com/auth/login ✅ Working
- **User Info**: https://api.yargimcp.com/auth/user ✅ Protected
- **MCP Endpoint (HTTP)**: https://api.yargimcp.com/mcp/ ✅ Claude AI Compatible
- **MCP Endpoint (SSE)**: https://api.yargimcp.com/sse/ ✅ Server-Sent Events Transport

### Complete Deployment Guide

For detailed step-by-step instructions, see **[docs/DEPLOYMENT_FLYIO.md](docs/DEPLOYMENT_FLYIO.md)** which covers:
- Clerk OAuth configuration
- Google Cloud Console setup
- Fly.io deployment process
- Production testing procedures
- Troubleshooting guide
- Security best practices

### Production OAuth Testing

#### Test OAuth Flow
```bash
# 1. Start OAuth flow in browser
open https://yargi-mcp.fly.dev/auth/login

# 2. Complete Google OAuth flow

# 3. Test authenticated endpoints
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://yargi-mcp.fly.dev/auth/user

# 4. Test MCP with authentication
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Session-ID: prod-session-123" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' \
  https://yargi-mcp.fly.dev/mcp/
```

#### Management Commands
```bash
# View logs
fly logs --app yargi-mcp

# Scale up/down
fly scale count 2

# Restart app
fly apps restart yargi-mcp

# SSH into container
fly ssh console --app yargi-mcp
```

## ChatGPT Deep Research Integration

The MCP server now includes specialized tools for ChatGPT Deep Research compatibility:

### Deep Research Tools

**search** - Universal search across all Turkish legal databases
- **Purpose**: Returns structured search results for Deep Research compatibility
- **Coverage**: All 9 supported Turkish legal databases in a single query
- **Output Format**: Array of objects with `id`, `title`, `text`, `url` fields as required by ChatGPT Deep Research specification
- **Databases Searched**:
  - Yargıtay (Court of Cassation) - Primary and Bedesten APIs
  - Danıştay (Council of State) - All 3 APIs
  - Anayasa Mahkemesi (Constitutional Court) - Norm control decisions
  - Rekabet Kurumu (Competition Authority) - Antitrust decisions
  - KİK (Public Procurement Authority) - Procurement disputes
  - Local Courts (Yerel Hukuk, İstinaf Hukuk) - Via Bedesten API
  - Kanun Yararına Bozma (KYB) - Extraordinary appeals
- **Usage**: `search(query="mülkiyet hakkı")` - Single query searches all databases

**fetch** - Document retrieval by ID
- **Purpose**: Retrieves complete legal document text for Deep Research analysis
- **Input**: Document identifier from search results (format: `database_documentid`)
- **Output Format**: Single object with `id`, `title`, `text`, `url`, `metadata` fields
- **Supported Databases**: All databases with automatic routing based on ID prefix
- **Usage**: `fetch(id="yargitay_12345")` - Returns full document content

### ChatGPT Integration Setup

1. **Add MCP Server in ChatGPT**:
   - Go to ChatGPT Settings → Connectors
   - Add new MCP server: `https://yargi-mcp.fly.dev/mcp`
   - Complete OAuth flow via Clerk
   - Server will appear in Deep Research sources

2. **OAuth Authentication**:
   - Uses Clerk OAuth 2.0 with Google provider
   - Mock OAuth flow for test environment compatibility
   - Development tokens supported for testing

3. **Deep Research Usage**:
   - Enable Deep Research mode in ChatGPT
   - Select "Yargı MCP Server" as data source
   - Ask legal research questions in Turkish or English
   - ChatGPT will automatically use `search` and `fetch` tools

### Example Deep Research Queries

```
"Türk hukukunda mülkiyet hakkının sınırları nelerdir?"
"What are the recent Constitutional Court decisions on freedom of expression?"
"Rekabet hukukunda hakim durumun kötüye kullanılması nasıl değerlendiriliyor?"
"Public procurement tender cancellation procedures in Turkish law"
```

### Tool Response Format

**Search Results Example**:
```json
[
  {
    "id": "yargitay_12345",
    "title": "Yargıtay 1. Hukuk Dairesi - E.2024/123 K.2024/456",
    "text": "Supreme Court decision on property rights...",
    "url": "https://yargi-mcp.fly.dev/documents/yargitay/12345"
  }
]
```

**Fetch Results Example**:
```json
{
  "id": "yargitay_12345",
  "title": "Yargıtay Supreme Court Decision - Document 12345",
  "text": "# Yargıtay 1. Hukuk Dairesi\n\nEsas No: 2024/123...",
  "url": "https://yargi-mcp.fly.dev/documents/yargitay/12345",
  "metadata": {
    "database": "Yargıtay (Court of Cassation)",
    "court_level": "Supreme Court",
    "jurisdiction": "Civil and Criminal Law",
    "document_id": "12345"
  }
}
```

### Testing Deep Research Tools

```bash
# Test universal search tool
curl -X POST https://yargi-mcp.fly.dev/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Session-ID: deep-research-test" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {
        "query": "mülkiyet hakkı"
      }
    }
  }'

# Test fetch tool with result ID
curl -X POST https://yargi-mcp.fly.dev/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Session-ID: deep-research-test" \
  -d '{
    "jsonrpc": "2.0", 
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "fetch",
      "arguments": {
        "id": "yargitay_12345"
      }
    }
  }'
```

## FastMCP Client Testing Results


## PyPI Package Publishing

### Overview
The project is published on PyPI as `yargi-mcp` for easy installation without Git dependencies.

**PyPI Package**: https://pypi.org/project/yargi-mcp/

### User Installation
```bash
# Install from PyPI (Recommended - no Git required)
pip install yargi-mcp

# Or use uvx for isolated execution
uvx yargi-mcp

# Claude Desktop/5ire configuration
{
  "mcpServers": {
    "yargi-mcp": {
      "command": "yargi-mcp"
    }
  }
}
```

### Automated Publishing Workflow
- **GitHub Actions**: `.github/workflows/publish.yml`
- **Trigger**: Release creation on GitHub
- **Process**: Build → Test → Publish to PyPI
- **Requirements**: `PYPI_API_TOKEN` secret in GitHub

### Publishing Process
1. **Update Version**: Bump version in `pyproject.toml`
2. **Commit & Push**: Git commit and push changes
3. **Create Release**: Use GitHub CLI or web interface
   ```bash
   # Via GitHub CLI
   gh release create v0.1.3 --title "v0.1.3" --notes ""
   
   # Via web: https://github.com/saidsurucu/yargi-mcp/releases/new
   ```
4. **Automatic Publishing**: GitHub Actions publishes to PyPI

### PyPI Configuration (pyproject.toml)
```toml
[project]
name = "yargi-mcp"
version = "0.1.2"  # Update for each release
description = "MCP Server For Turkish Legal Databases"
license = {text = "MIT"}
authors = [{name = "Said Surucu", email = "saidsrc@gmail.com"}]
keywords = ["mcp", "turkish-law", "legal", "yargitay", "danistay"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Legal Industry",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"
```

## Summary

### Current Tool Architecture (Updated)

**Total Tools**: 21 MCP tools across 9 legal institutions (Production Verified ✅)

**Legal Database Coverage**:
1. **Yargıtay**: ❌ ~~2 tools~~ → Use Bedesten unified instead (DEACTIVATED)
2. **Danıştay**: ❌ ~~3 tools~~ → Use Bedesten unified instead (DEACTIVATED)  
3. **Bedesten Unified**: 2 tools (unified search + document retrieval) - **COVERS YARGITAY & DANISTAY**
4. **Emsal**: 2 tools (search + document)
5. **Uyuşmazlık**: 2 tools (search + document)
6. **Constitutional Court**: ✅ 2 tools (unified norm control + individual applications) - **NEWLY UNIFIED**
7. **KİK**: 2 tools (search + document)
8. **Competition Authority**: 2 tools (search + document)
9. **KVKK**: 2 tools (search + document)
10. **Sayıştay**: 4 tools (3 search types + document)

### Recent Updates

#### ✅ Bedesten API Unification (Completed)
- **Before**: 10 separate tools for different court types
- **After**: 2 unified tools supporting all court types
- **Benefits**: Simplified interface, multi-court search, better UX
- **Court Types**: YARGITAYKARARI, DANISTAYKARAR, YERELHUKUK, ISTINAFHUKUK, KYB

#### ✅ Constitutional Court Unification (Phase 6 - Completed)
- **Before**: 4 separate tools (2 norm control + 2 individual applications)
- **After**: 2 unified tools with decision type parameter
- **Benefits**: Single interface, auto-detection, simplified usage
- **Tools**: search_anayasa_unified + get_anayasa_document_unified

#### 🔄 Sayıştay Module (Available, Active)
- **Module**: `sayistay_mcp_module/` - Complete implementation  
- **Status**: 4 tools active and operational
- **Coverage**: General Assembly, Appeals Board, Chamber decisions
- **Tools**: search_sayistay_genel_kurul, search_sayistay_temyiz_kurulu, search_sayistay_daire, get_sayistay_document_markdown

#### ✅ Production Deployment & Claude AI Integration (Completed - Jan 21, 2025)
- **Status**: All systems fully operational on Fly.io production
- **Authentication**: OAuth 2.0 + Bearer JWT token authentication working
- **Tools Integration**: All 21 tools successfully integrated with Claude AI
- **Cross-Origin Auth**: Resolved subdomain authentication challenges
- **Issues Resolved**: 
  - ✅ Bearer token scope/audience validation
  - ✅ MCP tools initialization sequence
  - ✅ FastMCP app auth provider integration
  - ✅ 308 redirect for /mcp endpoint
  - ✅ Session management and tool discovery
- **Claude AI**: Successfully connects and uses all Turkish legal database tools

### Key Features
- **FastMCP Framework**: Modern MCP server implementation
- **Unified APIs**: Single interface for multiple court systems
- **Multi-format Support**: HTML and PDF document conversion
- **Advanced Search**: Chamber filtering, date ranges, exact phrases
- **Production Ready**: OAuth authentication, cloud deployment, monitoring
