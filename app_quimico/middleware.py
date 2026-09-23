"""Middleware de política Force-MFA para el grupo ``Administradores``.

Política sellada con el operador: la verificación en dos pasos (TOTP) es
**obligatoria** para el grupo ``Administradores``. Sin un ``TOTPDevice``
confirmado, una sesión autenticada de ese grupo no puede navegar por el sitio:
cualquier ruta (incluido ``/admin/``) redirige a ``mfa_setup`` con un aviso en
español. Sin este middleware, el administrador podía escapar de la política con
cualquier enlace ("Volver a mi perfil") después del login.

Decisiones de frontera:

* La política es por **grupo**, no por ``is_staff``/``is_superuser``: un
  superusuario que no pertenece a ``Administradores`` navega con total libertad.
* Rutas exentas exactas: ``mfa_setup`` y ``logout``, más ``STATIC_URL`` y
  ``MEDIA_URL``. ``mfa_verify`` **no** se exime: sin dispositivo confirmado no
  tiene nada que verificar y su vista terminaría en error. El flujo de
  recuperación/cambio de contraseña tampoco se exime (el usuario conserva el
  logout para salir).
* Una sesión ya verificada (``request.user.is_verified()``) navega libre: por
  ejemplo un administrador que ingresó con un código de respaldo ``otp_static``
  no queda atrapado.
* La exención por nombre de ruta resuelto evita el bucle de redirección cuando
  la propia vista destino es ``mfa_setup``.

Ubicación en ``MIDDLEWARE``: debe ejecutarse **después** de
``django_otp.middleware.OTPMiddleware`` (necesita ``request.user.is_verified()``)
y **después** de ``django.contrib.messages.middleware.MessageMiddleware``
(usa ``messages.warning``; en Django 5 ese middleware es el único que inicializa
``request._messages``). Por eso queda al final de la lista, que satisface ambas
precondiciones y además deja que los middlewares externos procesen la respuesta
de redirección.
"""

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from django_otp.plugins.otp_totp.models import TOTPDevice

ADMIN_GROUP_NAME = "Administradores"
EXEMPT_URL_NAMES = frozenset({"mfa_setup", "logout"})
FORCE_MFA_WARNING = (
    "Tu perfil de Administrador requiere configurar la verificación en dos "
    "pasos antes de continuar."
)


def _asset_prefixes():
    """Prefijos normalizados de los assets exentos, sin barras laterales.

    ``STATIC_URL`` puede venir sin barra inicial (``'static/'``) mientras que
    ``request.path_info`` siempre empieza con ``'/'``; se comparan ambos sin la
    barra para no depender del formato configurado. Un prefijo vacío (el valor
    por defecto de ``MEDIA_URL`` es ``'/'``, que significa "sin media
    configurada") se descarta: ``str.startswith('')`` siempre da ``True`` y
    eximiría todo el sitio.
    """
    prefixes = []
    for value in (
        getattr(settings, "STATIC_URL", ""),
        getattr(settings, "MEDIA_URL", ""),
    ):
        prefix = (value or "").strip("/")
        if prefix:
            prefixes.append(prefix)
    return tuple(prefixes)


class ForceMFAAdminMiddleware:
    """Fuerza el enrolamiento MFA de ``Administradores`` durante toda la sesión."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_blocked(request):
            messages.warning(request, FORCE_MFA_WARNING)
            return redirect("mfa_setup")
        return self.get_response(request)

    def _is_blocked(self, request):
        """``True`` solo para un administrador sin MFA fuera de las rutas exentas."""
        user = getattr(request, "user", None)
        # (a) Anónimo: login y vistas públicas nunca pasan por la política.
        if user is None or not user.is_authenticated:
            return False

        # (b) Las rutas sin nombre (por ejemplo los assets que sirve el helper
        # `static()` en DEBUG) no participan de la política.
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return False

        # (c) 'mfa_setup' y 'logout' son las únicas rutas con nombre exentas.
        if match.url_name in EXEMPT_URL_NAMES:
            return False

        # (d) Assets estáticos y de media: siempre accesibles.
        asset_prefixes = _asset_prefixes()
        if asset_prefixes and request.path_info.lstrip("/").startswith(asset_prefixes):
            return False

        # (e) La política es exclusiva del grupo Administradores.
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return False

        # (f) Un TOTP confirmado habilita la navegación (el segundo factor de la
        # sesión lo exige el flujo de login, no esta política).
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            return False

        # (g) Sesión ya verificada (por ejemplo con códigos de respaldo).
        return not user.is_verified()
