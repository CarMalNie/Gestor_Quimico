"""Seeds the operator-approved industrial catalog expansion.

Adds 8 new industrias and their 26 aplicaciones on top of the cátedra base
rows seeded by 0007_seed_industrias_aplicaciones. Idempotent via
get_or_create, so re-applying the migration never duplicates rows.
Compounds are intentionally NOT seeded here; the operator creates them
manually through the web application.

Reverse deletes only the rows this migration created, matched by name.
"""

from django.db import migrations

INDUSTRIAS = [
    "Agroquímica",
    "Cosmética e Higiene",
    "Construcción",
    "Automotriz",
    "Textil",
    "Pinturas y Recubrimientos",
    "Cuidado del Hogar",
    "Laboratorio y Docencia",
]

# (nombre_uso, nombre_industria)
APLICACIONES = [
    ("Fertilización Nitrogenada", "Agroquímica"),
    ("Control de Malezas", "Agroquímica"),
    ("Ajuste de pH de Suelos", "Agroquímica"),
    ("Fungicida Foliar", "Agroquímica"),
    ("Ajuste de pH de Cosméticos", "Cosmética e Higiene"),
    ("Conservación de Formulaciones", "Cosmética e Higiene"),
    ("Antitranspirantes", "Cosmética e Higiene"),
    ("Exfoliación Química", "Cosmética e Higiene"),
    ("Acelerante de Hormigón", "Construcción"),
    ("Limpieza de Superficies de Obra", "Construcción"),
    ("Fabricación de Vidrio", "Construcción"),
    ("Electrolito de Baterías", "Automotriz"),
    ("Refrigeración de Motores", "Automotriz"),
    ("Limpiador de Frenos", "Automotriz"),
    ("Blanqueo de Fibras", "Textil"),
    ("Fijación de Tintes", "Textil"),
    ("Neutralización de Baños de Tintura", "Textil"),
    ("Pigmentación Blanca", "Pinturas y Recubrimientos"),
    ("Disolución de Resinas", "Pinturas y Recubrimientos"),
    ("Desengrasado Metálico", "Pinturas y Recubrimientos"),
    ("Desinfección Doméstica", "Cuidado del Hogar"),
    ("Removedor de Sarro", "Cuidado del Hogar"),
    ("Limpieza Multiusos", "Cuidado del Hogar"),
    ("Preparación de Reactivos", "Laboratorio y Docencia"),
    ("Estandarización de Soluciones", "Laboratorio y Docencia"),
    ("Indicadores de pH", "Laboratorio y Docencia"),
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
        ("app_quimico", "0007_seed_industrias_aplicaciones"),
    ]

    operations = [
        migrations.RunPython(
            crear_industrias_y_aplicaciones,
            eliminar_industrias_y_aplicaciones,
        ),
    ]
