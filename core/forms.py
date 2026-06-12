from django import forms
from django.utils.text import slugify
import secrets

from .models import Channel, ContentItem, Tag


class MagicLoginRequestForm(forms.Form):
    email = forms.EmailField(label="Email")
    captcha_answer = forms.IntegerField(label="Verificacio", min_value=0)
    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "class": "captcha-honeypot",
                "tabindex": "-1",
            }
        ),
    )

    session_key = "magic_login_captcha"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        challenge = self._challenge()
        if challenge:
            self.fields["captcha_answer"].label = f"Quant fan {challenge['a']} + {challenge['b']}?"

    def _challenge(self):
        if not self.request:
            return None
        challenge = self.request.session.get(self.session_key)
        if not challenge:
            random = secrets.SystemRandom()
            challenge = {
                "a": random.randint(2, 9),
                "b": random.randint(2, 9),
            }
            challenge["answer"] = challenge["a"] + challenge["b"]
            self.request.session[self.session_key] = challenge
            self.request.session.modified = True
        return challenge

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("No s'ha pogut validar el formulari.")
        return value

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get("captcha_answer")
        challenge = self._challenge()
        if not challenge or answer != challenge["answer"]:
            raise forms.ValidationError("Resposta de verificacio incorrecta.")
        return answer


class ChannelForm(forms.ModelForm):
    top_item_ids = forms.Field(required=False, widget=forms.MultipleHiddenInput)

    class Meta:
        model = Channel
        fields = ["name", "description", "cover_image", "cover_image_url"]
        labels = {
            "name": "Nom del canal",
            "description": "Descripcio",
            "cover_image": "Imatge de portada",
            "cover_image_url": "URL externa de portada",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "cover_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["top_item_ids"].initial = [
                str(top_item.item_id) for top_item in self.instance.top_items.order_by("position")
            ]

    def clean_top_item_ids(self):
        values = self.cleaned_data.get("top_item_ids", [])
        ids = []
        for value in values:
            if not str(value).isdigit():
                raise forms.ValidationError("La llista Top 10 conte un item invalid.")
            item_id = int(value)
            if item_id not in ids:
                ids.append(item_id)

        if len(ids) > 10:
            raise forms.ValidationError("El Top 10 del canal no pot tenir mes de 10 items.")
        if ids and self.instance and self.instance.pk:
            existing_count = ContentItem.objects.filter(channel=self.instance, pk__in=ids).count()
            if existing_count != len(ids):
                raise forms.ValidationError("El Top 10 nomes pot contenir items del teu canal.")
        return ids

    def clean_cover_image(self):
        image = self.cleaned_data.get("cover_image")
        if not image:
            return image
        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("El fitxer de portada ha de ser una imatge.")
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imatge de portada no pot superar els 5 MB.")
        return image

    def clean_cover_image_url(self):
        url = self.cleaned_data.get("cover_image_url", "").strip()
        if not url:
            return url
        if self.instance and self.instance.pk and url == (self.instance.cover_image_url or ""):
            return url
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")
        if not url.lower().split("?", 1)[0].endswith(image_extensions):
            raise forms.ValidationError("La URL externa de portada ha d'apuntar directament a una imatge.")
        return url


class ContentItemForm(forms.ModelForm):
    priority = forms.ChoiceField(
        label="Prioritat",
        required=False,
        choices=[
            ("", "Normal"),
            (ContentItem.Priority.LOW, "Baixa"),
            (ContentItem.Priority.NORMAL, "Normal"),
            (ContentItem.Priority.HIGH, "Alta"),
        ],
    )
    expiry_amount = forms.TypedChoiceField(
        label="Número",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "No")] + [(str(i), str(i)) for i in range(1, 61)],
    )
    expiry_unit = forms.ChoiceField(
        label="Unitat",
        required=False,
        choices=[
            ("", "No"),
            (ContentItem.ExpiryUnit.YEARS, "Anys"),
            (ContentItem.ExpiryUnit.MONTHS, "Mesos"),
            (ContentItem.ExpiryUnit.WEEKS, "Setmanes"),
            (ContentItem.ExpiryUnit.DAYS, "Dies"),
            (ContentItem.ExpiryUnit.HOURS, "Hores"),
            (ContentItem.ExpiryUnit.MINUTES, "Minuts"),
        ],
    )
    personal_comment = forms.CharField(
        label="Comentari personal",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Només tu el veus.",
    )
    internal_context = forms.CharField(
        label="Context intern",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Per recordar per què l'has guardat o com vols usar-lo.",
    )
    tag_list = forms.CharField(
        label="Etiquetes",
        required=False,
        help_text="Separades per comes.",
    )

    class Meta:
        model = ContentItem
        fields = [
            "url",
            "title",
            "description",
            "image_url",
            "source_platform",
            "content_type",
            "visibility",
            "author",
            "language",
            "personal_comment",
            "priority",
            "internal_context",
            "expiry_amount",
            "expiry_unit",
            "tag_list",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["url"].help_text = "Enganxa una URL. Selectora intentara completar la resta."
        self.fields["title"].required = False
        self.fields["description"].required = False
        self.fields["image_url"].required = False
        self.fields["source_platform"].required = False
        self.fields["visibility"].required = False
        self.fields["visibility"].label = "Visibilitat"
        self.fields["visibility"].choices = [
            (ContentItem.Visibility.PUBLIC, "Públic"),
            (ContentItem.Visibility.PRIVATE, "Privat"),
        ]
        self.fields["visibility"].initial = ContentItem.Visibility.PUBLIC
        self.fields["author"].required = False
        self.fields["language"].required = False
        self.fields["priority"].required = False
        self.fields["priority"].initial = ContentItem.Priority.NORMAL
        self.fields["expiry_amount"].required = False
        self.fields["expiry_unit"].required = False
        self.fields["personal_comment"].required = False
        self.fields["internal_context"].required = False
        if self.instance and self.instance.pk:
            self.fields["tag_list"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))
            self.fields["priority"].initial = self.instance.priority

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("expiry_amount")
        unit = cleaned_data.get("expiry_unit")
        if bool(amount) != bool(unit):
            raise forms.ValidationError("La caducitat necessita número i unitat, o bé deixa-la buida.")
        return cleaned_data

    def save_tags(self, item):
        names = [name.strip() for name in self.cleaned_data.get("tag_list", "").split(",") if name.strip()]
        tags = []
        for name in names:
            slug = slugify(name)[:90]
            if not slug:
                continue
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags.append(tag)
        item.tags.set(tags)
