"""Seed the Administradores group so fresh environments match production.

Production created it manually (navbar badge fix for the superuser); without
this seed a fresh local/dev database lacked the group and the navbar badge
rendered empty for admins until someone recreated it by hand."""

from django.db import migrations


def seed_administradores(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Administradores")


def borrar_grupo(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Administradores").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app_quimico", "0008_seed_industrias_aplicaciones_expansion"),
    ]

    operations = [
        migrations.RunPython(seed_administradores, borrar_grupo),
    ]
