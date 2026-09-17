"""Create default groups (Quimicos / Colaboradores) so registration and the
role matrix work without manual admin setup.

Permissions are created here explicitly because auth's post_migrate signal has
not run yet while migrations execute on a fresh database."""

from django.db import migrations


def crear_permisos_de_app(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.contenttypes.management import create_contenttypes
    from django.contrib.auth.management import create_permissions

    app_config = global_apps.get_app_config("app_quimico")
    create_contenttypes(app_config)
    create_permissions(app_config)


GRUPO_PERMISOS = {
    "Quimicos": [],
    "Colaboradores": [
        ("add_industria", "industria"),
        ("change_industria", "industria"),
        ("add_aplicacion", "aplicacion"),
        ("change_aplicacion", "aplicacion"),
        ("add_elementoquimico", "elementoquimico"),
        ("change_elementoquimico", "elementoquimico"),
        ("add_detalleelemento", "detalleelemento"),
        ("change_detalleelemento", "detalleelemento"),
    ],
}


def crear_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    crear_permisos_de_app(apps, schema_editor)

    for nombre_grupo, codenames in GRUPO_PERMISOS.items():
        grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
        for codename, model in codenames:
            try:
                permiso = Permission.objects.get(
                    codename=codename, content_type__app_label="app_quimico",
                    content_type__model=model,
                )
            except Permission.DoesNotExist:
                raise RuntimeError(
                    f"Permiso {codename} ({model}) no encontrado tras crear los "
                    "content types de app_quimico."
                )
            grupo.permissions.add(permiso)


def borrar_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GRUPO_PERMISOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app_quimico", "0002_alter_compuestoquimico_formula_compuesto_and_more"),
        # The legacy ContentType.name column must already be removed
        # (contenttypes 0002) before creating content types explicitly.
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(crear_grupos, borrar_grupos),
    ]
