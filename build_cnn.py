"""
Build cnn.html from cnn-raw.html:
- Parse CNN article page
- Strip all external scripts / tracking / analytics / ads
- Strip preconnect/dns-prefetch to CNN + third parties
- Download all referenced CNN images locally to cnn-assets/images
- Rewrite image URLs to local paths
- Replace article body with the XRP newsletter block (taken from whitehouse.html)
- Inject <script src="affiliate-tracker.js"></script> before </body>
"""
import os
import re
import sys
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Comment

ROOT = Path(__file__).parent
RAW = ROOT / "cnn-raw.html"
OUT = ROOT / "cnn.html"
ASSETS_DIR = ROOT / "cnn-assets"
IMG_DIR = ASSETS_DIR / "images"
WHITEHOUSE = ROOT / "whitehouse.html"

IMG_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

# -----------------------------------------------------------------------------
# 1. XRP article body written as native CNN paragraphs. We use CNN's own
#    paragraph-elevate class so the text renders in CNN typography and looks
#    indistinguishable from a real CNN article.
# -----------------------------------------------------------------------------

CTA_URL = "https://qfsmagastore.com/pages/xrp-gold-coins"

NEW_TITLE = "The Louisville Miracle: How Sixty Tokens Rewrote One Father's Destiny | CNN"
NEW_HEADLINE = "The Louisville Miracle: How Sixty Tokens Rewrote One Father&rsquo;s Destiny"
HERO_IMG = "photo_1_2026-04-17_16-53-39.jpg"
HERO_CAPTION = ("Joseph Miller, a Louisville construction laborer, sits in his truck after "
                "another long shift &mdash; moments before he made the decision that would "
                "change everything.")

def P(text: str) -> str:
    return (
        '<p class="paragraph-elevate inline-placeholder vossi-paragraph_elevate" '
        'data-component-name="paragraph" data-article-gutter="true">'
        f'{text}</p>'
    )

def H2(text: str) -> str:
    return (
        '<h2 class="paragraph-elevate inline-placeholder vossi-paragraph_elevate" '
        'data-component-name="subheader" data-article-gutter="true" '
        'style="font-family:inherit;font-size:26px;font-weight:700;line-height:1.3;'
        'margin:36px auto 12px;max-width:640px;padding:0 20px;color:#0c0c0c;">'
        f'{text}</h2>'
    )

def PULL(text: str) -> str:
    return (
        '<blockquote class="paragraph-elevate inline-placeholder vossi-paragraph_elevate" '
        'data-component-name="quote" data-article-gutter="true" '
        'style="font-family:inherit;font-size:24px;line-height:1.4;font-weight:500;'
        'border-left:4px solid #c00;margin:28px auto;max-width:640px;padding:4px 0 4px 24px;'
        'color:#262626;">'
        f'&ldquo;{text}&rdquo;</blockquote>'
    )

def IMG(src: str, alt: str, caption: str) -> str:
    return (
        '<figure class="inline-placeholder" data-article-gutter="true" '
        'style="margin:28px auto;max-width:660px;padding:0 20px;">'
        f'<img src="{src}" alt="{alt}" loading="lazy" '
        'style="width:100%;height:auto;display:block;border-radius:2px;" />'
        '<figcaption style="font-family:inherit;font-size:13px;line-height:1.4;'
        'color:#6e6e6e;padding:8px 0 0;">'
        f'{caption}</figcaption></figure>'
    )

def CTA(label: str, sub: str = "") -> str:
    sub_html = (
        f'<div style="font-size:13px;color:#6e6e6e;margin-top:10px;'
        f'font-family:inherit;">{sub}</div>' if sub else ""
    )
    return (
        '<div class="inline-placeholder" data-article-gutter="true" '
        'style="max-width:640px;margin:32px auto;padding:28px 24px;text-align:center;'
        'background:#f8f8f8;border-left:4px solid #c00;border-radius:2px;">'
        f'<a href="{CTA_URL}" target="_blank" rel="noreferrer noopener" class="aff-link" '
        'style="display:inline-block;background:#c00;color:#fff;'
        'padding:14px 36px;font-family:inherit;font-size:15px;font-weight:700;'
        'letter-spacing:0.04em;text-transform:uppercase;text-decoration:none;'
        f'border-radius:2px;">{label} &rarr;</a>{sub_html}</div>'
    )

