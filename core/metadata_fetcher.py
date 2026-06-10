from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from django.utils import timezone


REQUEST_TIMEOUT = 5
USER_AGENT = "SelectoraBot/0.1 (+https://github.com/jaumet/selectora)"


@dataclass
class MetadataResult:
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def fetch_url_metadata(url: str, http_get=None) -> MetadataResult:
    http_get = http_get or requests.get
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    try:
        response = http_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        data = _fallback_metadata(url)
        if _is_tiktok_url(url):
            data = _merge_metadata(data, _fetch_tiktok_oembed_metadata(url, http_get))
        data = _merge_metadata(data, _platform_image_metadata(url))
        return MetadataResult(data=data, error=str(exc))

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "xml" not in content_type and content_type:
        data = _fallback_metadata(response.url)
        if _is_tiktok_url(response.url):
            data = _merge_metadata(data, _fetch_tiktok_oembed_metadata(response.url, http_get))
        data = _merge_metadata(data, _platform_image_metadata(response.url))
        return MetadataResult(data=data, error="URL did not return HTML.")

    data = extract_metadata(response.text, response.url)
    if _is_tiktok_url(response.url):
        data = _merge_metadata(data, _fetch_tiktok_oembed_metadata(response.url, http_get))
    data = _merge_metadata(data, _platform_completion_metadata(url))
    data = _merge_metadata(data, _platform_image_metadata(response.url))
    return MetadataResult(data=data, error="")


def _merge_metadata(base, extra):
    merged = {**base}
    for key, value in extra.items():
        if key == "metadata_json":
            merged[key] = {**merged.get(key, {}), **value}
        elif key in {"title", "author", "thumbnail_url", "image_url"} and value:
            merged[key] = value
        elif value and (not merged.get(key) or merged.get(key) == "TikTok - Make Your Day"):
            merged[key] = value
    return merged


