import os
import pathlib
import httpx
from mcp.server.fastmcp import FastMCP

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

mcp = FastMCP(
    name=SERVER_NAME,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8080))
)

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

@mcp.tool()
async def count_tokens(text: str, model: str = "gpt-4o") -> str:
    """
    Count the exact number of tokens in a text string for a specific AI model.
    Uses tiktoken for OpenAI models and estimates for others.
    
    Args:
        text: The text to count tokens for
        model: The AI model to count tokens for. Options: gpt-4o, gpt-4o-mini, 
               gpt-4.1, claude-sonnet, claude-haiku, gemini-pro, gemini-flash,
               llama-4, deepseek-v3, mistral-large. Default: gpt-4o
    
    Returns:
        Token count information including count, context window, and fit status
    """
    import tiktoken
    
    MODEL_INFO = {
        "gpt-4o": {"context": 128000, "price": 2.50, "tokenizer": "cl100k_base", "ratio": 1.0},
        "gpt-4o-mini": {"context": 128000, "price": 0.15, "tokenizer": "cl100k_base", "ratio": 1.0},
        "gpt-4.1": {"context": 1000000, "price": 2.00, "tokenizer": "cl100k_base", "ratio": 1.0},
        "gpt-4.1-mini": {"context": 1000000, "price": 0.40, "tokenizer": "cl100k_base", "ratio": 1.0},
        "o3": {"context": 200000, "price": 10.00, "tokenizer": "cl100k_base", "ratio": 1.0},
        "claude-sonnet": {"context": 200000, "price": 3.00, "tokenizer": "cl100k_base", "ratio": 1.1},
        "claude-haiku": {"context": 200000, "price": 1.00, "tokenizer": "cl100k_base", "ratio": 1.1},
        "claude-opus": {"context": 200000, "price": 5.00, "tokenizer": "cl100k_base", "ratio": 1.1},
        "gemini-pro": {"context": 2000000, "price": 1.25, "tokenizer": "cl100k_base", "ratio": 0.85},
        "gemini-flash": {"context": 1000000, "price": 0.30, "tokenizer": "cl100k_base", "ratio": 0.85},
        "llama-4": {"context": 128000, "price": 0.15, "tokenizer": "cl100k_base", "ratio": 1.05},
        "deepseek-v3": {"context": 128000, "price": 0.27, "tokenizer": "cl100k_base", "ratio": 1.0},
        "mistral-large": {"context": 128000, "price": 0.50, "tokenizer": "cl100k_base", "ratio": 1.0},
    }
    
    model_key = model.lower().replace(" ", "-")
    if model_key not in MODEL_INFO:
        model_key = "gpt-4o"
    
    info = MODEL_INFO[model_key]
    
    try:
        enc = tiktoken.get_encoding(info["tokenizer"])
        base_tokens = len(enc.encode(text))
    except Exception:
        base_tokens = len(text.split()) * 4 // 3
    
    token_count = int(base_tokens * info["ratio"])
    context_window = info["context"]
    fits = token_count <= context_window
    cost = (token_count / 1_000_000) * info["price"]
    remaining = context_window - token_count
    
    result = f"""# Token Count for {model}

**Token count:** {token_count:,} tokens
**Context window:** {context_window:,} tokens
**Fits in context:** {'✅ Yes' if fits else '❌ No — exceeds context window by ' + str(abs(remaining):,) + ' tokens'}
**Tokens remaining:** {max(0, remaining):,} tokens
**Processing cost:** ${cost:.4f}
**Price per million tokens:** ${info['price']}

## All Models Comparison

| Model | Tokens | Context | Fits | Cost |
|-------|--------|---------|------|------|
"""
    
    for m, i in MODEL_INFO.items():
        t = int(base_tokens * i["ratio"])
        f = "✅" if t <= i["context"] else "❌"
        c = (t / 1_000_000) * i["price"]
        result += f"| {m} | {t:,} | {i['context']:,} | {f} | ${c:.4f} |\n"
    
    return result

