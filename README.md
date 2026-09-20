# ⚗️ Gestor Químico

[![CI](https://github.com/CarMalNie/Gestor_Quimico/actions/workflows/ci.yml/badge.svg)](https://github.com/CarMalNie/Gestor_Quimico/actions/workflows/ci.yml)

Sistema web de gestión de información química construido con **Django 5.2** (patrón MVT) y **MySQL**.
Centraliza la tabla periódica, el cálculo automático de pesos moleculares y la asociación de
compuestos con sus usos industriales, con control de propiedad por usuario y roles de curación.

## Qué resuelve

- **Catálogo maestro de elementos químicos**: 118 elementos con propiedades científicas validadas
  (número atómico, peso atómico, electronegatividad, afinidad electrónica, energía de ionización,
  radio covalente) con validadores de rango a nivel de modelo.
- **Motor de cálculo de peso molecular**: parser propio de fórmulas IUPAC (algoritmo de pila con
  multiplicadores de grupo) que calcula el PM y descompone la composición atómica de cada compuesto.
- **Compuestos por usuario**: cada usuario gestiona su catálogo privado de compuestos, con su
  aplicación industrial, concentración mínima y composición elemental derivada de la fórmula.
- **Roles separados por propósito**: usuarios de producto (químicos), curadores de datos maestros
  y gobernanza de plataforma (ver matriz de roles).
- **Ciclo de credenciales completo**: registro, login protegido con rate limiting,
  recuperación de contraseña por email real, cambio de contraseña para el usuario
  autenticado y MFA TOTP opcional (Google Authenticator compatible).

## Arquitectura

| Capa | Implementación |
| :--- | :--- |
| Modelos (8 tablas) | `Industria`, `ElementoQuimico` + `DetalleElemento` (1:1), `CompuestoQuimico`, `Aplicacion`, `ElementoCompuesto` (M:N), `CompuestoAplicacion` (M:N), `ElementoAplicacion` (M:N) |
| Vistas | Class-Based Views (CRUD completo), transacciones atómicas, `select_related`/`prefetch_related` |
| Motor de cálculo | `app_quimico.utils.CalculadoraPM`: validación IUPAC estricta, tokenización posicional, balanceo de agrupadores, cache de pesos por proceso |
| Formularios | `django-crispy-forms` (Bootstrap 5), validación cruzada industria↔aplicación, cascada cliente |
| Frontend | Templates DTL, Bootstrap 5.3 local-friendly, CSS de diseño propio, tema claro/oscuro persistente |
| Base de datos | MySQL (modo `STRICT_TRANS_TABLES`) |
| Envío de email | Transporte dual por entorno: SMTP (Brevo) en desarrollo, API HTTP de Brevo en PythonAnywhere (selección automática por variables de entorno) |
| Tests | pytest + pytest-django: 125 ejecuciones (108 tests, algunos parametrizados) — permisos/ownership, parser (sin BD), formularios, flujos de autenticación, MFA y backend de email |

### Matriz de roles

| Acción | Químico | Colaborador | Administrador |
| :--- | :---: | :---: | :---: |
| Crear/editar/eliminar sus compuestos | ✅ | — | — |
| Ver compuestos ajenos desde la web | ❌ | ❌ | ❌ |
| CRUD de datos maestros (elementos, industrias, aplicaciones) | Solo lectura | ✅ | ✅ |
| Moderación y gestión de usuarios | — | — | Vía `/admin` |

Los compuestos son privados de su dueño en toda la aplicación web; la moderación y auditoría se
realizan a través del panel de administración de Django.

### Reglas del motor de cálculo (nomenclatura IUPAC)

- Los símbolos de dos letras se escriben con la primera en mayúscula y la segunda en minúscula.
- `Cu` → cobre (1 elemento); `CU` → carbono + uranio (lectura literal, 2 elementos).
- `cU`, `cu`, `Uc` y cualquier carácter fuera de la gramática IUPAC generan error de validación.
- Los hidratos (`CuSO4·5H2O`) se rechazan explícitamente con mensaje informativo (soporte planificado).
- El PM se recalcula automáticamente al crear o modificar la fórmula; la composición elemental se
  deriva de la fórmula y queda registrada como relación M:N auditable.

## Autenticación y recuperación

- **Registro y login**: registro con asignación automática al grupo `Químicos`; login con bloqueo
  por intentos fallidos (django-axes).
- **Recuperación de contraseña por email**: flujo nativo de Django (`/accounts/password_reset/`)
  con plantillas propias, respuesta idéntica para emails existentes o desconocidos (sin
  enumeración de usuarios), token de un solo uso y expiración configurable.
- **Cambio de contraseña autenticado**: `/accounts/password-change/` (vistas nativas) con
  verificación de la contraseña anterior, validadores estándar y rotación del hash de sesión
  (la sesión del usuario sobrevive al cambio).
- **MFA TOTP opcional**: enrolamiento con QR (cualquier app TOTP: Google/Microsoft Authenticator,
  Authy, Bitwarden…) vía `django-otp`; segundo paso en el login para usuarios con dispositivo
  confirmado; verificación con throttling integrado; gestión de dispositivos vía `/admin`.
- **Recuperación con autenticador perdido**: códigos de respaldo de un solo uso (`otp_static`)
  autogestionados desde `/accounts/mfa/backup-codes/`: se generan 10 códigos tras confirmar el
  TOTP (se muestran una única vez) y se usan en el segundo paso del login (`?backup=1`).
  Regenerarlos invalida el set anterior. Alternativa administrativa — el staff elimina el
  dispositivo TOTP del usuario desde el admin (sección *OTP TOTP*) y el usuario re-enrola. El
  reset de contraseña **no** saltea el segundo factor.
- **Códigos de respaldo MFA**: implementados con `django_otp.plugins.otp_static`; son un respaldo
  del segundo factor (requieren TOTP confirmado), no un factor independiente.

## Configuración

### Prerrequisitos

- Python 3.10+
- MySQL 8 en ejecución, con una base de datos creada para el proyecto

### Instalación

```bash
git clone https://github.com/CarMalNie/Gestor_Quimico gestor_quimico
cd gestor_quimico
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env   # y completar SECRET_KEY y credenciales de la BD
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La aplicación queda en `http://127.0.0.1:8000/`.

### Envío de email (recuperación de contraseña)

El transporte se selecciona automáticamente por variables de entorno (ver `.env.example`):

| Entorno | Variable clave | Transporte |
| :--- | :--- | :--- |
| Desarrollo local | `EMAIL_HOST` | SMTP (p. ej. Brevo ~300/día, Gmail app password ~500/día) |
| Producción en PythonAnywhere (free) | `EMAIL_API_KEY` | API HTTP de Brevo (`api.brevo.com`, en la whitelist de PA) |
| Sin configurar | — | Consola (el email se imprime en terminal) |

Ambos transportes usan el mismo flujo de Django (`send_mail`); el backend de API es
implementación propia (`app_quimico/brevo_api_backend.py`). Las claves SMTP y API de Brevo
son credenciales independientes y no se versionan.

### Despliegue (PythonAnywhere)

1. `git pull` en la consola del proyecto
2. Instalar dependencias con el pip del virtualenv de la web app
3. `python manage.py migrate`
4. `.env` con credenciales de BD, `EMAIL_*` de Brevo y `EMAIL_API_KEY` (el plan gratuito de
   PA bloquea SMTP saliente desde web apps; `api.brevo.com` está en su lista blanca)
5. Reload de la web app desde el dashboard

### Grupos y permisos (primer arranque)

El registro de usuarios asigna automáticamente el grupo `Quimicos`. Antes del primer uso,
crear desde `/admin` los grupos con sus permisos:

- **Administradores**: permisos completos de datos maestros (uso vía `/admin`).
- **Colaboradores**: add/change/delete de `Industria`, `Aplicacion`, `ElementoQuimico`, `DetalleElemento`.
- **Químicos**: sin permisos de maestros (solo gestión de sus compuestos).

### Tests

```bash
pytest app_quimico -q
```

## Seguridad

- `SECRET_KEY`, `DEBUG` y credenciales de base de datos se leen de variables de entorno
  (`python-decouple`); ver `.env.example`. Ningún secreto se versiona.
- `STATIC_ROOT` configurado para `collectstatic` en despliegue.
- CSRF, sesiones y validadores de contraseña con la configuración estándar de Django.
- Headers de seguridad: `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  same-origin`, `X-Frame-Options: DENY`.
- Hardening HTTPS por variables de entorno para producción: `SECURE_HSTS_SECONDS`,
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` (en desarrollo
  quedan desactivados; ver `.env.example`).
- Rate limiting del login con `django-axes`: bloqueo tras 5 intentos fallidos por
  usuario e IP, con cool-off de 1 hora.
- Ownership estricto: los compuestos web son privados de su dueño para todos los
  roles, verificado por tests de permisos.
- Suite de **125 ejecuciones de tests** (108 tests, algunos parametrizados) cubre permisos,
  parser, servicios, forms, paginación, seguridad, flujos de autenticación, MFA y el
  backend de email.

## Roadmap

- [x] CI con GitHub Actions (tests en cada push)
- [x] Recuperación y cambio de contraseña, MFA TOTP, envío de email real (Brevo SMTP/API)
- [x] Tema claro/oscuro persistente; paginación en listados
- [x] Códigos de respaldo MFA de un solo uso (`otp_static`) — **prerrequisito de la API REST**
- [ ] API REST con Django REST Framework (mismas reglas de propiedad por rol)
- [ ] Soporte de hidratos en el motor de cálculo
- [ ] Pulido de navbar en ancho móvil (360–414 px, ambos temas)
- [ ] Integración de flujos completos en tests + contenedor de despliegue
