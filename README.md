# inktomd MCP Server

Convert any file or URL to clean AI-ready Markdown directly from Claude, Claude Code, Cursor, or any MCP-compatible AI agent.

inktomd reduces token usage by up to 63% by converting raw documents to clean Markdown — the format AI models were trained on.

## Tools

| Tool | Description |
|------|-------------|
| `convert_url` | Convert any webpage, article, or web document to Markdown |
| `convert_file` | Convert a local file (PDF, Word, Excel, and more) to Markdown |
| `convert_youtube` | Extract YouTube video transcript as Markdown |
| `convert_arxiv` | Convert ArXiv research paper to Markdown |
| `list_supported_formats` | List all supported file formats and URL types |

## Supported Formats

**Files:** PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), EPUB, HTML, CSV, JSON, XML, Jupyter (.ipynb), Email (.eml/.msg), ZIP, 7-Zip (.7z)

**URLs:** Any webpage, YouTube, ArXiv, Wikipedia, Substack, RSS feeds, Google Docs, GitHub

## Installation & Configuration

### Claude Desktop

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "inktomd": {
      "command": "uvx",
      "args": ["inktomd-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add inktomd uvx inktomd-mcp
```

Or add to `.claude/settings.json` in your project:

```json
{
  "mcpServers": {
    "inktomd": {
      "command": "uvx",
      "args": ["inktomd-mcp"]
    }
  }
}
```

### Cursor

Go to Cursor Settings → Features → MCP → Add new MCP server:

```json
{
  "inktomd": {
    "command": "uvx",
    "args": ["inktomd-mcp"]
  }
}
```

### Run from source

```bash
git clone https://github.com/hadirizvi093/inktomd
cd inktomd/mcp
pip install -r requirements.txt
python server.py
```

## Usage Examples

**Convert a research paper:**
> Convert this ArXiv paper to Markdown: https://arxiv.org/abs/2301.07041

**Convert a local PDF:**
> Convert /Users/me/documents/report.pdf to Markdown

**Extract a YouTube transcript:**
> Get the transcript from https://youtube.com/watch?v=dQw4w9WgXcQ

**Convert a webpage:**
> Convert https://example.com/article to Markdown

**Check supported formats:**
> What file formats does inktomd support?

## Privacy

Files are processed in-memory on inktomd's backend (Google Cloud Run) and deleted immediately after conversion. Nothing is stored. No authentication required.

## Limits

- Free tier: 10 conversions per day
- Maximum file size: 20MB
- Pro plan: Unlimited conversions — inktomd.com/pricing

## Links

- Website: https://www.inktomd.com
- Pricing: https://www.inktomd.com/pricing
- Contact: hadi@inktomd.com
