<h2 align="center">Firecrawl</h2>

add to .env

### Firecrawl Scraper API Configurations
FIRECRAWL_API_KEY="your-firecrawl-api-key-here"

<h2 align="center">Web Scraper & YouTube Subtitle Extractor: web-reader</h2>

<p align="center">
  <em>On-device webpage markdown conversion and timestamp-free YouTube transcript extraction.</em>
</p>

*   **Dynamic Web Scraping**: Converts any standard webpage into clean Markdown using Jina Reader's free cloud proxy.
*   **YouTube Transcripts**: Uses native `yt-dlp` to extract auto-subtitles, stripping timestamps and collapsing scrolling duplicates.
*   **Interactive Prompts**: Prompts you dynamically in your terminal if launched without a URL, bypassing stdout pipes.

---

### Expected Behavior

If you launch the tool in your active session with no URL:
```console
❯ web reader
❯ Enter Web URL to process: https://en.wikipedia.org/wiki/Artificial_intelligence
```

