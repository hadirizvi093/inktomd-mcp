import os
import uvicorn
import pathlib
import httpx
from mcp.server.fastmcp import FastMCP
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window: int = 3600):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.requests: dict = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.headers.get("x-forwarded-for", 
                    request.client.host if request.client else "unknown")
        client_ip = client_ip.split(",")[0].strip()
        now = time.time()
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] 
            if now - t < self.window
        ]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                {"error": "Rate limit exceeded. Maximum 30 requests per hour per IP."},
                status_code=429
            )
        
        self.requests[client_ip].append(now)
        return await call_next(request)

API_BASE = "https://www.inktomd.com/api"
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SERVER_NAME = "inktomd"
SERVER_VERSION = "0.1.0"

SUPPORTED_EXTENSIONS = {
    ".pdf", ".doc", ".docx",
    ".xls", ".xlsx",
    ".ppt", ".pptx",
    ".epub",
    ".html", ".htm",
    ".csv",
    ".json",
    ".xml",
    ".ipynb",
    ".eml", ".msg",
    ".zip", ".7z"
}

SUPPORTED_FORMATS_DESCRIPTION = {
    "PDF (.pdf)": "Research papers, reports, ebooks, scanned documents",
    "Word (.doc, .docx)": "Business documents, essays, proposals",
    "Excel (.xls, .xlsx)": "Spreadsheets, data tables, financial models",
    "PowerPoint (.ppt, .pptx)": "Presentations, slide decks, pitch decks",
    "EPUB (.epub)": "Ebooks, digital publications",
    "HTML (.html, .htm)": "Web pages, exported websites",
    "CSV (.csv)": "Comma-separated data, database exports",
    "JSON (.json)": "API responses, configuration files, data exports",
    "XML (.xml)": "Structured data, configuration files",
    "Jupyter Notebook (.ipynb)": "Data science notebooks with code and output",
    "Email (.eml, .msg)": "Email files from Outlook and standard email clients",
    "ZIP archive (.zip)": "Archives containing multiple supported documents",
    "7-Zip archive (.7z)": "Compressed archives containing multiple documents",
}

SUPPORTED_URLS_DESCRIPTION = {
    "Any webpage": "Articles, blog posts, documentation pages",
    "YouTube": "Video transcripts from any public video with captions",
    "ArXiv": "Research papers via arxiv.org/abs/ or arxiv.org/pdf/ links",
    "Wikipedia": "Any Wikipedia article in any language",
    "Substack": "Newsletter posts from any public Substack",
    "RSS feeds": "Any RSS feed URL returns structured article list",
    "Google Docs": "Any public Google Doc (set to Anyone with link can view)",
    "GitHub": "README files, repository pages, GitHub Gists",
}

mcp = FastMCP(name=SERVER_NAME)

@mcp.tool()
async def convert_url(url: str) -> str:
    """Convert any URL to clean AI-ready Markdown. Supports webpages, YouTube videos, ArXiv papers, Wikipedia articles, Substack newsletters, RSS feeds, Google Docs, GitHub pages, and more. Returns Markdown with up to 63% fewer tokens than the raw source HTML."""
    if not (url.startswith("http://") or url.startswith("https://")):
        return "Invalid URL. Must start with http:// or https://"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{API_BASE}/convert-url", json={"url": url})
            if response.status_code == 200:
                data = response.json()
                return data.get("markdown", "")
            else:
                return f"Conversion failed (HTTP {response.status_code}): {response.text}"
    except httpx.TimeoutException:
        return "Request timed out after 60 seconds. The URL may be slow to load or the content is very large."
    except httpx.RequestError:
        return "Network error: could not reach inktomd API. Check your internet connection."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
