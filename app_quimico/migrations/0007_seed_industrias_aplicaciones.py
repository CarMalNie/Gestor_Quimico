"""Seeds the cátedra base rows: 5 industrias and its 10 aplicaciones.

Idempotent via get_or_create, so re-applying the migration never duplicates
rows. Compounds are intentionally NOT seeded here; the operator creates them
manually through the web application.

Reverse deletes only the rows this migration created, matched by name.
"""

from django.db import migrations

INDUSTRIAS = [
    "Farmacéutica",
    "Alimenticia",
    "Tratamiento de Aguas",
    "Petroquímica",
    "Metalurgia",
]

# (nombre_uso, nombre_industria)
APLICACIONES = [
    ("Esterilización de Equipos", "Farmacéutica"),
    ("Solución Salina", "Farmacéutica"),
    ("Desinfección de Superficies", "Alimenticia"),
    ("Estabilización de pH", "Alimenticia"),
    ("Neutralización de Residuos", "Tratamiento de Aguas"),
    ("Adición de Cloro", "Tratamiento de Aguas"),
    ("Lubricante de Motor", "Petroquímica"),
    ("Control de Corrosión", "Petroquímica"),
    ("Baño de Galvanizado", "Metalurgia"),
    ("Limpieza Ácida de Metales", "Metalurgia"),
]


def crear_industrias_y_aplicaciones(apps, schema_editor):
    Industria = apps.get_model("app_quimico", "Industria")
    Aplicacion = apps.get_model("app_quimico", "Aplicacion")

    industrias = {}
    for nombre in INDUSTRIAS:
        industria, _ = Industria.objects.get_or_create(nombre_industria=nombre)
        industrias[nombre] = industria

    for nombre_uso, nombre_industria in APLICACIONES:
        Aplicacion.objects.get_or_create(
            nombre_uso=nombre_uso,
            defaults={"id_industria": industrias[nombre_industria]},
        )


def eliminar_industrias_y_aplicaciones(apps, schema_editor):
    Industria = apps.get_model("app_quimico", "Industria")
    Aplicacion = apps.get_model("app_quimico", "Aplicacion")

    for nombre_uso, _ in APLICACIONES:
        Aplicacion.objects.filter(nombre_uso=nombre_uso).delete()

    for nombre in INDUSTRIAS:
        Industria.objects.filter(nombre_industria=nombre).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app_quimico", "0006_alter_detalleelemento_afinidad_electronica_and_more"),
    ]

    operations = [
        migrations.RunPython(
            crear_industrias_y_aplicaciones,
            eliminar_industrias_y_aplicaciones,
        ),
    ]
