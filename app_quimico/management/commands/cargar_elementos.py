"""Loads the complete periodic table (IUPAC 2021) plus its per-element details.

Idempotent: runs update_or_create per element and per detail row, so it can be
executed on fresh databases and re-run on existing ones without duplicating
rows or losing changes made to other fields.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from app_quimico.data.detalles_elementos import DETALLES_ELEMENTOS
from app_quimico.data.elementos import ELEMENTOS_IUPAC_2021
from app_quimico.models import DetalleElemento, ElementoQuimico


def _a_decimal(valor):
    """Returns ``Decimal(valor)`` when present, or ``None`` when missing."""
    return Decimal(valor) if valor is not None else None


class Command(BaseCommand):
    help = (
        "Carga la tabla periódica completa (118 elementos, IUPAC 2021) "
        "y sus detalles (grupo, período, categoría y propiedades)."
    )

    def handle(self, *args, **options):
        creados, actualizados, detalles = 0, 0, 0
        for numero, simbolo, nombre, peso in ELEMENTOS_IUPAC_2021:
            elemento, created = ElementoQuimico.objects.update_or_create(
                simbolo_elemento=simbolo,
                defaults={
                    "nombre_elemento": nombre,
                    "numero_atomico_elemento": numero,
                    "peso_atomico_elemento": Decimal(peso),
                },
            )
            if created:
                creados += 1
            else:
                actualizados += 1

            (
                grupo,
                periodo,
                categoria,
                electronegatividad,
                afinidad_electronica,
                energia_de_ionizacion,
                radio_covalente,
                descripcion,
            ) = DETALLES_ELEMENTOS[simbolo]

            DetalleElemento.objects.update_or_create(
                id_elemento=elemento,
                defaults={
                    "grupo_elemento": grupo,
                    "periodo_elemento": periodo,
                    "categoria_elemento": categoria,
                    "electronegatividad": _a_decimal(electronegatividad),
                    "afinidad_electronica": _a_decimal(afinidad_electronica),
                    "energia_de_ionizacion": _a_decimal(energia_de_ionizacion),
                    "radio_covalente": _a_decimal(radio_covalente),
                    "descripcion_elemento": descripcion,
                },
            )
            detalles += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tabla periódica cargada: {creados} creados, {actualizados} actualizados, "
            f"{detalles} detalles (total {len(ELEMENTOS_IUPAC_2021)} elementos)."
        ))
