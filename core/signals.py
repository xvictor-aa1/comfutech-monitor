# core/signals.py
"""
Signals para invalidar el caché de `runtime_config` al guardar
configuraciones.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SystemConfig, EmailConfig
from . import runtime_config


@receiver(post_save, sender=SystemConfig)
def system_config_changed(sender, instance, **kwargs):
    """Al guardar SystemConfig, se limpia el caché."""
    runtime_config.reset_cache()


@receiver(post_save, sender=EmailConfig)
def email_config_changed(sender, instance, **kwargs):
    """Al guardar EmailConfig, se limpia el caché y se reaplica al settings."""
    runtime_config.reset_cache()
    runtime_config.apply_email_config_to_settings()
#    try:
#        runtime_config.apply_email_config_to_settings()
#    except Exception:
#        pass