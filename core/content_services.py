from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from django.db.models import Q
from django.utils.text import slugify

from .metadata_fetcher import fetch_url_metadata
from .models import Channel, ContentItem, Tag


TRACKING_QUERY_PARAMS = {
    "app",
    "dclid",
    "fbclid",
    "feature",
    "gclid",
    "igsh",
    "igshid",
    "mc_cid",
    "mc_eid",
    "share_id",
    "si",
}


def get_or_create_channel(user):
    return Channel.objects.get_or_create(
        owner=user,
        defaults={
            "name": f"Canal de {user.username}",
            "description": "Seleccio personal de continguts digitals.",
        },
    )[0]


def apply_metadata_to_item(item, metadata, manual_data=None):
    manual_data = manual_data or {}
    for field, value in metadata.data.items():
        if field in {"tags", "metadata_json"}:
            continue
        if field in manual_data and manual_data.get(field):
            continue
        if hasattr(item, field) and value:
            setattr(item, field, value)

    for field, value in manual_data.items():
        if hasattr(item, field) and value is not None and value != "":
            setattr(item, field, value)

    if metadata.data.get("metadata_json"):
        item.metadata_json = metadata.data["metadata_json"]
    if not item.title:
        item.title = item.url


def set_item_tags(item, names):
    tags = []
    for name in names:
        clean_name = name.strip()
        if not clean_name:
            continue
        slug = slugify(clean_name)[:90]
        if not slug:
            continue
        tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": clean_name})
        tags.append(tag)
    item.tags.set(tags)


def duplicate_url_key(url):
    value = (url or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value

    youtube_id = youtube_video_id(parsed)
    if youtube_id:
        return f"https://www.youtube.com/watch?v={youtube_id}"

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_params = []
    for key, param_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_PARAMS:
            continue
        query_params.append((key, param_value))

    return urlunparse((scheme, netloc, path, "", urlencode(query_params, doseq=True), ""))


def youtube_video_id(parsed):
    host = parsed.netloc.lower()
    parts = [part for part in parsed.path.split("/") if part]
    if "youtu.be" in host:
        return parts[0] if parts else ""
    if "youtube.com" in host or "youtube-nocookie.com" in host:
        if parts and parts[0] in {"shorts", "live", "embed", "v"}:
            return parts[1] if len(parts) > 1 else ""
        return parse_qs(parsed.query).get("v", [""])[0]
    return ""


def duplicate_url_keys(*urls):
    keys = set()
    for url in urls:
        value = (url or "").strip()
        if not value:
            continue
        keys.add(value)
        keys.add(duplicate_url_key(value))
    return {key for key in keys if key}


def find_public_duplicate(url, canonical_url=""):
    keys = duplicate_url_keys(url, canonical_url)
    if not keys:
        return None

    queryset = (
        ContentItem.objects
        .filter(channel__is_public=True, visibility=ContentItem.Visibility.PUBLIC)
        .select_related("channel", "user")
    )

    direct_match = queryset.filter(Q(url__in=keys) | Q(canonical_url__in=keys)).first()
    if direct_match:
        return direct_match

    for item in queryset:
        if duplicate_url_keys(item.url, item.canonical_url) & keys:
            return item
    return None


def create_content_item_from_url(user, url, manual_data=None, manual_tags=None):
    channel = get_or_create_channel(user)
    existing = ContentItem.objects.filter(channel=channel, url=url).first()
    if existing:
        if not existing.embed_url:
            metadata = fetch_url_metadata(url)
            apply_metadata_to_item(existing, metadata, manual_data)
            existing.save()
            if not existing.tags.exists():
                tag_names = list(metadata.data.get("tags", []))
                if manual_tags:
                    tag_names.extend(manual_tags)
                set_item_tags(existing, tag_names)
            return existing, False, metadata.error
        return existing, False, ""

    public_duplicate = find_public_duplicate(url)
    if public_duplicate:
        error = "public_duplicate" if public_duplicate.channel_id != channel.id else ""
        return public_duplicate, False, error

    metadata = fetch_url_metadata(url)
    public_duplicate = find_public_duplicate(url, metadata.data.get("canonical_url", ""))
    if public_duplicate:
        error = "public_duplicate" if public_duplicate.channel_id != channel.id else ""
        return public_duplicate, False, error

    item = ContentItem(user=user, channel=channel, url=url)
    apply_metadata_to_item(item, metadata, manual_data)
    item.save()

    tag_names = list(metadata.data.get("tags", []))
    if manual_tags:
        tag_names.extend(manual_tags)
    set_item_tags(item, tag_names)
    return item, True, metadata.error
