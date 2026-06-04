from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, FormView, ListView, RedirectView, TemplateView, UpdateView, View
from django.conf import settings

from .auth import consume_magic_token, send_magic_login_email
from .content_services import create_content_item_from_url, get_or_create_channel
from .forms import ChannelForm, ContentItemForm, MagicLoginRequestForm
from .models import Channel, Collection, ContentItem, ContentItemVisit, Tag
from .telegram import process_telegram_update


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_items = ContentItem.objects.filter(channel__is_public=True, visibility=ContentItem.Visibility.PUBLIC)
        public_channels = (
            Channel.objects.filter(is_public=True)
            .select_related("owner")
            .annotate(item_count=Count("items"))
            .filter(item_count__gt=0)
            .order_by("-updated_at")
        )
        context["public_channels"] = public_channels[:8]
        public_collections = list(
            public_collections_queryset()
            .select_related("channel", "user")
            .prefetch_related(public_collection_items_prefetch())
            .order_by("-updated_at")[:8]
        )
        context["public_collections"] = public_collections
        pending_public_items = []
        if self.request.user.is_authenticated:
            pending_public_items = list(
                public_items.exclude(visits__user=self.request.user)
                .select_related("channel", "user")
                .prefetch_related("tags")
                .order_by("-created_at")[:12]
            )
        context["pending_public_items"] = pending_public_items
        recent_public_items = list(
            public_items
            .select_related("channel", "user")
            .prefetch_related("tags")
            .order_by("-created_at")[:10]
        )
        video_public_items = list(
            public_items.filter(content_type=ContentItem.ContentType.VIDEO)
            .select_related("channel", "user")
            .prefetch_related("tags")
            .order_by("-created_at")[:12]
        )
        podcast_public_items = list(
            public_items.filter(content_type=ContentItem.ContentType.PODCAST)
            .select_related("channel", "user")
            .prefetch_related("tags")
            .order_by("-created_at")[:12]
        )
        article_public_items = list(
            public_items.filter(content_type=ContentItem.ContentType.ARTICLE)
            .select_related("channel", "user")
            .prefetch_related("tags")
            .order_by("-created_at")[:12]
        )
        context["home_sections"] = ordered_sections(
            [
                {"title": "Col.leccions", "type": "collections", "collections": public_collections},
                {"title": "Items pendents de veure", "type": "items", "items": pending_public_items},
                {"title": "Ultimes seleccions", "type": "items", "items": recent_public_items, "link_url": reverse("explore"), "link_label": "Veure tot"},
                {"title": "Videos i socials", "type": "items", "items": video_public_items},
                {"title": "Articles", "type": "items", "items": article_public_items},
                {"title": "Podcasts", "type": "items", "items": podcast_public_items},
            ]
        )
        context["global_tags"] = ordered_tags(
            Tag.objects.filter(content_items__channel__is_public=True)
            .filter(content_items__visibility=ContentItem.Visibility.PUBLIC)
            .annotate(item_count=Count("content_items", distinct=True))
            .filter(item_count__gt=0),
            self.request.GET,
        )
        context["global_tags"] = context["global_tags"][:28]
        context["content_types"] = ContentItem.ContentType.choices
        context["platforms"] = (
            public_items.exclude(source_platform="").order_by("source_platform").values_list("source_platform", flat=True).distinct()
        )
        context["authors"] = public_items.exclude(author="").order_by("author").values_list("author", flat=True).distinct()
        context["languages"] = public_items.exclude(language="").order_by("language").values_list("language", flat=True).distinct()
        context.update(tag_sort_context(self.request.GET))
        return context


class LegacyHtmlRedirectView(RedirectView):
    pattern_name = "home"
    permanent = False


class MagicLoginRequestView(FormView):
    template_name = "registration/magic_login.html"
    form_class = MagicLoginRequestForm
    success_url = "/accounts/check-email/"

    def form_valid(self, form):
        magic_url = send_magic_login_email(self.request, form.cleaned_data["email"])
        if self.request.user.is_staff or self.request.get_host().startswith(("127.0.0.1", "localhost")):
            self.request.session["last_magic_login_url"] = magic_url
        return super().form_valid(form)


class MagicLoginSentView(TemplateView):
    template_name = "registration/magic_login_sent.html"


