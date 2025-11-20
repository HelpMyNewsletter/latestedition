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
    """Remove all Beehiiv poll embed variants."""
    html = re.sub(r"<beehiiv-poll[\s\S]*?</beehiiv-poll>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<div[^>]*data-poll-id[^>]*>[\s\S]*?</div>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<div[^>]*class=[\"']?bh-poll[^>]*>[\s\S]*?</div>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<script[^>]*poll\.beehiiv\.com[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<script[^>]*poll\.beehiiv\.com[^>]*/>", "", html, flags=re.IGNORECASE)
    return html


def strip_beehiiv_footer(html: str) -> str:
    """Strip the built-in 'powered by beehiiv' footer included in RSS."""
    marker = "powered by beehiiv"
    lower_html = html.lower()
    idx = lower_html.find(marker)
    if idx != -1:
        return html[:idx]
    return html


def main():
    try:
        xml = fetch_rss()
    except (HTTPError, URLError) as e:
        print(f"Failed to fetch RSS: {e}")
        return

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

    body_html = remove_polls(body_html)
    body_html = strip_beehiiv_footer(body_html)

    full_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Latest Help My Newsletter Edition</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
  body {{
    margin: 0;
    padding: 0 0 50px 0;
    background: #000000;
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }}

  .hmn-shell {{
    max-width: 568px;
    margin: 0 auto;
    padding: 20px;
  }}

  .hmn-footer {{
    max-width: 568px;
    margin: 28px auto 0 auto;
    padding: 12px 20px;
    border-top: 1px solid #333333;

    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .hmn-footer a img {{
    display: block;
    max-height: 64px;   /* bigger size */
    width: auto;
  }}

  @media (max-width: 480px) {{
    .hmn-footer {{
      flex-direction: column;
      gap: 16px;
    }}
  }}
</style>
</head>

<body>

<div class="hmn-shell">
  {body_html}
</div>

<div class="hmn-footer">

  <!-- Left: Beehiiv Referral -->
  <a href="https://www.beehiiv.com?via=JenniferGibbs1"
     target="_blank" rel="noopener noreferrer">
    <img
      src="https://beehiiv-images-production.s3.amazonaws.com/uploads/asset/file/de8db07f-5edf-4790-be80-2c28563eede9/Add_a_subheading.png?t=1763656347"
      alt="Start your newsletter on beehiiv">
  </a>

  <!-- Right: Book a 15-minute Consult -->
  <a href="https://clarity.fm/jennifergibbs/helpmynewsletter"
     target="_blank" rel="noopener noreferrer">
    <img
      src="https://beehiiv-images-production.s3.amazonaws.com/uploads/asset/file/f5603471-e469-4bfe-94a6-dd08601cbbd5/Add_a_subheading__1_.png?t=1763656403"
      alt="Book a free 15-minute consult">
  </a>

</div>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_page)


if __name__ == "__main__":
    main()
