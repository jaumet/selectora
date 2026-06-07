from pathlib import Path
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.metadata_fetcher import fetch_url_metadata
from core.models import ContentItem


IMAGE_TIMEOUT = 12
IMAGE_USER_AGENT = "Mozilla/5.0 (compatible; SelectoraBot/0.1)"


class Command(BaseCommand):
    help = "Refresh metadata for content items, focused on missing images by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Refresh every item instead of only items without image fields.",
        )
        parser.add_argument(
            "--overwrite-images",
            action="store_true",
            help="Replace existing image and thumbnail URLs when new values are found.",
        )
        parser.add_argument(
            "--cache-images",
            action="store_true",
            help="Download item images to local media storage and prefer them in the UI.",
        )
        parser.add_argument(
            "--social-only",
            action="store_true",
            help="Only process Instagram and TikTok items.",
        )

    def handle(self, *args, **options):
        queryset = ContentItem.objects.all().order_by("pk")
        if options["social_only"]:
            queryset = queryset.filter(source_platform__in=["Instagram", "TikTok"])
        if not options["all"]:
            if options["cache_images"]:
                queryset = queryset.filter(image_file="")
            else:
                queryset = queryset.filter(image_url="", thumbnail_url="")

        updated = 0
        scanned = 0
        for item in queryset:
            scanned += 1
            metadata = fetch_url_metadata(item.url)
            changed_fields = []
            for field in ("image_url", "thumbnail_url", "favicon_url"):
                value = metadata.data.get(field)
                if not value:
                    continue
                if options["overwrite_images"] or not getattr(item, field):
                    setattr(item, field, value)
                    changed_fields.append(field)

            for field in ("canonical_url", "embed_url", "source_platform", "site_name", "content_type"):
                value = metadata.data.get(field)
                if value and not getattr(item, field):
                    setattr(item, field, value)
                    changed_fields.append(field)

            if options["cache_images"]:
                image_source = metadata.data.get("thumbnail_url") or metadata.data.get("image_url") or item.thumbnail_url or item.image_url
                if image_source and (options["overwrite_images"] or not item.image_file):
                    image_name, image_bytes = download_image(image_source)
                    if image_name and image_bytes:
                        item.image_file.save(f"{item.pk}-{image_name}", ContentFile(image_bytes), save=False)
                        changed_fields.append("image_file")
                    else:
                        self.stdout.write(self.style.WARNING(f"{item.pk}: could not cache image"))

            if changed_fields:
                item.save(update_fields=sorted(set(changed_fields + ["updated_at"])))
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"{item.pk}: updated {', '.join(sorted(set(changed_fields)))}"))
            else:
                self.stdout.write(f"{item.pk}: no image found")

            if metadata.error:
                self.stdout.write(self.style.WARNING(f"{item.pk}: {metadata.error}"))

        self.stdout.write(self.style.SUCCESS(f"Scanned {scanned} item(s), updated {updated}."))


def download_image(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": IMAGE_USER_AGENT, "Accept": "image/avif,image/webp,image/*,*/*"},
            timeout=IMAGE_TIMEOUT,
        )
        response.raise_for_status()
    except Exception:
        return "", b""

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type and not content_type.startswith("image/"):
        return "", b""

    extension = extension_for_response(url, content_type)
    return f"thumb{extension}", response.content


def extension_for_response(url, content_type):
    content_extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/avif": ".avif",
    }
    if content_type in content_extensions:
        return content_extensions[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"