class MagicLoginConfirmView(TemplateView):
    template_name = "registration/magic_login_confirm.html"

    def get(self, request, *args, **kwargs):
        user = consume_magic_token(kwargs["token"])
        if not user:
            messages.warning(request, "Aquest enllaç ja no és valid. Demana'n un de nou.")
            return redirect("login")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Has entrat a Selectora.")
        return redirect("dashboard")


def selected_values(params, key):
    if hasattr(params, "getlist"):
        return [value for value in params.getlist(key) if value]
    value = params.get(key, "")
    return [value] if value else []


def query_url(params, key, value, remove=False):
    query = params.copy()
    values = selected_values(query, key)
    if remove:
        values = [item for item in values if item != value]
    elif value not in values:
        values.append(value)
    if values:
        query.setlist(key, values)
    else:
        query.pop(key, None)
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


def set_query_url(params, key, value):
    query = params.copy()
    query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


def clear_query_values_url(params, key):
    query = params.copy()
    query.pop(key, None)
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


def tag_sort_context(params):
    current = params.get("tag_sort", "count")
    if current not in {"count", "alpha"}:
        current = "count"
    return {
        "tag_sort": current,
        "tag_sort_count_url": set_query_url(params, "tag_sort", "count"),
        "tag_sort_alpha_url": set_query_url(params, "tag_sort", "alpha"),
        "clear_tags_url": clear_query_values_url(params, "tag"),
    }


def ordered_tags(queryset, params):
    if params.get("tag_sort") == "alpha":
        return queryset.order_by("name")
    return queryset.order_by("-item_count", "name")


def tag_filter_options(tags, params):
    selected = set(selected_values(params, "tag"))
    return [
        {
            "tag": tag,
            "active": tag.slug in selected,
            "toggle_url": query_url(params, "tag", tag.slug, remove=tag.slug in selected),
            "remove_url": query_url(params, "tag", tag.slug, remove=True),
        }
        for tag in tags
    ]