article_body_html = "\n".join([
    P("<strong>LOUISVILLE, KY</strong> &mdash; For fifteen years, Joseph Miller&rsquo;s "
      "life was built on routine: early mornings, long hours, and the steady weight of "
      "responsibility."),
    P("As a construction laborer in Louisville, he worked to support his wife, Sarah, "
      "and their two young children &mdash; not chasing wealth, but trying to keep up "
      "with bills that never seemed to slow down."),
    PULL("I had about $400 in savings and a car that was about to give out. I remember "
         "sitting in my truck thinking&hellip; I&rsquo;m running out of options."),
    P("At home, the pressure was constant. Envelopes marked &ldquo;PAST DUE&rdquo; sat "
      "on the kitchen table, quiet but impossible to ignore."),

    H2("A Risk Built on Belief"),
    P("Miller says everything began to shift when he came across reports about "
      "<strong>physical XRP tokens</strong> &mdash; a concept he didn&rsquo;t fully "
      "understand, but one that caught his attention."),
    P("What made him take it seriously was the broader message surrounding it. Public "
      "statements, including those from Donald Trump, framed digital assets like XRP "
      "as part of a future financial system designed to protect everyday Americans."),
    PULL("I&rsquo;ve always supported Trump. When I saw him talking about it, it made "
         "me stop and listen."),
    P("With little savings and even less certainty, Miller made a decision that felt "
      "like a risk &mdash; but also like his only chance forward."),
    P("He purchased <strong>60 XRP tokens</strong>."),
    P("&ldquo;It wasn&rsquo;t about being sure,&rdquo; he says. &ldquo;It was about "
      "believing something had to change.&rdquo;"),

    CTA("Secure Your XRP Tokens",
        "Same official program Miller used &mdash; limited allocations remaining"),

    H2("The Call"),
    IMG("photo_2_2026-04-17_16-53-39.jpg",
        "Miller stares at his phone in disbelief, a pile of XRP tokens on the kitchen table beside PAST DUE notices.",
        "Miller at his kitchen table the afternoon the call came in. The tokens he "
        "had almost forgotten about had quietly become the most valuable thing in his home."),
    P("For months, nothing happened. Miller continued working, the tokens sitting "
      "quietly, almost forgotten."),
    P("Then one afternoon, his phone rang."),
    P("&ldquo;I thought it was a scam,&rdquo; he says. &ldquo;I almost hung up.&rdquo;"),
    P("Instead, he listened."),
    P("The message was direct: the market had shifted. His tokens &mdash; the same "
      "ones he had taken a chance on &mdash; were now valued at <strong>approximately "
      "$230,000 each</strong>."),
    PULL("I didn&rsquo;t even process it at first. They told me it was about "
         "$14 million&hellip; and I just sat there."),
    IMG("photo_3_2026-04-17_16-53-39.jpg",
        "Miller laughs on his phone on a construction site, still in his work vest and helmet.",
        "Miller moments after the call, still on the job site. &ldquo;I didn&rsquo;t "
        "know whether to laugh or cry,&rdquo; he said. &ldquo;So I did both.&rdquo;"),
    P("Under official guidance, Miller completed the process through a private "
      "cashout facility. The transition was fast, structured, and unlike anything he "
      "had experienced before."),
    IMG("photo_4_2026-04-17_16-53-39.jpg",
        "Miller shakes hands with an Office of Financial Services representative as a $14,000,000 transaction confirmation appears on screen.",
        "The confirmation screen read $14,000,000 &mdash; status: completed. "
        "&ldquo;I kept asking them to double-check,&rdquo; Miller said."),
    P("Within days, everything had changed."),

    H2("The Moment It Became Real"),
    P("But for Miller, the reality of it didn&rsquo;t hit in the office."),
    P("It hit at home."),
    IMG("photo_5_2026-04-17_16-53-39.jpg",
        "Miller embraces his wife Sarah and their two children at their old kitchen table.",
        "&ldquo;For the first time, I didn&rsquo;t feel pressure walking into my own "
        "home,&rdquo; Miller said."),
    P("&ldquo;I remember walking through the door,&rdquo; he says. &ldquo;I "
      "didn&rsquo;t even know how to say it.&rdquo;"),
    P("Sarah noticed immediately."),
    P("&ldquo;He just stood there,&rdquo; she recalls. &ldquo;Like he was trying to "
      "find the words.&rdquo;"),
    P("When he finally told her, there was a moment of silence &mdash; the kind where "
      "everything hangs in the air."),
    P("Then came the reaction."),
    P("&ldquo;We just&hellip; hugged,&rdquo; Miller says. &ldquo;All of us. The kids "
      "didn&rsquo;t fully understand, but they knew something was different.&rdquo;"),
    P("There were tears. Laughter. Relief that didn&rsquo;t need to be explained."),

    H2("A New Beginning"),
    IMG("photo_6_2026-04-17_16-53-39.jpg",
        "The Miller family celebrates in their new home, holding the keys and standing next to a moving box labeled NEW HOME.",
        "The Miller family on move-in day. Each child, for the first time, got their "
        "own room."),
    P("The first major change wasn&rsquo;t a business decision &mdash; it was a home."),
    P("The Miller family moved into a new house, filled with natural light and space "
      "they had never had before. Each child had their own room. The kitchen table "
      "was no longer a place of stress, but of normal life."),
    PULL("My wife doesn&rsquo;t check the bank account before buying groceries "
         "anymore. That peace&hellip; that&rsquo;s what matters."),

    CTA("Start Your Own Story Today",
        "Allocations are limited &mdash; the window closes soon"),

    H2("Building Something Bigger"),
    IMG("photo_7_2026-04-17_16-53-39.jpg",
        "Miller, now in a suit, holds a Miller Construction hardhat in front of his new construction company's excavators and a rising skyscraper.",
        "Miller at the site of his first major project. The hardhat still carries his "
        "name &mdash; the company now does, too."),
    P("Only after that did Miller turn back to what he knew best."),
    P("Construction."),
    P("But this time, from a different position."),
    P("He founded <strong>Miller Construction</strong>, shifting from laborer to "
      "owner &mdash; not leaving his past behind, but building on it."),
    PULL("I know what it&rsquo;s like to be out there. I don&rsquo;t forget that."),

    H2("From Pressure to Peace"),
    IMG("photo_8_2026-04-17_16-53-39.jpg",
        "A split image showing Miller's transformation: on the left, exhausted and surrounded by PAST DUE envelopes; on the right, confident in a suit holding a Miller Construction hardhat at a rising skyscraper.",
        "Before and after. Miller said the hardest part of the change wasn&rsquo;t "
        "what he gained &mdash; it was remembering what had been missing."),
    P("For Miller, the transformation isn&rsquo;t defined by the number."),
    P("It&rsquo;s defined by what&rsquo;s no longer there."),
    P("The stress. The constant worry. The feeling of falling behind."),
    PULL("I used to feel like everything was closing in. Now&hellip; it feels like I "
         "finally have room to breathe."),
    P("From a construction site in Louisville to a life of stability, Miller&rsquo;s "
      "journey reflects more than a financial shift. It&rsquo;s the story of a father "
      "who took a risk &mdash; and, for the first time, saw it lead somewhere better."),

    CTA("Claim Your XRP Allocation",
        "The same path Miller took &mdash; official and verified"),
])