@mcp.tool()
async def convert_batch(urls: list[str]) -> str:
    """
    Convert multiple URLs to Markdown in a single call. 
    Maximum 10 URLs per batch. Each URL is converted independently.
    
    Args:
        urls: List of URLs to convert. Maximum 10. Each must start with http:// or https://
    
    Returns:
        All converted Markdown documents combined, clearly separated with headers
    """
    if not urls:
        return "Error: No URLs provided. Please provide a list of URLs to convert."
    
    if len(urls) > 10:
        return f"Error: Maximum 10 URLs per batch. You provided {len(urls)}. Please split into multiple batches."
    
    results = []
    errors = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, url in enumerate(urls, 1):
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                errors.append(f"URL {i}: Invalid URL — must start with http:// or https://")
                continue
            
            try:
                response = await client.post(
                    f"{API_BASE}/convert-url",
                    json={"url": url}
                )
                response.raise_for_status()
                data = response.json()
                markdown = data.get("markdown", "")
                results.append(f"---\n\n## Document {i}: {url}\n\n{markdown}")
            except httpx.TimeoutException:
                errors.append(f"URL {i} ({url}): Timed out after 60 seconds")
            except httpx.HTTPStatusError as e:
                errors.append(f"URL {i} ({url}): HTTP {e.response.status_code}")
            except Exception as e:
                errors.append(f"URL {i} ({url}): {str(e)}")
    
    output = f"# Batch Conversion Results\n\n"
    output += f"**Converted:** {len(results)}/{len(urls)} URLs successfully\n\n"
    
    if errors:
        output += f"**Errors:**\n"
        for err in errors:
            output += f"- {err}\n"
        output += "\n"
    
    output += "\n".join(results)
    return output

@mcp.tool()
async def convert_with_metadata(source: str, source_type: str = "url") -> str:
    """
    Convert a file or URL to Markdown and return both content and structured metadata.
    Metadata includes title, estimated token counts for all major models, word count,
    character count, and reading time.
    
    Args:
        source: Either a URL (starting with http/https) or absolute file path
        source_type: Either "url" or "file". Default: "url"
    
    Returns:
        Markdown content with a metadata header block containing all stats
    """
    import tiktoken
    from pathlib import Path
    
    markdown = ""
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        if source_type == "file":
            path = Path(source)
            if not path.exists():
                return f"Error: File not found: {source}"
            
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return f"Error: Unsupported format: {ext}"
            
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return f"Error: File too large ({file_size / 1024 / 1024:.1f}MB). Maximum: {MAX_FILE_SIZE_MB}MB"
            
            content = path.read_bytes()
            files = {"file": (path.name, content)}
            
            try:
                response = await client.post(f"{API_BASE}/convert", files=files)
                response.raise_for_status()
                markdown = response.json().get("markdown", "")
            except Exception as e:
                return f"Error converting file: {str(e)}"
        else:
            if not source.startswith(("http://", "https://")):
                return "Error: Invalid URL. Must start with http:// or https://"
            
            try:
                response = await client.post(f"{API_BASE}/convert-url", json={"url": source})
                response.raise_for_status()
                markdown = response.json().get("markdown", "")
            except Exception as e:
                return f"Error converting URL: {str(e)}"
    
    # Calculate metadata
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        base_tokens = len(enc.encode(markdown))
    except Exception:
        base_tokens = len(markdown.split()) * 4 // 3
    
    word_count = len(markdown.split())
    char_count = len(markdown)
    reading_time = max(1, word_count // 200)
    
    models = {
        "gpt-4o": (base_tokens, 2.50),
        "claude-sonnet": (int(base_tokens * 1.1), 3.00),
        "gemini-pro": (int(base_tokens * 0.85), 1.25),
        "gpt-4.1": (base_tokens, 2.00),
        "deepseek-v3": (base_tokens, 0.27),
    }
    
    metadata = f"""---
# Document Metadata

| Property | Value |
|----------|-------|
| Source | {source} |
| Word count | {word_count:,} words |
| Character count | {char_count:,} characters |
| Reading time | ~{reading_time} minute{'s' if reading_time != 1 else ''} |

## Token Counts by Model

| Model | Tokens | Cost to Process |
|-------|--------|-----------------|
"""
    
    for model_name, (tokens, price) in models.items():
        cost = (tokens / 1_000_000) * price
        metadata += f"| {model_name} | {tokens:,} | ${cost:.4f} |\n"
    
    metadata += "\n---\n\n"
    
    return metadata + markdown

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