def _fetch_tiktok_oembed_metadata(url: str, http_get) -> dict[str, Any]:
    try:
        response = http_get(
            "https://www.tiktok.com/oembed",
            params={"url": url},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {}

    thumbnail_width = payload.get("thumbnail_width") or payload.get("width")
    thumbnail_height = payload.get("thumbnail_height") or payload.get("height")
    return {
        "title": payload.get("title", ""),
        "author": payload.get("author_name", ""),
        "site_name": payload.get("provider_name", "TikTok"),
        "source_platform": payload.get("provider_name", "TikTok"),
        "thumbnail_url": payload.get("thumbnail_url", ""),
        "image_url": payload.get("thumbnail_url", ""),
        "metadata_json": {
            "oembed": payload,
            "video_width": thumbnail_width,
            "video_height": thumbnail_height,
        },
    }


def extract_metadata(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    base_url = _base_url(soup, url)
    json_ld = _json_ld_blocks(soup)
    visible_title = _visible_title(soup)
    latest_episode = _latest_episode_from_links(soup)
    host_site_name = _site_name_from_url(url)
    canonical_url = _first(_canonical(soup, base_url), _meta(soup, "og:url"), url)
    image_url = _absolute(_first(*_image_candidates(soup, json_ld, html)), base_url)
    platform_image_url = _first(_social_json_image(html, canonical_url), _youtube_thumbnail(canonical_url))

    raw = {
        "title": _first(
            _meta(soup, "og:title"),
            _meta(soup, "twitter:title"),
            _json_ld_value(json_ld, "headline"),
            _json_ld_value(json_ld, "name"),
            visible_title,
            soup.title.string.strip() if soup.title and soup.title.string else "",
        ),
        "description": _first(
            _meta(soup, "og:description"),
            _meta(soup, "twitter:description"),
            _meta_name(soup, "description"),
            _json_ld_value(json_ld, "description"),
            latest_episode.get("description", ""),
            _first_meaningful_paragraph(soup),
        ),
        "image_url": _first(platform_image_url, image_url),
        "thumbnail_url": _first(platform_image_url, image_url),
        "favicon_url": _favicon(soup, base_url),
        "site_name": _first(_meta(soup, "og:site_name"), _json_ld_value(json_ld, "publisher.name"), host_site_name),
        "source_platform": _source_platform(soup, url),
        "content_type": _content_type(soup, json_ld, canonical_url),
        "author": _first(
            _meta_name(soup, "author"),
            _meta(soup, "article:author"),
            _json_ld_value(json_ld, "author.name"),
            _json_ld_value(json_ld, "creator.name"),
        ),
        "published_date": _parse_date(
            _first(
                _meta(soup, "article:published_time"),
                _meta_name(soup, "date"),
                _json_ld_value(json_ld, "datePublished"),
                _json_ld_value(json_ld, "uploadDate"),
            )
        ),
        "duration": _first(_meta(soup, "video:duration"), _json_ld_value(json_ld, "duration")),
        "language": _first(
            soup.html.get("lang", "") if soup.html else "",
            _meta_name(soup, "language"),
            _json_ld_value(json_ld, "inLanguage"),
        ),
        "canonical_url": canonical_url,
        "embed_url": _absolute(_first(_meta(soup, "og:video:url"), _meta(soup, "twitter:player")), base_url),
        "tags": _tags(soup, json_ld),
        "metadata_json": {
            "open_graph": _all_meta_by_prefix(soup, "og:"),
            "twitter": _all_meta_by_prefix(soup, "twitter:"),
            "json_ld": json_ld,
            "latest_episode": latest_episode,
            "video_width": _first(_meta(soup, "og:video:width"), _meta(soup, "twitter:player:width")),
            "video_height": _first(_meta(soup, "og:video:height"), _meta(soup, "twitter:player:height")),
        },
    }

    if not raw["embed_url"]:
        raw["embed_url"] = (
            _youtube_embed(raw["canonical_url"] or url)
            or _instagram_embed(raw["canonical_url"] or url)
            or _tiktok_embed(raw["canonical_url"] or url)
        )

    return {key: value for key, value in raw.items() if value not in ("", None, [], {})}


def _fallback_metadata(url: str) -> dict[str, Any]:
    return {
        "title": urlparse(url).netloc or url,
        "canonical_url": url,
        "source_platform": _site_name_from_url(url) or _platform_from_url(url),
        "content_type": _content_type(None, [], url),
        **_platform_image_metadata(url),
        "embed_url": _youtube_embed(url) or _instagram_embed(url) or _tiktok_embed(url),
        "metadata_json": {},
    }


def _platform_completion_metadata(url: str) -> dict[str, Any]:
    metadata = _fallback_metadata(url)
    return {
        key: value
        for key, value in metadata.items()
        if key in {"canonical_url", "source_platform", "content_type", "image_url", "thumbnail_url", "embed_url"}
    }


def _base_url(soup, url):
    base = soup.find("base", href=True)
    return urljoin(url, base["href"]) if base else url


def _meta(soup, property_name):
    tag = soup.find("meta", attrs={"property": property_name}) or soup.find("meta", attrs={"name": property_name})
    return tag.get("content", "").strip() if tag and tag.get("content") else ""


def _meta_name(soup, name):
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content", "").strip() if tag and tag.get("content") else ""


def _all_meta_by_prefix(soup, prefix):
    values = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        if key and key.startswith(prefix) and tag.get("content"):
            values[key] = tag["content"]
    return values


def _first(*values):
    for value in values:
        if value:
            return value
    return ""


def _absolute(value, base_url):
    return urljoin(base_url, value) if value else ""


def _canonical(soup, base_url):
    tag = soup.find("link", rel=lambda rel: rel and "canonical" in rel)
    return _absolute(tag.get("href"), base_url) if tag and tag.get("href") else ""


def _favicon(soup, base_url):
    for rel in ("icon", "shortcut icon", "apple-touch-icon"):
        tag = soup.find("link", rel=lambda value: value and rel in " ".join(value).lower())
        if tag and tag.get("href"):
            return _absolute(tag["href"], base_url)
    return urljoin(base_url, "/favicon.ico")


def _json_ld_blocks(soup):
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            value = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            blocks.extend(value)
        elif isinstance(value, dict) and isinstance(value.get("@graph"), list):
            blocks.extend(value["@graph"])
            blocks.append(value)
        elif isinstance(value, dict):
            blocks.append(value)
    return blocks


def _json_ld_value(blocks, dotted_key):
    keys = dotted_key.split(".")
    for block in blocks:
        value = block
        for key in keys:
            if isinstance(value, list):
                value = value[0] if value else {}
            if not isinstance(value, dict):
                value = {}
                break
            value = value.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _json_ld_image(blocks):
    for block in blocks:
        image = block.get("image") if isinstance(block, dict) else None
        if isinstance(image, str):
            return image
        if isinstance(image, list) and image:
            return image[0] if isinstance(image[0], str) else image[0].get("url", "")
        if isinstance(image, dict):
            return image.get("url", "")
    return ""


def _parse_date(value):
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    except (ValueError, TypeError, OverflowError):
        return None


def _content_type(soup, json_ld, url):
    og_type = _meta(soup, "og:type").lower() if soup else ""
    schema_type = _json_ld_value(json_ld, "@type").lower()
    combined = f"{og_type} {schema_type} {url}".lower()
    if "video" in combined or "youtube.com" in combined or "youtu.be" in combined:
        return "video"
    if "instagram.com" in combined and "/reel/" in combined:
        return "video"
    if "instagram.com" in combined:
        return "social"
    if "tiktok.com" in combined and "/video/" in combined:
        return "video"
    if "tiktok.com" in combined:
        return "social"
    if "podcast" in combined or "audio" in combined:
        return "podcast"
    if "music" in combined or "song" in combined:
        return "music"
    if "article" in combined or "news" in combined or "blog" in combined:
        return "article"
    return "other"


def _visible_title(soup):
    for selector in ("main h1", "article h1", "h1", "main h2", "article h2"):
        tag = soup.select_one(selector)
        if tag:
            text = _clean_text(tag.get_text(" ", strip=True))
            if _meaningful_text(text):
                return text
    return ""


def _first_meaningful_paragraph(soup):
    for tag in soup.select("main p, article p, p"):
        text = _clean_text(tag.get_text(" ", strip=True))
        if _meaningful_text(text) and len(text) > 60:
            return text
    return ""


def _first_image(soup):
    for image in soup.find_all("img"):
        src = _image_source(image)
        if not src:
            continue
        if not _usable_image_candidate(src, image.get("alt", "")):
            continue
        return src
    return ""


def _image_candidates(soup, json_ld, html):
    return [
        _meta(soup, "og:image:secure_url"),
        _meta(soup, "og:image:url"),
        _meta(soup, "og:image"),
        _meta(soup, "twitter:image:src"),
        _meta(soup, "twitter:image"),
        _meta_name(soup, "thumbnail"),
        _meta_name(soup, "image"),
        _link_image(soup),
        _itemprop_image(soup),
        _json_ld_image(json_ld),
        _social_json_image(html, ""),
        _first_image(soup),
    ]


def _link_image(soup):
    for rel in ("image_src", "preload"):
        tag = soup.find("link", rel=lambda value: value and rel in " ".join(value).lower())
        if not tag or not tag.get("href"):
            continue
        if rel == "preload" and tag.get("as") != "image":
            continue
        href = tag["href"].strip()
        if _usable_image_candidate(href):
            return href
    return ""


def _itemprop_image(soup):
    tag = soup.find(attrs={"itemprop": "image"})
    if not tag:
        return ""
    value = tag.get("content") or tag.get("src") or tag.get("href")
    return value.strip() if value and _usable_image_candidate(value) else ""


def _image_source(image):
    for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-url"):
        value = image.get(attr)
        if value:
            return value.strip()
    srcset = image.get("srcset") or image.get("data-srcset")
    return _best_srcset_image(srcset)


def _best_srcset_image(srcset):
    best_url = ""
    best_score = -1
    for candidate in (srcset or "").split(","):
        parts = candidate.strip().split()
        if not parts:
            continue
        url = parts[0]
        score = 0
        if len(parts) > 1:
            descriptor = parts[1]
            try:
                if descriptor.endswith("w"):
                    score = int(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = int(float(descriptor[:-1]) * 1000)
            except ValueError:
                score = 0
        if score >= best_score and _usable_image_candidate(url):
            best_url = url
            best_score = score
    return best_url


def _usable_image_candidate(src, alt=""):
    value = (src or "").strip()
    if not value:
        return False
    lowered = f"{value} {alt or ''}".lower()
    if value.startswith("data:"):
        return False
    if any(skip in lowered for skip in ("tracking", "pixel", "spacer", "blank.gif")):
        return False
    if any(skip in lowered for skip in ("avatar", "profile_pic")):
        return False
    if any(skip in lowered for skip in ("logo", "icon", "favicon", "sprite")):
        image_like = lowered.split("?", 1)[0].endswith((".jpg", ".jpeg", ".png", ".webp", ".avif"))
        return image_like and not any(size in lowered for size in ("16x16", "32x32", "64x64"))
    return True


def _social_json_image(html, url):
    patterns = [
        r'"display_url"\s*:\s*"([^"]+)"',
        r'"thumbnail_src"\s*:\s*"([^"]+)"',
        r'"thumbnail_url"\s*:\s*"([^"]+)"',
        r'"thumbnailUrl"\s*:\s*\[\s*"([^"]+)"',
        r'"thumbnailUrl"\s*:\s*"([^"]+)"',
        r'"cover"\s*:\s*"([^"]+)"',
        r'"originCover"\s*:\s*"([^"]+)"',
        r'"dynamicCover"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "")
        if not match:
            continue
        value = _decode_json_url(match.group(1))
        if _usable_image_candidate(value):
            return value
    return _youtube_thumbnail(url)


def _decode_json_url(value):
    return (value or "").replace("\\u0026", "&").replace("\\/", "/")


def _platform_image_metadata(url):
    image_url = _youtube_thumbnail(url)
    return {"image_url": image_url, "thumbnail_url": image_url} if image_url else {}


def _youtube_thumbnail(url):
    video_id = _youtube_video_id(url)
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""


def _youtube_video_id(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/").split("/", 1)[0]
    if "youtube.com" in host or "youtube-nocookie.com" in host:
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] in {"shorts", "live", "embed", "v"}:
            return parts[1] if len(parts) > 1 else ""
        return parse_qs(parsed.query).get("v", [""])[0]
    return ""


def _latest_episode_from_links(soup):
    date_pattern = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
    for link in soup.find_all("a", href=True):
        text = _clean_text(link.get_text(" ", strip=True))
        if not date_pattern.search(text):
            continue
        if len(text) < 40:
            continue
        parts = date_pattern.split(text, maxsplit=1)
        date = date_pattern.search(text).group(0)
        body = parts[1].strip(" -:") if len(parts) > 1 else text
        sentences = re.split(r"(?<=[.!?])\s+", body)
        title = sentences[0].strip() if sentences else body
        description = body
        return {
            "date": date,
            "title": title[:255],
            "description": description[:500],
            "url": link.get("href", ""),
        }
    return {}


def _clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def _meaningful_text(value):
    lowered = value.lower()
    ignored = {"menu", "cerca", "subscriptor", "inicia sessió", "podcasts", "pòdcasts"}
    return value and lowered not in ignored


def _tags(soup, json_ld):
    values = []
    keywords = _meta_name(soup, "keywords")
    if keywords:
        values.extend([tag.strip() for tag in keywords.split(",")])
    for block in json_ld:
        if not isinstance(block, dict):
            continue
        for key in ("keywords", "about"):
            value = block.get(key)
            if isinstance(value, str):
                values.extend([tag.strip() for tag in re.split(r",|;", value)])
            elif isinstance(value, list):
                values.extend(item.get("name", item) if isinstance(item, dict) else item for item in value)
    return sorted({tag for tag in values if isinstance(tag, str) and 1 < len(tag) <= 80})[:12]


def _platform_from_url(url):
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host.split(":")[0]


def _site_name_from_url(url):
    host = _platform_from_url(url)
    known_sites = {
        "vilaweb.cat": "VilaWeb",
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "instagram.com": "Instagram",
        "tiktok.com": "TikTok",
    }
    return known_sites.get(host, host)


def _is_tiktok_url(url):
    return "tiktok.com" in urlparse(url).netloc.lower()


def _source_platform(soup, url):
    host_site_name = _site_name_from_url(url)
    if host_site_name in {"Instagram", "TikTok", "YouTube", "VilaWeb"}:
        return host_site_name
    return _first(_meta(soup, "og:site_name"), host_site_name, _platform_from_url(url))


def _youtube_embed(url):
    video_id = _youtube_video_id(url)
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"
    return ""


def _instagram_embed(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "instagram.com" not in host:
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    for kind in ("reel", "p", "tv"):
        if kind in parts:
            index = parts.index(kind)
            if len(parts) > index + 1:
                shortcode = parts[index + 1]
                return f"https://www.instagram.com/{kind}/{shortcode}/embed"
    return ""


def _tiktok_embed(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "tiktok.com" not in host:
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if "video" not in parts:
        return ""
    index = parts.index("video")
    if len(parts) <= index + 1:
        return ""
    video_id = parts[index + 1]
    if not video_id.isdigit():
        return ""
    return f"https://www.tiktok.com/player/v1/{video_id}?controls=1&progress_bar=1&play_button=1&volume_control=1&fullscreen_button=1"