async def convert_file(file_path: str) -> str:
    """Convert a local file to clean AI-ready Markdown. Supports PDF, Word (.doc/.docx), Excel (.xls/.xlsx), PowerPoint (.ppt/.pptx), EPUB, HTML, CSV, JSON, XML, Jupyter notebooks (.ipynb), Email files (.eml/.msg), ZIP archives (.zip), and 7-Zip archives (.7z). Provide the absolute file path. Maximum file size: 20MB."""
    path = pathlib.Path(file_path)
    
    if not path.exists() or not path.is_file():
        return f"File not found: {file_path}"
        
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f"Unsupported format: '{ext}'. Supported extensions: {sorted(list(SUPPORTED_EXTENSIONS))}"
        
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return f"File is too large ({size / 1024 / 1024:.1f}MB). inktomd supports files up to {MAX_FILE_SIZE_MB}MB."
        
    try:
        file_bytes = path.read_bytes()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"file": (path.name, file_bytes)}
            response = await client.post(f"{API_BASE}/convert", files=files)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("markdown", "")
            elif response.status_code == 400:
                return f"Conversion error: {response.text}. The file may be corrupted, password-protected, or in an unsupported variant of the format."
            elif response.status_code == 413:
                return "File too large for server processing. Try splitting the document into smaller parts."
            elif response.status_code >= 500:
                return f"Server error during conversion: {response.text}"
            else:
                return f"Conversion failed (HTTP {response.status_code}): {response.text}"
    except httpx.TimeoutException:
        return "Conversion timed out. Large files may take longer — try a smaller file or split the document."
    except httpx.RequestError:
        return "Network error: could not reach inktomd API."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
async def convert_youtube(url: str) -> str:
    """Extract the full transcript from any public YouTube video as clean Markdown. Works with standard watch links (youtube.com/watch?v=) and short links (youtu.be/). The video must have captions enabled — including auto-generated captions. Returns the transcript as flowing Markdown paragraphs, not raw caption fragments."""
    if "youtube.com" not in url and "youtu.be" not in url:
        return "Not a YouTube URL. Please provide a URL starting with youtube.com or youtu.be"
        
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{API_BASE}/convert-url", json={"url": url})
            if response.status_code == 200:
                data = response.json()
                return data.get("markdown", "")
            else:
                return "Could not extract transcript. The video may be private, have captions disabled, or be unavailable in your region."
    except httpx.TimeoutException:
        return "Request timed out after 60 seconds. The URL may be slow to load or the content is very large."
    except httpx.RequestError:
        return "Network error: could not reach inktomd API. Check your internet connection."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
async def convert_arxiv(url: str) -> str:
    """Convert any ArXiv research paper to clean structured Markdown. Accepts both abstract page URLs (arxiv.org/abs/PAPER_ID) and direct PDF links (arxiv.org/pdf/PAPER_ID). Returns the full paper content with headings, sections, and content preserved — uses significantly fewer tokens than the PDF format for AI analysis."""
    if "arxiv.org" not in url:
        return "Not an ArXiv URL. Please provide a URL from arxiv.org (e.g., https://arxiv.org/abs/2301.07041)"
        
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{API_BASE}/convert-url", json={"url": url})
            if response.status_code == 200:
                data = response.json()
                return data.get("markdown", "")
            else:
                return "Could not convert paper. The paper may not exist, be embargoed, or temporarily unavailable."
    except httpx.TimeoutException:
        return "Request timed out after 90 seconds. The URL may be slow to load or the content is very large."
    except httpx.RequestError:
        return "Network error: could not reach inktomd API. Check your internet connection."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
async def list_supported_formats() -> str:
    """List all file formats and URL types that inktomd supports for conversion to Markdown. Use this to check whether a specific file type or URL source is supported before attempting conversion."""
    lines = ["# inktomd Supported Formats\n"]
    lines.append("## File Formats\n")
    for fmt, desc in SUPPORTED_FORMATS_DESCRIPTION.items():
        lines.append(f"- **{fmt}** — {desc}")
    lines.append("\n## URL Sources\n")
    for src, desc in SUPPORTED_URLS_DESCRIPTION.items():
        lines.append(f"- **{src}** — {desc}")
    lines.append(f"\n## Limits\n- Maximum file size: {MAX_FILE_SIZE_MB}MB\n- Free tier: 10 conversions per day\n- Pro: Unlimited (inktomd.com/pricing)")
    
    return "\n".join(lines)

if __name__ == "__main__":
    import os
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    
    port = int(os.environ.get("PORT", 8080))
    
    # Get the FastMCP app and disable host checking
    app = mcp.streamable_http_app()
    
    async def health_check(request: Request):
        return JSONResponse({"status": "ok"})
        
    app.add_route("/", health_check)
    
    # Remove any existing TrustedHostMiddleware and add permissive one
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(RateLimitMiddleware, max_requests=30, window=3600)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        forwarded_allow_ips="*",
        proxy_headers=True,
        server_header=False,
        headers=[("server", "inktomd")]
    )
