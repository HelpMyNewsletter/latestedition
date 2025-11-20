import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

RSS_URL = "https://rss.beehiiv.com/feeds/NRMXBlkDdv.xml"


def fetch_rss() -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    req = Request(RSS_URL, headers=headers)
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def remove_polls(html: str) -> str:
    """
    Removes Beehiiv poll blocks regardless of format.
    Covers:
      - <beehiiv-poll ...></beehiiv-poll>
      - <div data-poll-id="...">...</div>
      - <script src="https://poll.beehiiv.com/..."></script>
      - <div class="bh-poll ...">...</div>
    """

    # Remove <beehiiv-poll>…</beehiiv-poll> blocks
    html = re.sub(
        r"<beehiiv-poll[\s\S]*?</beehiiv-poll>",
        "",
        html,
        flags=re.IGNORECASE
    )

    # Remove <div data-poll-id="…">…</div> blocks
    html = re.sub(
        r"<div[^>]*data-poll-id[^>]*>[\s\S]*?</div>",
        "",
        html,
        flags=re.IGNORECASE
    )

    # Remove older bh-poll wrapper blocks
    html = re.sub(
        r"<div[^>]*class=[\"']?bh-poll[^>]*>[\s\S]*?</div>",
        "",
        html,
        flags=re.IGNORECASE
    )

    # Remove Beehiiv poll script tags
    html = re.sub(
        r"<script[^>]*poll\.beehiiv\.com[^>]*>[\s\S]*?</script>",
        "",
        html,
        flags=re.IGNORECASE
    )
    html = re.sub(
        r"<script[^>]*poll\.beehiiv\.com[^>]*/>",
        "",
        html,
        flags=re.IGNORECASE
    )

    return html


def main():
    try:
        xml = fetch_rss()
    except (HTTPError, URLError) as e:
        print(f"Failed to fetch RSS: {e}")
        return

    # Find ONLY the first edition’s content (non-greedy)
    m = re.search(
        r"<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>",
        xml,
        re.DOTALL,
    )

    if m:
        body_html = m.group(1)
    else:
        m2 = re.search(
            r"<description><!\[CDATA\[(.*)\]\]></description>",
            xml,
            re.DOTALL,
        )
        body_html = m2.group(1) if m2 else "<p>No content found.</p>"

    # Remove polls before output
    body_html = remove_polls(body_html)

    full_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Latest Help My Newsletter Edition</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #000000;
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
  </style>
</head>
<body>
{body_html}
<script>
  // auto-resize iframe height via postMessage
  function reportHeight() {
    const height = document.body.scrollHeight;
    parent.postMessage({ type: "resize-latest-edition", height }, "*");
  }

  window.addEventListener("load", reportHeight);
  window.addEventListener("resize", reportHeight);
  new MutationObserver(reportHeight).observe(document.body, { childList: true, subtree: true });
</script>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_page)


if __name__ == "__main__":
    main()
