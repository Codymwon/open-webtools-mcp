import json
import logging
import re
from urllib.parse import urlparse, parse_qs

from mcp.server.fastmcp import FastMCP
from ddgs import DDGS
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
MAX_BODY_CHARS = 200          # Truncate each search result body
MAX_WEBSITE_CHARS = 15000     # Max characters returned from read_website

# Initialize FastMCP server
mcp = FastMCP("Web Search")


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.

    Use this tool to find current information on any topic. Returns a JSON array of
    result objects, each containing:
      - "title": the page title
      - "href": the URL of the result
      - "body": a short snippet/summary of the page (truncated to ~200 chars)

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5, hard cap 10).
    """
    max_results = min(max_results, 10)  # hard cap
    logger.info("Searching for: %s (max_results=%d)", query, max_results)
    try:
        results = list(DDGS().text(query, max_results=max_results))
        # Truncate long body snippets to stay within LLM context limits
        for r in results:
            if "body" in r and len(r["body"]) > MAX_BODY_CHARS:
                r["body"] = r["body"][:MAX_BODY_CHARS] + "..."
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error("Search failed: %s", e)
        return f"Error performing search: {str(e)}"


@mcp.tool()
def read_website(url: str) -> str:
    """
    Extract the main text content from a webpage URL.

    Use this tool when you need to read the full content of a specific webpage.
    Returns the extracted text content, truncated to ~15 000 characters if the
    page is very long. Returns an error string if the fetch or extraction fails.

    Args:
        url: The full URL of the webpage to read (must start with http:// or https://).
    """
    logger.info("Reading website: %s", url)
    try:
        downloaded = trafilatura.fetch_url(url, no_ssl=True)
        if downloaded is None:
            return f"Error: Could not fetch content from {url}"

        text = trafilatura.extract(downloaded)
        if text is None:
            return f"Error: Could not extract text from {url}"

        # Truncate to avoid overwhelming the LLM context window
        if len(text) > MAX_WEBSITE_CHARS:
            text = text[:MAX_WEBSITE_CHARS] + "\n\n... [truncated — content exceeded 15 000 characters]"

        return text
    except Exception as e:
        logger.error("Website read failed for %s: %s", url, e)
        return f"Error reading website: {str(e)}"


def _extract_youtube_video_id(video_id_or_url: str) -> str:
    """Robustly extract a YouTube video ID from various URL formats or a raw ID."""
    raw = video_id_or_url.strip()

    # If it looks like a bare 11-char video ID, return directly
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw

    # Try to parse as a URL
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()

    # Standard: youtube.com/watch?v=ID
    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
        # /shorts/ID, /embed/ID, /live/ID, /v/ID
        for prefix in ("/shorts/", "/embed/", "/live/", "/v/"):
            if parsed.path.startswith(prefix):
                return parsed.path[len(prefix):].split("/")[0].split("?")[0]

    # Shortened: youtu.be/ID
    if host == "youtu.be":
        return parsed.path.lstrip("/").split("/")[0].split("?")[0]

    # Fallback — return the original input and let the API error naturally
    return raw


@mcp.tool()
def get_youtube_transcript(video_id_or_url: str) -> str:
    """
    Get the text transcript of a YouTube video.

    Use this tool to retrieve spoken content from a YouTube video. Accepts a
    video ID (e.g. "dQw4w9WgXcQ") or any common YouTube URL format including
    youtube.com/watch, youtu.be, /shorts/, /embed/, and /live/ links.

    Returns the full transcript as a single string, or an error message if no
    transcript is available.

    Args:
        video_id_or_url: A YouTube video ID or URL.
    """
    logger.info("Fetching transcript for: %s", video_id_or_url)
    try:
        video_id = _extract_youtube_video_id(video_id_or_url)
        logger.info("Resolved video ID: %s", video_id)

        # List all available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to find a manual English transcript, then generated English, then any
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except Exception:
                try:
                    transcript = next(iter(transcript_list))
                except StopIteration:
                    return f"No transcript found for video {video_id}"

        # Fetch the actual transcript data
        transcript_data = transcript.fetch()

        # Combine transcript text
        full_text = " ".join([entry.text for entry in transcript_data])
        return full_text
    except Exception as e:
        logger.error("Transcript fetch failed for %s: %s", video_id_or_url, e)
        return f"Error fetching transcript: {str(e)}"


if __name__ == "__main__":
    mcp.run()
