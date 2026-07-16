# Firecrawl Scraper API Configurations

add to ~/.config/local-ai/.env

FIRECRAWL_API_KEY="your-firecrawl-api-key-here"

---

# Web Scraper & YouTube Subtitle Extractor: web-reader


On-device webpage markdown conversion and timestamp-free YouTube transcript extraction.

*   **Dynamic Web Scraping**: Converts any standard webpage into clean Markdown using Jina Reader's free cloud proxy.
*   **YouTube Transcripts**: Uses native `yt-dlp` to extract auto-subtitles, stripping timestamps and collapsing scrolling duplicates.
*   **Interactive Prompts**: Prompts you dynamically in your terminal if launched without a URL, bypassing stdout pipes.

---

### Expected Behavior

If you launch the tool in your active session with no URL:
```console
~ ❯ web reader
[02/02] ❯ [web reader yt] ~/.config/local-ai/tools/agentic/web/web-reader youtube $1 | mdcat
:: ↵ run  Esc: 
❯ Enter Youtube URL to process: 
```

