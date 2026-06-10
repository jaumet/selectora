from django.db import migrations, models


def make_existing_channels_public(apps, schema_editor):
    Channel = apps.get_model("core", "Channel")
    Channel.objects.update(is_public=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_contentitem_image_file"),
    ]

    operations = [
        migrations.AlterField(
            model_name="channel",
            name="is_public",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(make_existing_channels_public, migrations.RunPython.noop),
    ]