print(f"[story] article body: {len(article_body_html)} bytes")

# -----------------------------------------------------------------------------
# 2. Parse CNN HTML
# -----------------------------------------------------------------------------
print("[cnn] parsing raw HTML...")
raw = RAW.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(raw, "lxml")

# -----------------------------------------------------------------------------
# 3. Strip ALL scripts. Static clone doesn't need CNN's JS, and every external
#    script would leak user data to third parties (CNN, Google, Amazon, etc.).
# -----------------------------------------------------------------------------
script_count = 0
for s in soup.find_all("script"):
    s.decompose()
    script_count += 1
print(f"[strip] removed {script_count} <script> tags")

# Remove noscript as well (often contains tracking pixels).
ns_count = 0
for ns in soup.find_all("noscript"):
    ns.decompose()
    ns_count += 1
print(f"[strip] removed {ns_count} <noscript> tags")

# Remove iframes (ads).
for ifr in soup.find_all("iframe"):
    ifr.decompose()

# Remove preconnect / dns-prefetch / preload links that ping third parties.
leak_rels = {"preconnect", "dns-prefetch", "preload", "prefetch", "canonical", "alternate", "amphtml"}
link_removed = 0
for link in soup.find_all("link"):
    rel = link.get("rel", [])
    if isinstance(rel, list):
        rel_set = set(r.lower() for r in rel)
    else:
        rel_set = {rel.lower()}
    if rel_set & leak_rels:
        link.decompose()
        link_removed += 1
        continue
    # Also strip stylesheets that point to external origins (none here, but safe).
    href = link.get("href", "") or ""
    if href.startswith("http"):
        link.decompose()
        link_removed += 1
