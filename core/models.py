# core/models.py
"""
Modelos de la app `core`.

Incluye:
  - SystemConfig: configuración global (Grafana, InfluxDB, Telegram, Monitor).
  - EmailConfig: configuración SMTP.
  - EmailVerification: estado de verificación del email por usuario.
  - PasswordResetCode: código temporal de recuperación de contraseña.
  - PasswordResetAttempt: registro de intentos de recuperación.
"""
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SystemConfig(models.Model):
    """Configuración global del sistema (singleton, id=1)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)

    # --- TELEGRAM ---
    telegram_bot_token = models.CharField(max_length=255, blank=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True)
    telegram_enabled = models.BooleanField(default=False)

    # --- INFLUXDB ---
    influx_url = models.CharField(
        max_length=255, blank=True, default="http://localhost:8086",
        verbose_name="InfluxDB URL",
    )
    influx_token = models.CharField(
        max_length=500, blank=True, verbose_name="InfluxDB API Token",
    )
    influx_org = models.CharField(
        max_length=100, blank=True, default="comfutech",
        verbose_name="Organización",
    )
    influx_bucket = models.CharField(
        max_length=100, blank=True, default="metricas_red",
        verbose_name="Bucket",
    )

    # --- GRAFANA ---
    grafana_url = models.CharField(
        max_length=500, blank=True, default="http://localhost:3000",
        verbose_name="Grafana URL",
    )

    # --- MONITOR ---
    monitor_enabled = models.BooleanField(default=True)
    snmp_poll_interval = models.PositiveIntegerField(default=60)
    health_poll_interval = models.PositiveIntegerField(default=120)
    icmp_poll_interval = models.PositiveIntegerField(default=120)

    # --- AUDITORÍA ---
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="config_updates",
    )

    class Meta:
        db_table = "system_config"
        verbose_name = "Configuración del sistema"
        verbose_name_plural = "Configuración del sistema"

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return f"Config (Telegram: {'ON' if self.telegram_enabled else 'OFF'})"


class EmailConfig(models.Model):
    """Configuración del servidor de correo (singleton)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)

    email_host = models.CharField(
        max_length=255, blank=True, default="smtp.gmail.com",
        verbose_name="Servidor SMTP",
    )
    email_port = models.PositiveIntegerField(default=587, verbose_name="Puerto")
    email_use_tls = models.BooleanField(default=True, verbose_name="Usar TLS")
    email_use_ssl = models.BooleanField(default=False, verbose_name="Usar SSL")
    email_host_user = models.CharField(
        max_length=255, blank=True, verbose_name="Usuario SMTP",
    )
    email_host_password = models.CharField(
        max_length=500, blank=True, verbose_name="Contraseña SMTP",
    )
    default_from_email = models.CharField(
        max_length=255, blank=True,
        default="Comfutech Monitor <noreply@comfutech.local>",
        verbose_name="Remitente por defecto",
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="email_config_updates",
    )

    class Meta:
        db_table = "email_config"
        verbose_name = "Configuración de Email"
        verbose_name_plural = "Configuración de Email"

    def save(self, *args, **kwargs):
        self.id = 1
        # TLS y SSL son mutuamente excluyentes
        if self.email_use_ssl:
            self.email_use_tls = False
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return f"EmailConfig ({self.email_host}:{self.email_port})"


class EmailVerification(models.Model):
    """
    Estado de verificación del email de un usuario.

    Cada usuario tiene a lo sumo un registro. El campo `verified_email`
    guarda el correo que fue verificado para poder invalidar la
    verificación cuando el email cambia.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name="email_verification",
    )
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_email = models.EmailField(blank=True)

    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    token_created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_verifications"
        verbose_name = "Verificación de email"
        verbose_name_plural = "Verificaciones de email"

    def __str__(self):
        state = "verificado" if self.verified else "pendiente"
        return f"{self.user.username} ({self.user.email}) — {state}"

    @classmethod
    def get_or_create_for(cls, user):
        """Devuelve o crea el registro de verificación para un usuario."""
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    @classmethod
    def is_email_verified(cls, user) -> bool:
        """
        True si el usuario tiene el email verificado Y coincide
        con el email actual del User.
        """
        if not user or not user.email:
            return False
        try:
            v = cls.objects.get(user=user)
        except cls.DoesNotExist:
            return False
        return (
            v.verified
            and v.verified_email
            and v.verified_email.lower() == user.email.lower()
        )

    def regenerate_token(self):
        """Genera un token nuevo e invalida la verificación actual."""
        self.token = uuid.uuid4()
        self.verified = False
        self.verified_at = None
        self.verified_email = ""
        self.save()
        return self.token

    def mark_verified(self, email: str):
        """Marca el email como verificado."""
        self.verified = True
        self.verified_at = timezone.now()
        self.verified_email = email
        self.save()

    def reset_verification(self):
        """Invalida la verificación (ej: al cambiar el email)."""
        self.verified = False
        self.verified_at = None
        self.verified_email = ""
        self.token = uuid.uuid4()
        self.save()

    def is_token_valid(self, max_age_hours: int = 48) -> bool:
        """Comprueba si el token sigue vigente."""
        if not self.token_created_at:
            return False
        age = (timezone.now() - self.token_created_at).total_seconds()
        return age < (max_age_hours * 3600)


class PasswordResetCode(models.Model):
    """Código temporal de 8 dígitos para recuperación de contraseña."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reset_codes",
    )
    code = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "used"]),
        ]

    @classmethod
    def generate_for(cls, user, minutes: int = 5):
        """Genera un código nuevo válido por N minutos."""
        cls.objects.filter(user=user, used=False).update(used=True)
        code = "".join(str(secrets.randbelow(10)) for _ in range(8))
        expires = timezone.now() + timedelta(minutes=minutes)
        return cls.objects.create(user=user, code=code, expires_at=expires)

    def is_valid(self) -> bool:
        return (not self.used) and timezone.now() < self.expires_at

    def seconds_remaining(self) -> int:
        if self.used:
            return 0
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))

    def __str__(self):
        return f"{self.user.username} - {self.code}"


class PasswordResetAttempt(models.Model):
    """Registra intentos de recuperación para anti-fuerza-bruta."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reset_attempts",
    )
    ip = models.CharField(max_length=45, blank=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_attempts"
        ordering = ["-created_at"]

    @classmethod
    def recent_failed_count(cls, user, minutes: int = 15) -> int:
        """Cuenta los intentos fallidos recientes de un usuario."""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            user=user, successful=False, created_at__gte=cutoff
        ).count()

    @classmethod
    def log(cls, user, ip: str, success: bool):
        """Registra un intento de recuperación."""
        return cls.objects.create(user=user, ip=ip or "", successful=success)