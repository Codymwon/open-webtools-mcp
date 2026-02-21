# Web Search MCP Server (Free)

A free MCP server providing web search, website reading, and YouTube transcript tools for LLMStudio and other MCP clients. Uses DuckDuckGo — no API keys required.

## Installation

1.  **Prerequisites**: Python 3.10+
2.  **Clone/Download**: Get this repository.
3.  **Setup Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/macOS
    source .venv/bin/activate

    pip install -r requirements.txt
    ```

## Usage

Configure the MCP server in your client settings:

```json
{
  "mcpServers": {
    "web-search": {
      "command": "<path-to-repo>/.venv/Scripts/python.exe",
      "args": ["<path-to-repo>/server.py"]
    }
  }
}
```

Or run directly:
```bash
python server.py
```

## Tools

| Tool | Description |
|---|---|
| `search_web(query, max_results=5)` | Search the web via DuckDuckGo. Returns JSON array of results with title, href, and body. Hard cap of 10 results. |
| `read_website(url)` | Extract main text content from a webpage URL. Output truncated to 15 000 chars for long pages. |
| `get_youtube_transcript(video_id_or_url)` | Get the text transcript of a YouTube video. Accepts video IDs and all common URL formats (`/watch`, `youtu.be`, `/shorts/`, `/embed/`, `/live/`). |

## Troubleshooting

- **"command not found"**: Use the full path to the python executable inside `.venv`.
- **Empty search results**: Ensure `ddgs` is up to date (`pip install --upgrade ddgs`).
- **SSL errors on read_website**: The server uses `no_ssl=True` by default to avoid cert issues.