print(f"[strip] removed {link_removed} <link> tags")

# Remove meta tags that expose referrers or identify CNN as source.
meta_removed = 0
bad_meta_names = {
    "twitter:site", "twitter:creator", "twitter:url", "fb:app_id", "fb:pages",
    "al:ios:app_store_id", "al:ios:app_name", "al:ios:url",
    "al:android:package", "al:android:url", "al:android:app_name",
    "apple-itunes-app", "google-site-verification", "msvalidate.01",
    "referrer",
}
bad_meta_props = {
    "og:url", "og:site_name", "og:image", "og:image:url", "og:image:secure_url",
    "article:publisher", "article:author", "twitter:image",
}
for meta in list(soup.find_all("meta")):
    name = (meta.get("name") or "").lower()
    prop = (meta.get("property") or "").lower()
    if name in bad_meta_names or prop in bad_meta_props:
        meta.decompose()
        meta_removed += 1
print(f"[strip] removed {meta_removed} leaky <meta> tags")

# Force meta referrer no-referrer so clicks from this page don't show CNN.
head = soup.head
if head:
    ref = soup.new_tag("meta")
    ref["name"] = "referrer"
    ref["content"] = "no-referrer"
    head.insert(0, ref)

# Override CSS: CNN relies on JS to reveal certain chrome (top nav, right-side
# Watch/Listen/Sign in block, user account nav, and the hero image fade-in).
# Without JS, these stay hidden. We add a late-priority override so the static
# page renders with the full CNN chrome visible.
if head:
    override = soup.new_tag("style")
    override.string = (
        ".header__nav,.header-elevate .header__nav{visibility:visible!important;"
        "height:auto!important;overflow:visible!important}"
        ".header__right,.header-elevate .header__right{visibility:visible!important}"
        ".user-account-nav{visibility:visible!important}"
        ".image_large__img--fade-in,.image__img--fade-in,.image_expandable__img--fade-in"
        "{opacity:1!important;visibility:visible!important}"
        ".image_large__dam-img--loading,.image__dam-img--loading,"
        ".image_expandable__dam-img--loading{background-color:transparent!important}"
        ".ad-slot-header,.ad-slot-header__wrapper,.ad-slot{display:none!important}"
    )
    head.append(override)

# Remove HTML comments (may contain tracking beacons).
for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
    c.extract()

# -----------------------------------------------------------------------------
# 4. Download and localize images. Walk every element with src/srcset/href
#    pointing to media.cnn.com, cdn.cnn.com, static.cnn.com, lightning.cnn.com,
#    ix.cnn.io or similar CNN-controlled hosts. Replace with local path.
# -----------------------------------------------------------------------------
_url_to_local = {}

