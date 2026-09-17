"""Signals keeping the process-wide atomic weight cache consistent."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app_quimico.models import ElementoQuimico
from app_quimico.utils import invalidar_cache_pesos


@receiver(post_save, sender=ElementoQuimico)
@receiver(post_delete, sender=ElementoQuimico)
def invalidate_weight_cache(sender, **kwargs):
    invalidar_cache_pesos()
