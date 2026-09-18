"""Loads the complete periodic table (IUPAC 2021) into ElementoQuimico.

Idempotent: runs update_or_create per element, so it can be executed on
fresh databases and re-run on existing ones without duplicating rows or
losing changes made to other fields.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from app_quimico.data.elementos import ELEMENTOS_IUPAC_2021
from app_quimico.models import ElementoQuimico


class Command(BaseCommand):
    help = "Carga la tabla periódica completa (118 elementos, IUPAC 2021)."

    def handle(self, *args, **options):
        creados, actualizados = 0, 0
        for numero, simbolo, nombre, peso in ELEMENTOS_IUPAC_2021:
            _, created = ElementoQuimico.objects.update_or_create(
                simbolo_elemento=simbolo,
                defaults={
                    "nombre_elemento": nombre,
                    "numero_atomico_elemento": numero,
                    "peso_atomico_elemento": Decimal(peso),
                },
            )
            if _:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tabla periódica cargada: {creados} creados, {actualizados} actualizados "
            f"(total {len(ELEMENTOS_IUPAC_2021)})."
        ))
