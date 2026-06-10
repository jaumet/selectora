from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0011_channel_public_by_default"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentItemRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "main_value",
                    models.CharField(
                        choices=[
                            ("passo", "Passo"),
                            ("curios", "Curiós"),
                            ("val_la_pena", "Val la pena"),
                            ("recomanaria", "Recomanaria"),
                            ("must", "Must"),
                        ],
                        max_length=24,
                    ),
                ),
                ("nuance_values", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ratings",
                        to="core.contentitem",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_item_ratings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentitemrating",
            constraint=models.UniqueConstraint(fields=("user", "item"), name="unique_content_item_rating"),
        ),
    ]