def filtered_items(queryset, params):
    content_type = params.get("type", "")
    platform = params.get("platform", "")
    author = params.get("author", "")
    language = params.get("language", "")
    tags = selected_values(params, "tag")
    query = params.get("q", "")
    ordering = params.get("sort", "-created_at")

    if content_type:
        queryset = queryset.filter(content_type=content_type)
    if platform:
        queryset = queryset.filter(Q(source_platform=platform) | Q(site_name=platform))
    if author:
        queryset = queryset.filter(author=author)
    if language:
        queryset = queryset.filter(language=language)
    if tags:
        queryset = queryset.filter(tags__slug__in=tags).distinct()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(source_platform__icontains=query)
            | Q(author__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    allowed_ordering = {
        "-created_at": "-created_at",
        "created_at": "created_at",
        "title": "title",
        "platform": "source_platform",
        "type": "content_type",
    }
    return queryset.order_by(allowed_ordering.get(ordering, "-created_at"))


def public_items_queryset():
    return ContentItem.objects.filter(
        channel__is_public=True,
        visibility=ContentItem.Visibility.PUBLIC,
    )


def public_collections_queryset():
    return Collection.objects.filter(
        channel__is_public=True,
        visibility=Collection.Visibility.PUBLIC,
    )


def public_collection_items_prefetch():
    return Prefetch(
        "items",
        queryset=public_items_queryset().select_related("channel", "user").order_by("-created_at"),
        to_attr="public_preview_items",
    )


def absolute_url(request, path):
    return request.build_absolute_uri(path)


def item_share_text(item, url):
    parts = ["I found this on Selectora:", "", item.title]
    if item.description:
        parts.extend(["", item.description])
    parts.extend(["", url])
    return "\n".join(parts)


def collection_share_text(collection, url):
    parts = ["A human-curated collection on Selectora:", "", collection.title]
    if collection.description:
        parts.extend(["", collection.description])
    parts.extend(["", url])
    return "\n".join(parts)


def channel_share_text(channel, url):
    return f"{channel.name}'s Selectora channel:\n\n{url}"


def share_context(title, url, text):
    return {
        "share_title": title,
        "share_url": url,
        "share_text": text,
    }


def mark_item_visited(user, item):
    visit, _ = ContentItemVisit.objects.get_or_create(user=user, item=item)
    ContentItemVisit.objects.filter(pk=visit.pk).update(
        visit_count=visit.visit_count + 1,
        last_visited_at=timezone.now(),
    )


def can_view_item_queryset(user):
    queryset = ContentItem.objects.filter(channel__is_public=True, visibility=ContentItem.Visibility.PUBLIC)
    if user.is_authenticated:
        return ContentItem.objects.filter(
            Q(channel__is_public=True, visibility=ContentItem.Visibility.PUBLIC)
            | Q(user=user)
        )
    return queryset


def section_size(section):
    if section.get("type") == "collections":
        return len(section.get("collections", []))
    return len(section.get("items", []))


def ordered_sections(sections):
    return sorted(
        [section for section in sections if section_size(section)],
        key=lambda section: (-section_size(section), section["title"]),
    )


def channel_context(channel, items, params, include_private=True, viewer_user=None):
    all_items = channel.items.select_related("channel", "user").prefetch_related("tags")
    if not include_private:
        all_items = all_items.filter(visibility=ContentItem.Visibility.PUBLIC)
    tag_queryset = Tag.objects.filter(content_items__channel=channel)
    if not include_private:
        tag_queryset = tag_queryset.filter(content_items__visibility=ContentItem.Visibility.PUBLIC)
    tags = ordered_tags(
        tag_queryset.annotate(item_count=Count("content_items", filter=Q(content_items__channel=channel), distinct=True))
        .distinct(),
        params,
    )
    active_filters = any(
        params.get(key) if key != "tag" else selected_values(params, "tag")
        for key in ("q", "type", "platform", "author", "language", "tag", "sort")
        if key != "sort"
    )
    video_items = list(all_items.filter(content_type=ContentItem.ContentType.VIDEO)[:12])
    article_items = list(all_items.filter(content_type=ContentItem.ContentType.ARTICLE)[:12])
    podcast_items = list(all_items.filter(content_type=ContentItem.ContentType.PODCAST)[:12])
    music_items = list(all_items.filter(content_type=ContentItem.ContentType.MUSIC)[:12])
    recommended_items = list(all_items.filter(tags__slug="recomanat")[:12])
    recent_items = list(all_items.order_by("-created_at")[:12])
    pending_items = []
    if viewer_user and viewer_user.is_authenticated:
        pending_items = list(all_items.exclude(visits__user=viewer_user).order_by("-created_at")[:12])
    return {
        "channel": channel,
        "items": items,
        "recent_items": recent_items,
        "video_items": video_items,
        "article_items": article_items,
        "podcast_items": podcast_items,
        "music_items": music_items,
        "recommended_items": recommended_items,
        "item_sections": ordered_sections(
            [
                {"title": "Items pendents de veure", "type": "items", "items": pending_items},
                {"title": "Ultimes seleccions", "type": "items", "items": recent_items},
                {"title": "Videos", "type": "items", "items": video_items},
                {"title": "Articles i lectures", "type": "items", "items": article_items},
                {"title": "Podcasts", "type": "items", "items": podcast_items},
                {"title": "Musica", "type": "items", "items": music_items},
                {"title": "Recomanats pel creador", "type": "items", "items": recommended_items},
            ]
        ),
        "platforms": all_items.exclude(source_platform="").values_list("source_platform", flat=True).distinct(),
        "authors": all_items.exclude(author="").values_list("author", flat=True).distinct(),
        "languages": all_items.exclude(language="").values_list("language", flat=True).distinct(),
        "content_types": ContentItem.ContentType.choices,
        "tags": tags,
        "tag_options": tag_filter_options(tags, params),
        "selected_tags": [option for option in tag_filter_options(tags, params) if option["active"]],
        "filters": params,
        "active_filters": active_filters,
        **tag_sort_context(params),
    }


class DashboardView(LoginRequiredMixin, ListView):
    model = ContentItem
    template_name = "core/dashboard.html"
    context_object_name = "items"

    def get_queryset(self):
        self.channel = get_or_create_channel(self.request.user)
        queryset = self.channel.items.select_related("channel", "user").prefetch_related("tags")
        return filtered_items(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(channel_context(self.channel, context["items"], self.request.GET, viewer_user=self.request.user))
        context["is_owner"] = True
        return context


class ChannelUpdateView(LoginRequiredMixin, UpdateView):
    model = Channel
    form_class = ChannelForm
    template_name = "core/channel_form.html"

    def get_object(self, queryset=None):
        return get_or_create_channel(self.request.user)

    def get_success_url(self):
        return self.object.get_absolute_url() if self.object.is_public else reverse("dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Canal actualitzat.")
        return super().form_valid(form)


class ExploreView(ListView):
    model = ContentItem
    template_name = "core/explore.html"
    context_object_name = "items"

    def get_queryset(self):
        queryset = (
            public_items_queryset()
            .select_related("channel", "user")
            .prefetch_related("tags")
        )
        return filtered_items(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_items = public_items_queryset()
        context["content_types"] = ContentItem.ContentType.choices
        context["platforms"] = public_items.exclude(source_platform="").values_list("source_platform", flat=True).distinct()
        context["authors"] = public_items.exclude(author="").values_list("author", flat=True).distinct()
        context["languages"] = public_items.exclude(language="").values_list("language", flat=True).distinct()
        context["tags"] = ordered_tags(
            Tag.objects.filter(content_items__channel__is_public=True)
            .filter(content_items__visibility=ContentItem.Visibility.PUBLIC)
            .annotate(item_count=Count("content_items", distinct=True))
            .filter(item_count__gt=0),
            self.request.GET,
        )
        context["tag_options"] = tag_filter_options(context["tags"], self.request.GET)
        context["selected_tags"] = [option for option in context["tag_options"] if option["active"]]
        context["filters"] = self.request.GET
        context.update(tag_sort_context(self.request.GET))
        return context


class ContentItemCreateView(LoginRequiredMixin, CreateView):
    model = ContentItem
    form_class = ContentItemForm
    template_name = "core/contentitem_form.html"

    def form_valid(self, form):
        manual_data = {
            "title": form.cleaned_data.get("title", ""),
            "description": form.cleaned_data.get("description", ""),
            "image_url": form.cleaned_data.get("image_url", ""),
            "source_platform": form.cleaned_data.get("source_platform", ""),
            "content_type": form.cleaned_data.get("content_type", ""),
            "visibility": form.cleaned_data.get("visibility") or ContentItem.Visibility.PUBLIC,
            "author": form.cleaned_data.get("author", ""),
            "language": form.cleaned_data.get("language", ""),
        }
        if manual_data["content_type"] == ContentItem.ContentType.OTHER:
            manual_data.pop("content_type")
        manual_tags = [name.strip() for name in form.cleaned_data.get("tag_list", "").split(",") if name.strip()]
        item, created, error = create_content_item_from_url(
            self.request.user,
            form.cleaned_data["url"],
            manual_data=manual_data,
            manual_tags=manual_tags,
        )
        self.object = item
        if not created:
            messages.info(self.request, "Aquest contingut ja era al teu canal.")
            return redirect(item.get_absolute_url())
        if error:
            messages.warning(self.request, "No s'han pogut obtenir totes les metadades. Pots editar-les manualment.")
        return redirect(item.get_absolute_url())


class ContentItemUpdateView(LoginRequiredMixin, UpdateView):
    model = ContentItem
    form_class = ContentItemForm
    template_name = "core/contentitem_form.html"

    def get_queryset(self):
        return ContentItem.objects.filter(user=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save_tags(self.object)
        return response


class ContentItemDetailView(DetailView):
    model = ContentItem
    template_name = "core/contentitem_detail.html"
    context_object_name = "item"

    def get_queryset(self):
        queryset = ContentItem.objects.select_related("channel", "user").prefetch_related("tags")
        return queryset.filter(pk__in=can_view_item_queryset(self.request.user).values("pk"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_owner"] = self.request.user.is_authenticated and self.object.user == self.request.user
        context["is_item_visited"] = (
            self.request.user.is_authenticated
            and ContentItemVisit.objects.filter(user=self.request.user, item=self.object).exists()
        )
        return context


class ContentItemVisitedView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        item = get_object_or_404(can_view_item_queryset(request.user), pk=kwargs["pk"])
        mark_item_visited(request.user, item)
        return JsonResponse({"ok": True})


class ContentItemVisitToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        item = get_object_or_404(can_view_item_queryset(request.user), pk=kwargs["pk"])
        visited = request.POST.get("visited") == "1"
        if visited:
            mark_item_visited(request.user, item)
        else:
            ContentItemVisit.objects.filter(user=request.user, item=item).delete()
        return redirect(item.get_absolute_url())


class PublicChannelView(ListView):
    model = ContentItem
    template_name = "core/public_channel.html"
    context_object_name = "items"

    def dispatch(self, request, *args, **kwargs):
        self.channel = get_object_or_404(Channel, owner__username=kwargs["username"], is_public=True)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.channel.items.filter(visibility=ContentItem.Visibility.PUBLIC).select_related("channel", "user").prefetch_related("tags")
        return filtered_items(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            channel_context(
                self.channel,
                context["items"],
                self.request.GET,
                include_private=False,
                viewer_user=self.request.user,
            )
        )
        context["is_owner"] = self.request.user.is_authenticated and self.channel.owner == self.request.user
        public_collections = list(
            public_collections_queryset()
            .filter(channel=self.channel)
            .prefetch_related(public_collection_items_prefetch())
        )
        context["public_collections"] = public_collections
        context["item_sections"] = ordered_sections(
            [
                {"title": "Col.leccions", "type": "collections", "collections": public_collections},
                *context["item_sections"],
            ]
        )
        url = absolute_url(self.request, self.channel.get_absolute_url())
        context.update(share_context(self.channel.name, url, channel_share_text(self.channel, url)))
        return context


def unavailable(request, message):
    return render(request, "core/public_unavailable.html", {"message": message}, status=404)


class PublicItemShareView(TemplateView):
    template_name = "core/public_item.html"

    def get(self, request, *args, **kwargs):
        item = (
            ContentItem.objects.select_related("channel", "user")
            .prefetch_related("collections")
            .filter(pk=kwargs["pk"])
            .first()
        )
        if not item or not item.is_publicly_visible:
            return unavailable(request, "This content is private or unavailable.")
        collection = item.collections.filter(
            visibility=Collection.Visibility.PUBLIC,
            channel__is_public=True,
        ).first()
        url = absolute_url(request, item.get_public_url())
        context = {
            "item": item,
            "collection": collection,
            **share_context(item.title, url, item_share_text(item, url)),
        }
        return render(request, self.template_name, context)


class PublicCollectionShareView(TemplateView):
    template_name = "core/public_collection.html"

    def get(self, request, *args, **kwargs):
        collection = (
            Collection.objects.select_related("channel", "user")
            .filter(pk=kwargs["pk"])
            .first()
        )
        if not collection or not collection.is_publicly_visible:
            return unavailable(request, "This collection is private or unavailable.")
        items = collection.items.filter(
            channel__is_public=True,
            visibility=ContentItem.Visibility.PUBLIC,
        ).select_related("channel", "user")
        url = absolute_url(request, collection.get_public_url())
        context = {
            "collection": collection,
            "items": items,
            **share_context(collection.title, url, collection_share_text(collection, url)),
        }
        return render(request, self.template_name, context)


class PublicUserChannelShareView(ListView):
    model = ContentItem
    template_name = "core/public_user_channel.html"
    context_object_name = "items"

    def dispatch(self, request, *args, **kwargs):
        self.user_object = get_object_or_404(get_user_model(), pk=kwargs["pk"])
        self.channel = Channel.objects.filter(owner=self.user_object, is_public=True).first()
        if not self.channel:
            return unavailable(request, "This channel is private or unavailable.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return public_items_queryset().filter(channel=self.channel).select_related("channel", "user").prefetch_related("tags")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = self.channel
        context["public_collections"] = public_collections_queryset().filter(channel=self.channel).prefetch_related(public_collection_items_prefetch())
        url = absolute_url(self.request, reverse("public_user_channel", kwargs={"pk": self.user_object.pk}))
        context.update(share_context(self.channel.name, url, channel_share_text(self.channel, url)))
        return context


def dashboard_redirect(request):
    return redirect("dashboard")


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(TemplateView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
        received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if expected_secret and received_secret != expected_secret:
            return HttpResponseForbidden("Invalid Telegram secret")

        result = process_telegram_update(request.body)
        return JsonResponse({"ok": True, **result})
