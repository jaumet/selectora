import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .models import MagicLoginToken


TOKEN_BYTES = 32
TOKEN_TTL_MINUTES = 30


def normalize_email(email):
    return email.strip().lower()


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def username_from_email(email):
    User = get_user_model()
    base = slugify(email.split("@", 1)[0]) or "usuari"
    username = base[:140]
    counter = 1
    while User.objects.filter(username=username).exists():
        suffix = f"-{counter}"
        username = f"{base[: 150 - len(suffix)]}{suffix}"
        counter += 1
    return username


def get_or_create_user_for_email(email):
    User = get_user_model()
    normalized = normalize_email(email)
    user = User.objects.filter(email__iexact=normalized).first()
    if user:
        return user, False
    return User.objects.create_user(
        username=username_from_email(normalized),
        email=normalized,
        password=None,
    ), True


def create_magic_login(email):
    user, created = get_or_create_user_for_email(email)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    MagicLoginToken.objects.create(
        email=normalize_email(email),
        user=user,
        token_hash=token_hash(token),
        expires_at=timezone.now() + timedelta(minutes=TOKEN_TTL_MINUTES),
    )
    return user, token, created


def send_magic_login_email(request, email):
    user, token, created = create_magic_login(email)
    magic_url = request.build_absolute_uri(reverse("magic_login_confirm", kwargs={"token": token}))
    context = {
        "magic_url": magic_url,
        "user": user,
        "created": created,
        "ttl_minutes": TOKEN_TTL_MINUTES,
    }
    subject = "Enllaç d'entrada a Selectora"
    text_body = render_to_string("registration/magic_login_email.txt", context)
    send_mail(
        subject,
        text_body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "selectora@localhost"),
        [normalize_email(email)],
        fail_silently=False,
    )
    return magic_url


def consume_magic_token(token):
    hashed = token_hash(token)
    login_token = MagicLoginToken.objects.select_related("user").filter(token_hash=hashed).first()
    if not login_token or not login_token.is_valid:
        return None
    login_token.used_at = timezone.now()
    login_token.save(update_fields=["used_at"])
    return login_token.user
