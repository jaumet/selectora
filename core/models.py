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
    is_public = models.BooleanField(default=True)
    telegram_link_code = models.CharField(
        max_length=32,
        db_index=True,
        default=generate_telegram_link_code,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner__username"]

    def save(self, *args, **kwargs):
        self.is_public = True
        super().save(*args, **kwargs)

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
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    class ExpiryUnit(models.TextChoices):
        YEARS = "years", "Any"
        MONTHS = "months", "Mes"
        WEEKS = "weeks", "Setmana"
        DAYS = "days", "Dia"
        HOURS = "hours", "Hora"
        MINUTES = "minutes", "Minut"

    class Priority(models.TextChoices):
        LOW = "low", "Baixa"
        NORMAL = "normal", "Normal"
        HIGH = "high", "Alta"

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
    image_file = models.FileField(upload_to="item_images/", blank=True)
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
    personal_comment = models.TextField(blank=True)
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    internal_context = models.TextField(blank=True)
    expiry_amount = models.PositiveSmallIntegerField(blank=True, null=True)
    expiry_unit = models.CharField(
        max_length=16,
        choices=ExpiryUnit.choices,
        blank=True,
    )
    embed_url = models.URLField(max_length=500, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
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

    def get_public_url(self):
        return reverse("public_item", kwargs={"pk": self.pk})

    @property
    def is_publicly_visible(self):
        return self.visibility == self.Visibility.PUBLIC and self.channel.is_public

    @property
    def display_image_url(self):
        if self.image_file:
            return self.image_file.url
        return self.thumbnail_url or self.image_url

    @property
    def display_source(self):
        return self.source_platform or self.site_name

    @property
    def priority_label(self):
        return self.get_priority_display()

    @property
    def personal_expiry_label(self):
        if not self.expiry_amount or not self.expiry_unit:
            return ""
        singular = {
            self.ExpiryUnit.YEARS: "any",
            self.ExpiryUnit.MONTHS: "mes",
            self.ExpiryUnit.WEEKS: "setmana",
            self.ExpiryUnit.DAYS: "dia",
            self.ExpiryUnit.HOURS: "hora",
            self.ExpiryUnit.MINUTES: "minut",
        }[self.expiry_unit]
        plural = {
            self.ExpiryUnit.YEARS: "anys",
            self.ExpiryUnit.MONTHS: "mesos",
            self.ExpiryUnit.WEEKS: "setmanes",
            self.ExpiryUnit.DAYS: "dies",
            self.ExpiryUnit.HOURS: "hores",
            self.ExpiryUnit.MINUTES: "minuts",
        }[self.expiry_unit]
        unit = singular if self.expiry_amount == 1 else plural
        return f"{self.expiry_amount} {unit}"

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

    @property
    def rating_breakdown(self):
        options = [
            ("rating_passo_count", "Passo", "✋"),
            ("rating_curios_count", "Curiós", "?"),
            ("rating_val_la_pena_count", "Val la pena", "◆"),
            ("rating_recomanaria_count", "Recomanaria", "↗"),
            ("rating_must_count", "Must", "🔥"),
        ]
        return [
            {"label": label, "icon": icon, "count": count}
            for attr, label, icon in options
            if (count := getattr(self, attr, 0))
        ]

    @property
    def nuance_breakdown(self):
        counts = {}
        for rating in self.ratings.all():
            for nuance in rating.nuance_values:
                counts[nuance] = counts.get(nuance, 0) + 1
        return [
            {"label": option["label"], "icon": option["icon"], "count": counts.get(option["value"], 0)}
            for option in ContentItemRating.nuance_options()
            if counts.get(option["value"], 0)
        ]


class ContentItemVisit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_item_visits",
    )
    item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    visit_count = models.PositiveIntegerField(default=0)
    first_visited_at = models.DateTimeField(auto_now_add=True)
    last_visited_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_visited_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="unique_content_item_visit"),
        ]

    def __str__(self):
        return f"{self.user} visited {self.item}"


class ContentItemViewEvent(models.Model):
    item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="content_item_view_events",
        blank=True,
        null=True,
    )
    viewed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["item", "viewed_at"]),
        ]

    def __str__(self):
        return f"{self.item} viewed at {self.viewed_at:%Y-%m-%d %H:%M}"


class ContentItemRating(models.Model):
    class MainValue(models.TextChoices):
        PASSO = "passo", "Passo"
        CURIOS = "curios", "Curiós"
        VAL_LA_PENA = "val_la_pena", "Val la pena"
        RECOMANARIA = "recomanaria", "Recomanaria"
        MUST = "must", "Must"

    class Nuance(models.TextChoices):
        ORIGINAL = "original", "Original"
        UTIL = "util", "Útil"
        BEN_EXPLICAT = "ben_explicat", "Ben explicat"
        INSPIRADOR = "inspirador", "Inspirador"
        NECESSARI = "necessari", "Necessari"
        DISCUTIBLE = "discutible", "Discutible"
        REPETIT = "repetit", "Repetit"
        NO_ES_PER_MI = "no_es_per_mi", "No és per mi"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_item_ratings",
    )
    item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    main_value = models.CharField(max_length=24, choices=MainValue.choices)
    nuance_values = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="unique_content_item_rating"),
        ]

    def __str__(self):
        return f"{self.user} rated {self.item}: {self.main_value}"

    @classmethod
    def main_options(cls):
        return [
            {"value": cls.MainValue.PASSO, "label": "Passo", "icon": "✋"},
            {"value": cls.MainValue.CURIOS, "label": "Curiós", "icon": "?"},
            {"value": cls.MainValue.VAL_LA_PENA, "label": "Val la pena", "icon": "◆"},
            {"value": cls.MainValue.RECOMANARIA, "label": "Recomanaria", "icon": "↗"},
            {"value": cls.MainValue.MUST, "label": "Must", "icon": "🔥"},
        ]

    @classmethod
    def nuance_options(cls):
        return [
            {"value": cls.Nuance.ORIGINAL, "label": "Original", "icon": "✦"},
            {"value": cls.Nuance.UTIL, "label": "Útil", "icon": "✓"},
            {"value": cls.Nuance.BEN_EXPLICAT, "label": "Ben explicat", "icon": "☰"},
            {"value": cls.Nuance.INSPIRADOR, "label": "Inspirador", "icon": "◌"},
            {"value": cls.Nuance.NECESSARI, "label": "Necessari", "icon": "!"},
            {"value": cls.Nuance.DISCUTIBLE, "label": "Discutible", "icon": "↔"},
            {"value": cls.Nuance.REPETIT, "label": "Repetit", "icon": "↻"},
            {"value": cls.Nuance.NO_ES_PER_MI, "label": "No és per mi", "icon": "∅"},
        ]


class Collection(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    items = models.ManyToManyField(ContentItem, blank=True, related_name="collections")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "title"]

    def __str__(self):
        return self.title

    def get_public_url(self):
        return reverse("public_collection", kwargs={"pk": self.pk})

    @property
    def is_publicly_visible(self):
        return self.visibility == self.Visibility.PUBLIC and self.channel.is_public