def slug_for(url: str) -> str:
    """Stable local filename for a given remote URL."""
    if url in _url_to_local:
        return _url_to_local[url]
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path) or "img"
    # keep query signature in hash so different crops don't collide.
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    # preserve extension if obvious
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ".img"
    # sanitize
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:60]
    fname = f"{safe_name}-{digest}{ext}"
    _url_to_local[url] = fname
    return fname

def is_cnn_img(url: str) -> bool:
    if not url:
        return False
    # absolute
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/"):
        return True  # relative to CNN's root; we'll still rewrite
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False
    return any(
        host.endswith(d) for d in (
            "cnn.com", "cnn.io", "turner.com", "ampproject.org", "turnip.cdn.turner.com"
        )
    )

def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://edition.cnn.com/"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"[img] FAIL {url}: {e}")
        return False

def normalize(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        # assume CNN root
        return "https://edition.cnn.com" + url
    return url

# collect all urls to download
to_download = set()

def handle_url(u: str) -> str | None:
    """Return local rewritten path, or None if not a downloadable asset."""
    if not u:
        return None
    u = u.strip()
    if u.startswith("data:"):
        return None
    full = normalize(u)
    if not full.startswith("http"):
        return None
    if not is_cnn_img(full):
        # external non-CNN asset (e.g. media from a third party) — drop it
        # so there's no leak.
        return ""  # signal: remove
    fname = slug_for(full)
    to_download.add((full, IMG_DIR / fname))
    return f"cnn-assets/images/{fname}"

# img[src], source[srcset], link[href rel=icon|apple-touch-icon|manifest|mask-icon]
img_rewrites = 0
for img in soup.find_all("img"):
    src = img.get("src")
    if src:
        new = handle_url(src)
        if new == "":
            img.decompose()
            continue
        if new:
            img["src"] = new
            img_rewrites += 1
    # also process srcset
    ss = img.get("srcset")
    if ss:
        rewrite_srcset = []
        for part in ss.split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            url = bits[0]
            new = handle_url(url)
            if new == "" or new is None:
                continue
            bits[0] = new
            rewrite_srcset.append(" ".join(bits))
        if rewrite_srcset:
            img["srcset"] = ", ".join(rewrite_srcset)
        else:
            del img["srcset"]

for source in soup.find_all("source"):
    ss = source.get("srcset")
    if not ss:
        continue
    parts = []
    for part in ss.split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split()
        url = bits[0]
        new = handle_url(url)
        if new == "" or new is None:
            continue
        bits[0] = new
        parts.append(" ".join(bits))
    if parts:
        source["srcset"] = ", ".join(parts)
    else:
        source.decompose()

# favicons and manifests
for link in soup.find_all("link"):
    href = link.get("href", "")
    if not href:
        continue
    new = handle_url(href)
    if new == "" or new is None:
        continue
    link["href"] = new

# inline style url(...)
url_re = re.compile(r"url\((['\"]?)([^)'\"]+)\1\)")
def rewrite_style_urls(css: str) -> str:
    def sub(m):
        u = m.group(2)
        if u.startswith("data:"):
            return m.group(0)
        new = handle_url(u)
        if new is None or new == "":
            return m.group(0)  # leave alone (likely a relative path like /media/...)
        return f"url({new})"
    return url_re.sub(sub, css)

for el in soup.find_all(style=True):
    el["style"] = rewrite_style_urls(el["style"])

# <style> tags — the inline CSS contains tons of /media/sites/cnn/... refs.
# Rewrite them too but they're relative — we need to download them.
for style in soup.find_all("style"):
    if style.string:
        new_css = rewrite_style_urls(style.string)
        style.string.replace_with(new_css)

print(f"[img] queued {len(to_download)} unique URLs for download")

# -----------------------------------------------------------------------------
# 5. Download all queued images.
# -----------------------------------------------------------------------------
ok = 0
for url, dest in to_download:
    if download(url, dest):
        ok += 1
print(f"[img] downloaded {ok}/{len(to_download)}")

# -----------------------------------------------------------------------------
# 6. Replace article body with the XRP newsletter block. Inject the nl-* style
#    into <head>.
# -----------------------------------------------------------------------------
# Update <title>
title_tag = soup.find("title")
if title_tag:
    title_tag.string = NEW_TITLE

# Update og/twitter title/description metas so if anyone scrapes it, it shows our headline
for m in soup.find_all("meta"):
    prop = (m.get("property") or "").lower()
    name = (m.get("name") or "").lower()
    if prop in ("og:title", "twitter:title") or name in ("twitter:title",):
        m["content"] = NEW_TITLE
    if prop == "og:description" or name in ("description", "twitter:description"):
        m["content"] = ("A Louisville construction laborer bought 60 XRP tokens with his last $400. "
                        "Months later, a single phone call changed everything.")

# Update H1 headline
h1 = soup.find("h1", class_="headline__text")
if h1:
    h1.clear()
    h1.append(BeautifulSoup(NEW_HEADLINE, "html.parser"))

# Replace byline with our own
byline_authors = soup.find("div", class_="byline__authors")
if byline_authors:
    byline_authors.clear()
    byline_authors.append(BeautifulSoup(
        'By <div class="byline__author vossi-byline_elevate__author">'
        '<a class="byline__link vossi-byline_elevate__link" href="#">'
        '<span class="byline__name vossi-byline_elevate__name">CNN Staff</span></a></div>',
        "html.parser"))

# Replace hero <picture>/<img> in the lede wrapper with our local photo_1
lede = soup.find(class_="article__lede-wrapper")
if lede:
    lede.clear()
    hero_html = (
        '<figure class="image_large-elevate" '
        'style="margin:0 auto 24px;max-width:1100px;">'
        f'<img src="{HERO_IMG}" alt="Joseph Miller in his truck in Louisville" '
        'style="width:100%;height:auto;display:block;" />'
        '<figcaption style="font-family:inherit;font-size:13px;line-height:1.4;'
        'color:#6e6e6e;padding:10px 20px 0;">'
        f'{HERO_CAPTION}</figcaption></figure>'
    )
    lede.append(BeautifulSoup(hero_html, "html.parser"))

article_content = soup.find("div", class_="article__content")
if not article_content:
    print("[ERR] article__content div not found", file=sys.stderr)
    sys.exit(2)

article_content.clear()
# Inject our XRP paragraphs inline using CNN's paragraph-elevate styling so the
# body renders in CNN typography — visually indistinguishable from a real CNN
# article.
body_frag = BeautifulSoup(article_body_html, "html.parser")
for child in list(body_frag.children):
    article_content.append(child.extract())

# -----------------------------------------------------------------------------
# 7. Also remove CNN's "related", "paid-partner", "video-resource",
#    "video-playlist", "zone-outbrain", "zone-related" blocks that could still
#    beacon or look wrong with our content. (They don't have JS anymore but
#    may contain links we don't want.)
# -----------------------------------------------------------------------------
remove_selectors = [
    "[data-component-name='outbrain']",
    "[data-component-name='paid-partner-content']",
    "[data-component-name='related-content']",
    ".outbrain",
    ".ad-slot",
    ".ad-slot-header",
    ".ad-slot-header__wrapper",
    "[data-ad-slot]",
    "[class*='ad-feedback']",
    "[id*='google_ads']",
]
removed = 0
for sel in remove_selectors:
    for el in soup.select(sel):
        el.decompose()
        removed += 1
print(f"[strip] removed {removed} ad/related blocks")

# -----------------------------------------------------------------------------
# 8. Append our affiliate-tracker.js before </body>.
# -----------------------------------------------------------------------------
body = soup.body
if body:
    aff = soup.new_tag("script", src="affiliate-tracker.js")
    body.append(aff)

# -----------------------------------------------------------------------------
# 9. Write output.
# -----------------------------------------------------------------------------
html_out = str(soup)
OUT.write_text(html_out, encoding="utf-8")
size_mb = OUT.stat().st_size / 1024 / 1024
print(f"[out] wrote {OUT} ({size_mb:.2f} MB)")
