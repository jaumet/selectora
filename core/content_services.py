from django.utils.text import slugify

from .metadata_fetcher import fetch_url_metadata
from .models import Channel, ContentItem, Tag


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
        if hasattr(item, field) and value:
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


def create_content_item_from_url(user, url, manual_data=None, manual_tags=None):
    channel = get_or_create_channel(user)
    existing = ContentItem.objects.filter(channel=channel, url=url).first()
    if existing:
        return existing, False, ""

    metadata = fetch_url_metadata(url)
    item = ContentItem(user=user, channel=channel, url=url)
    apply_metadata_to_item(item, metadata, manual_data)
    item.save()

    tag_names = list(metadata.data.get("tags", []))
    if manual_tags:
        tag_names.extend(manual_tags)
    set_item_tags(item, tag_names)
    return item, True, metadata.error
