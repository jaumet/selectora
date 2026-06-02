from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
import secrets


def generate_telegram_link_code():
    return secrets.token_urlsafe(8)


class Channel(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="channel",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    cover_image = models.FileField(upload_to="channel_covers/", blank=True)
    cover_image_url = models.URLField(max_length=500, blank=True)
    is_public = models.BooleanField(default=False)
    telegram_link_code = models.CharField(
        max_length=32,
        db_index=True,
        default=generate_telegram_link_code,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner__username"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("public_channel", kwargs={"username": self.owner.username})

    @property
    def display_cover_image_url(self):
        if self.cover_image:
            return self.cover_image.url
        return self.cover_image_url


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MagicLoginToken(models.Model):
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="magic_login_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()


class TelegramAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_account",
    )
    telegram_user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=160, blank=True)
    first_name = models.CharField(max_length=160, blank=True)
    last_name = models.CharField(max_length=160, blank=True)
    chat_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.username or str(self.telegram_user_id)


class ContentItem(models.Model):
    class ContentType(models.TextChoices):
        VIDEO = "video", "Video"
        PODCAST = "podcast", "Podcast"
        ARTICLE = "article", "Article"
        NEWSLETTER = "newsletter", "Newsletter"
        MUSIC = "music", "Music"
        SOCIAL = "social", "Social"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_items",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    canonical_url = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    favicon_url = models.URLField(max_length=500, blank=True)
    site_name = models.CharField(max_length=160, blank=True)
    source_platform = models.CharField(max_length=120, blank=True)
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.OTHER,
    )
    author = models.CharField(max_length=160, blank=True)
    published_date = models.DateTimeField(blank=True, null=True)
    duration = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=32, blank=True)
    embed_url = models.URLField(max_length=500, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="content_items")
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("contentitem_detail", kwargs={"pk": self.pk})

    @property
    def display_image_url(self):
        return self.thumbnail_url or self.image_url

    @property
    def display_source(self):
        return self.source_platform or self.site_name

    @property
    def is_vertical_embed(self):
        width = self.metadata_json.get("video_width") if isinstance(self.metadata_json, dict) else None
        height = self.metadata_json.get("video_height") if isinstance(self.metadata_json, dict) else None
        if width and height:
            try:
                return int(height) > int(width)
            except (TypeError, ValueError):
                pass
        return any(platform in self.embed_url for platform in ("instagram.com", "tiktok.com"))

    @property
    def is_instagram_embed(self):
        return "instagram.com" in (self.embed_url or self.canonical_url or self.url)
