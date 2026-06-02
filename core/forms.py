from django import forms
from django.utils.text import slugify

from .models import Channel, ContentItem, Tag


class MagicLoginRequestForm(forms.Form):
    email = forms.EmailField(label="Email")


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "description", "cover_image", "cover_image_url", "is_public"]
        labels = {
            "name": "Nom del canal",
            "description": "Descripcio",
            "cover_image": "Imatge de portada",
            "cover_image_url": "URL externa de portada",
            "is_public": "Fer public aquest canal",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "cover_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

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
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")
        if not url.lower().split("?", 1)[0].endswith(image_extensions):
            raise forms.ValidationError("La URL externa de portada ha d'apuntar directament a una imatge.")
        return url


class ContentItemForm(forms.ModelForm):
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
            "author",
            "language",
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
        self.fields["author"].required = False
        self.fields["language"].required = False
        if self.instance and self.instance.pk:
            self.fields["tag_list"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))

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
