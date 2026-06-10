from django.contrib import admin

from .models import Channel, Collection, ContentItem, ContentItemVisit, MagicLoginToken, Tag, TelegramAccount


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name", "description", "owner__username", "owner__email")
    exclude = ("is_public",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(MagicLoginToken)
class MagicLoginTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "expires_at", "used_at", "created_at")
    list_filter = ("created_at", "expires_at", "used_at")
    search_fields = ("email", "user__username", "user__email")
    readonly_fields = ("email", "user", "token_hash", "expires_at", "used_at", "created_at")


@admin.register(TelegramAccount)
class TelegramAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_user_id", "username", "chat_id", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "username", "first_name", "last_name", "telegram_user_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "channel", "visibility", "content_type", "display_source", "author", "created_at")
    list_filter = ("visibility", "content_type", "source_platform", "site_name", "language", "created_at")
    search_fields = ("title", "url", "description", "source_platform", "site_name", "author", "user__username")
    autocomplete_fields = ("user", "channel")
    filter_horizontal = ("tags",)
    readonly_fields = ("metadata_json", "created_at", "updated_at")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "channel", "visibility", "updated_at")
    list_filter = ("visibility", "created_at", "updated_at")
    search_fields = ("title", "description", "user__username", "channel__name")
    autocomplete_fields = ("user", "channel")
    filter_horizontal = ("items",)


@admin.register(ContentItemVisit)
class ContentItemVisitAdmin(admin.ModelAdmin):
    list_display = ("item", "user", "visit_count", "last_visited_at")
    list_filter = ("last_visited_at",)
    search_fields = ("item__title", "user__username", "user__email")
    autocomplete_fields = ("item", "user")
    readonly_fields = ("first_visited_at", "last_visited_at")
