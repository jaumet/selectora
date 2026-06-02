import json
from unittest.mock import patch
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .metadata_fetcher import extract_metadata, fetch_url_metadata
from .auth import create_magic_login
from .models import Channel, ContentItem, MagicLoginToken, Tag, TelegramAccount


HTML_WITH_METADATA = """
<!doctype html>
<html lang="ca">
<head>
  <title>Fallback title</title>
  <link rel="canonical" href="https://example.com/canonical">
  <meta property="og:title" content="Titol Open Graph">
  <meta property="og:description" content="Descripcio Open Graph">
  <meta property="og:image" content="/cover.jpg">
  <meta property="og:site_name" content="Example Magazine">
  <meta property="og:type" content="article">
  <meta name="author" content="Ada Editor">
  <meta name="keywords" content="cultura, cinema, recomanat">
  <script type="application/ld+json">
    {"@type": "Article", "datePublished": "2026-05-20T12:00:00+02:00"}
  </script>
</head>
<body></body>
</html>
"""


class FakeResponse:
    headers = {"content-type": "text/html; charset=utf-8"}
    text = HTML_WITH_METADATA

    def __init__(self, url="https://example.com/article"):
        self.url = url

    def raise_for_status(self):
        return None


class FakeJsonResponse:
    headers = {"content-type": "application/json"}

    def __init__(self, payload):
        self.payload = payload
        self.url = "https://www.tiktok.com/oembed"
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class MetadataFetcherTests(TestCase):
    def test_extract_metadata_from_html(self):
        metadata = extract_metadata(HTML_WITH_METADATA, "https://example.com/article")

        self.assertEqual(metadata["title"], "Titol Open Graph")
        self.assertEqual(metadata["description"], "Descripcio Open Graph")
        self.assertEqual(metadata["image_url"], "https://example.com/cover.jpg")
        self.assertEqual(metadata["site_name"], "Example Magazine")
        self.assertEqual(metadata["content_type"], ContentItem.ContentType.ARTICLE)
        self.assertIn("recomanat", metadata["tags"])

    def test_fetch_metadata_falls_back_when_request_fails(self):
        def failing_get(*args, **kwargs):
            raise TimeoutError("timeout")

        result = fetch_url_metadata("https://example.com/missing", http_get=failing_get)

        self.assertTrue(result.error)
        self.assertEqual(result.data["source_platform"], "example.com")
        self.assertEqual(result.data["content_type"], ContentItem.ContentType.OTHER)

    def test_youtube_embed_iframe_has_referrer_policy(self):
        user = get_user_model().objects.create_user(username="owner", password="test-password")
        channel = Channel.objects.create(owner=user, name="Canal", is_public=True)
        item = ContentItem.objects.create(
            user=user,
            channel=channel,
            title="Video",
            url="https://youtu.be/eh1hrYQi4FY?si=2VUUOTC3qWwQxpwz",
            embed_url="https://www.youtube.com/embed/eh1hrYQi4FY",
            content_type=ContentItem.ContentType.VIDEO,
        )

        response = self.client.get(reverse("contentitem_detail", kwargs={"pk": item.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'referrerpolicy="strict-origin-when-cross-origin"')
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_instagram_detail_uses_iframe_embed(self):
        user = get_user_model().objects.create_user(username="insta", password="test-password")
        channel = Channel.objects.create(owner=user, name="Canal", is_public=True)
        item = ContentItem.objects.create(
            user=user,
            channel=channel,
            title="Instagram Reel",
            url="https://www.instagram.com/p/DMc6SczOX56/",
            canonical_url="https://www.instagram.com/reel/DMc6SczOX56/",
            embed_url="https://www.instagram.com/reel/DMc6SczOX56/embed",
            content_type=ContentItem.ContentType.VIDEO,
        )

        response = self.client.get(reverse("contentitem_detail", kwargs={"pk": item.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="https://www.instagram.com/reel/DMc6SczOX56/embed"')

    def test_podcast_index_without_social_metadata_uses_visible_content(self):
        html = """
        <html lang="ca">
          <head><title>La tertulia proscrita - VilaWeb</title></head>
          <body>
            <main>
              <h1>La tertúlia proscrita</h1>
              <a href="/noticies/episodi/">
                23.04.2026 La tertúlia proscrita: El jovent pren el relleu
                VilaWeb presenta un nou capítol amb Maria Maians i Txell Partal.
              </a>
            </main>
          </body>
        </html>
        """

        metadata = extract_metadata(html, "https://www.vilaweb.cat/podcasts/la-tertulia-proscrita/")

        self.assertEqual(metadata["title"], "La tertúlia proscrita")
        self.assertEqual(metadata["source_platform"], "VilaWeb")
        self.assertEqual(metadata["content_type"], ContentItem.ContentType.PODCAST)
        self.assertIn("El jovent pren el relleu", metadata["description"])
        self.assertEqual(metadata["metadata_json"]["latest_episode"]["date"], "23.04.2026")

    def test_instagram_reel_gets_platform_type_and_embed_url(self):
        html = """
        <html>
          <head>
            <meta property="og:site_name" content="Instagram">
            <meta property="og:url" content="https://www.instagram.com/dual_cat_oficial/reel/DYiAJdKM7gA/">
            <meta property="og:title" content="Dual.cat on Instagram">
            <meta property="og:image" content="https://cdn.example.com/reel.jpg">
            <meta name="twitter:title" content="Dual.cat (@dual_cat_oficial) • Instagram reel">
          </head>
        </html>
        """

        metadata = extract_metadata(html, "https://www.instagram.com/p/DYiAJdKM7gA/")

        self.assertEqual(metadata["source_platform"], "Instagram")
        self.assertEqual(metadata["content_type"], ContentItem.ContentType.VIDEO)
        self.assertEqual(metadata["embed_url"], "https://www.instagram.com/reel/DYiAJdKM7gA/embed")

    def test_tiktok_video_gets_platform_type_and_embed_url(self):
        metadata = extract_metadata(
            "<html><head><title>TikTok - Make Your Day</title></head></html>",
            "https://www.tiktok.com/@dual.cat3/video/7639623555843493142",
        )

        self.assertEqual(metadata["source_platform"], "TikTok")
        self.assertEqual(metadata["content_type"], ContentItem.ContentType.VIDEO)
        self.assertEqual(
            metadata["embed_url"],
            "https://www.tiktok.com/player/v1/7639623555843493142?controls=1&progress_bar=1&play_button=1&volume_control=1&fullscreen_button=1",
        )

    def test_tiktok_oembed_adds_title_author_thumbnail_and_dimensions(self):
        def fake_get(url, **kwargs):
            if "oembed" in url:
                return FakeJsonResponse(
                    {
                        "title": "Video horitzontal",
                        "author_name": "@dual.cat3",
                        "provider_name": "TikTok",
                        "thumbnail_url": "https://example.com/thumb.jpg",
                        "thumbnail_width": 1920,
                        "thumbnail_height": 1080,
                    }
                )
            return FakeResponse("https://www.tiktok.com/@dual.cat3/video/7638139327163141398")

        result = fetch_url_metadata(
            "https://www.tiktok.com/@dual.cat3/video/7638139327163141398",
            http_get=fake_get,
        )

        self.assertEqual(result.data["title"], "Video horitzontal")
        self.assertEqual(result.data["author"], "@dual.cat3")
        self.assertEqual(result.data["source_platform"], "TikTok")
        self.assertEqual(result.data["thumbnail_url"], "https://example.com/thumb.jpg")
        self.assertEqual(result.data["metadata_json"]["video_width"], 1920)
        self.assertEqual(result.data["metadata_json"]["video_height"], 1080)


class CoreViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="jaume",
            password="test-password",
        )
        self.channel = Channel.objects.create(
            owner=self.user,
            name="Canal de Jaume",
            description="Seleccio cultural.",
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selectora")

    def test_home_page_shows_public_channels_and_global_tags(self):
        self.channel.is_public = True
        self.channel.save()
        tag = Tag.objects.create(name="Cinema", slug="cinema")
        item = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Film",
            url="https://example.com/film",
            content_type=ContentItem.ContentType.VIDEO,
        )
        item.tags.add(tag)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Planeta")
        self.assertContains(response, "Canal de Jaume")
        self.assertContains(response, "Cinema")
        self.assertContains(response, reverse("explore") + "?tag=cinema")

    def test_home_page_compact_view_loads(self):
        self.channel.is_public = True
        self.channel.save()
        ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Video compacte",
            url="https://example.com/video",
            content_type=ContentItem.ContentType.VIDEO,
        )

        response = self.client.get(reverse("home"), {"view": "compact"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "compact-home")
        self.assertContains(response, "Video compacte")
        self.assertContains(response, "Canals publics")

    def test_explore_filters_by_global_tag(self):
        self.channel.is_public = True
        self.channel.save()
        cinema = Tag.objects.create(name="Cinema", slug="cinema")
        music = Tag.objects.create(name="Musica", slug="musica")
        film = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Film public",
            url="https://example.com/film",
        )
        song = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Song public",
            url="https://example.com/song",
        )
        film.tags.add(cinema)
        song.tags.add(music)

        response = self.client.get(reverse("explore"), {"tag": "cinema"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film public")
        self.assertNotContains(response, "https://example.com/song")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_magic_link_request_creates_user_token_and_sends_email(self):
        response = self.client.post(reverse("login"), {"email": "Nova@Example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(email__iexact="nova@example.com").exists())
        self.assertEqual(MagicLoginToken.objects.filter(email="nova@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/magic/", mail.outbox[0].body)

    def test_magic_link_logs_user_in_once(self):
        user, token, _ = create_magic_login("jaume@example.com")

        response = self.client.get(reverse("magic_login_confirm", kwargs={"token": token}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        second_response = self.client.get(reverse("magic_login_confirm", kwargs={"token": token}))

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(second_response.url, reverse("login"))

    def test_user_can_make_channel_public_from_settings(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("channel_update"),
            {
                "name": "Canal public",
                "description": "Ja es pot veure.",
                "cover_image_url": "",
                "is_public": "on",
            },
        )

        self.channel.refresh_from_db()
        self.assertTrue(self.channel.is_public)
        self.assertEqual(self.channel.name, "Canal public")
        self.assertEqual(response.status_code, 302)

    def test_user_can_upload_channel_cover_image(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.client.force_login(self.user)
                image = SimpleUploadedFile(
                    "cover.jpg",
                    b"fake image bytes",
                    content_type="image/jpeg",
                )

                response = self.client.post(
                    reverse("channel_update"),
                    {
                        "name": "Canal amb portada",
                        "description": "Portada local.",
                        "cover_image": image,
                        "cover_image_url": "",
                    },
                )

                self.channel.refresh_from_db()
                self.assertEqual(response.status_code, 302)
                self.assertTrue(self.channel.cover_image.name.startswith("channel_covers/"))
                self.assertIn("/media/channel_covers/", self.channel.display_cover_image_url)

    def test_channel_cover_upload_rejects_non_image_file(self):
        self.client.force_login(self.user)
        document = SimpleUploadedFile(
            "cover.txt",
            b"not an image",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("channel_update"),
            {
                "name": "Canal",
                "description": "",
                "cover_image": document,
                "cover_image_url": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ha de ser una imatge")

    def test_channel_cover_external_url_must_be_image_url(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("channel_update"),
            {
                "name": "Canal",
                "description": "",
                "cover_image_url": "https://example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ha d&#x27;apuntar directament a una imatge")

    @patch("core.telegram.send_telegram_message")
    def test_telegram_webhook_connects_account_with_channel_code(self, send_mock):
        payload = {
            "message": {
                "text": f"/connect {self.channel.telegram_link_code}",
                "from": {"id": 12345, "username": "jaume"},
                "chat": {"id": 67890},
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        account = TelegramAccount.objects.get(telegram_user_id=12345)
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.chat_id, 67890)
        send_mock.assert_called()

    @patch("core.content_services.fetch_url_metadata")
    @patch("core.telegram.send_telegram_message")
    def test_telegram_webhook_publishes_url_to_linked_channel(self, send_mock, metadata_mock):
        TelegramAccount.objects.create(user=self.user, telegram_user_id=12345, chat_id=67890)
        metadata_mock.return_value.data = {
            "title": "Article des de Telegram",
            "description": "Publicat compartint una URL.",
            "content_type": ContentItem.ContentType.ARTICLE,
            "tags": ["telegram"],
        }
        metadata_mock.return_value.error = ""
        payload = {
            "message": {
                "text": "Mira aixo https://example.com/telegram",
                "from": {"id": 12345, "username": "jaume"},
                "chat": {"id": 67890},
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        item = ContentItem.objects.get(url="https://example.com/telegram")
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.channel, self.channel)
        self.assertEqual(item.title, "Article des de Telegram")
        self.assertTrue(item.tags.filter(slug="telegram").exists())
        send_mock.assert_called()

    @override_settings(TELEGRAM_WEBHOOK_SECRET="expected-secret")
    def test_telegram_webhook_rejects_wrong_secret(self):
        response = self.client.post(
            reverse("telegram_webhook"),
            data="{}",
            content_type="application/json",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )

        self.assertEqual(response.status_code, 403)

    @patch("core.content_services.fetch_url_metadata")
    def test_authenticated_user_can_create_content_item_from_url_metadata(self, metadata_mock):
        metadata_mock.return_value.data = {
            "title": "Titol enriquit",
            "description": "Descripcio enriquida.",
            "image_url": "https://example.com/image.jpg",
            "source_platform": "Example",
            "content_type": ContentItem.ContentType.ARTICLE,
            "tags": ["cultura", "recomanat"],
        }
        metadata_mock.return_value.error = ""
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("contentitem_create"),
            {
                "url": "https://example.com/article",
                "title": "",
                "description": "",
                "image_url": "",
                "source_platform": "",
                "content_type": ContentItem.ContentType.OTHER,
                "author": "",
                "language": "",
                "tag_list": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        item = ContentItem.objects.get(user=self.user, title="Titol enriquit")
        self.assertEqual(item.content_type, ContentItem.ContentType.ARTICLE)
        self.assertEqual(item.tags.count(), 2)

    @patch("core.content_services.fetch_url_metadata")
    def test_duplicate_url_in_same_channel_redirects_to_existing_item(self, metadata_mock):
        metadata_mock.return_value.data = {}
        metadata_mock.return_value.error = ""
        self.client.force_login(self.user)
        existing = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Existing",
            url="https://example.com/repeated",
        )

        response = self.client.post(
            reverse("contentitem_create"),
            {
                "url": "https://example.com/repeated",
                "title": "",
                "description": "",
                "image_url": "",
                "source_platform": "",
                "content_type": ContentItem.ContentType.OTHER,
                "author": "",
                "language": "",
                "tag_list": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, existing.get_absolute_url())
        self.assertEqual(ContentItem.objects.filter(channel=self.channel, url="https://example.com/repeated").count(), 1)
        metadata_mock.assert_not_called()

    def test_private_item_detail_is_not_public(self):
        item = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Privat",
            url="https://example.com/private",
        )

        response = self.client.get(reverse("contentitem_detail", kwargs={"pk": item.pk}))

        self.assertEqual(response.status_code, 404)

    def test_public_channel_loads_when_enabled(self):
        self.channel.is_public = True
        self.channel.save()
        ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Public",
            url="https://example.com/public",
            content_type=ContentItem.ContentType.VIDEO,
            source_platform="Example",
        )

        response = self.client.get(reverse("public_channel", kwargs={"username": self.user.username}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Canal de Jaume")
        self.assertContains(response, "Public")

    def test_dashboard_filters_by_content_type(self):
        self.client.force_login(self.user)
        ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Video",
            url="https://example.com/video",
            content_type=ContentItem.ContentType.VIDEO,
        )
        ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Article",
            url="https://example.com/article",
            content_type=ContentItem.ContentType.ARTICLE,
        )

        response = self.client.get(reverse("dashboard"), {"type": ContentItem.ContentType.VIDEO})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Video")
        self.assertContains(response, "poster-video")
        self.assertNotContains(response, "https://example.com/article")

    def test_dashboard_filters_by_tag(self):
        self.client.force_login(self.user)
        cinema = Tag.objects.create(name="Cinema", slug="cinema")
        music = Tag.objects.create(name="Musica", slug="musica")
        film = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Film",
            url="https://example.com/film",
        )
        song = ContentItem.objects.create(
            user=self.user,
            channel=self.channel,
            title="Song",
            url="https://example.com/song",
        )
        film.tags.add(cinema)
        song.tags.add(music)

        response = self.client.get(reverse("dashboard"), {"tag": "cinema"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film")
        self.assertNotContains(response, "https://example.com/song")

    def test_dashboard_filters_by_multiple_tags(self):
        self.client.force_login(self.user)
        cinema = Tag.objects.create(name="Cinema", slug="cinema")
        music = Tag.objects.create(name="Musica", slug="musica")
        food = Tag.objects.create(name="Cuina", slug="cuina")
        film = ContentItem.objects.create(user=self.user, channel=self.channel, title="Film", url="https://example.com/film")
        song = ContentItem.objects.create(user=self.user, channel=self.channel, title="Song", url="https://example.com/song")
        recipe = ContentItem.objects.create(user=self.user, channel=self.channel, title="Recipe", url="https://example.com/recipe")
        film.tags.add(cinema)
        song.tags.add(music)
        recipe.tags.add(food)

        response = self.client.get(reverse("dashboard"), {"tag": ["cinema", "musica"]})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film")
        self.assertContains(response, "Song")
        self.assertNotContains(response, "https://example.com/recipe")
        self.assertContains(response, "active-tag")

    def test_dashboard_tag_tools_include_sort_and_clear_all(self):
        self.client.force_login(self.user)
        cinema = Tag.objects.create(name="Cinema", slug="cinema")
        music = Tag.objects.create(name="Musica", slug="musica")
        item = ContentItem.objects.create(user=self.user, channel=self.channel, title="Film", url="https://example.com/film")
        item.tags.add(cinema, music)

        response = self.client.get(reverse("dashboard"), {"tag": ["cinema", "musica"], "tag_sort": "alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Desactiva totes")
        self.assertContains(response, "?tag_sort=alpha")
        self.assertContains(response, "A-Z")

    def test_vertical_embed_detects_platform_and_dimensions(self):
        vertical = ContentItem(
            user=self.user,
            channel=self.channel,
            title="TikTok",
            url="https://example.com",
            embed_url="https://www.tiktok.com/player/v1/7639623555843493142",
        )
        horizontal = ContentItem(
            user=self.user,
            channel=self.channel,
            title="Horizontal",
            url="https://example.com",
            embed_url="https://www.tiktok.com/player/v1/7639623555843493142",
            metadata_json={"video_width": "1920", "video_height": "1080"},
        )

        self.assertTrue(vertical.is_vertical_embed)
        self.assertFalse(horizontal.is_vertical_embed)
