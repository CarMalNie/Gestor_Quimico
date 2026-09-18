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

## Arquitectura

| Capa | Implementación |
| :--- | :--- |
| Modelos (8 tablas) | `Industria`, `ElementoQuimico` + `DetalleElemento` (1:1), `CompuestoQuimico`, `Aplicacion`, `ElementoCompuesto` (M:N), `CompuestoAplicacion` (M:N), `ElementoAplicacion` (M:N) |
| Vistas | Class-Based Views (CRUD completo), transacciones atómicas, `select_related`/`prefetch_related` |
| Motor de cálculo | `app_quimico.utils.CalculadoraPM`: validación IUPAC estricta, tokenización posicional, balanceo de agrupadores, cache de pesos por proceso |
| Formularios | `django-crispy-forms` (Bootstrap 5), validación cruzada industria↔aplicación, cascada cliente |
| Frontend | Templates DTL, Bootstrap 5.3 local-friendly, CSS de diseño propio |
| Base de datos | MySQL (modo `STRICT_TRANS_TABLES`) |
| Tests | pytest + pytest-django: permisos/ownership, parser (sin BD), validación de formularios |

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
- Suite de 41 tests cubre permisos, parser, servicios, forms, paginación y seguridad.

## Roadmap

- [ ] API REST con Django REST Framework (mismas reglas de propiedad por rol)
- [ ] Cobertura de tests ampliada (integración de flujos completos)
- [ ] CI con GitHub Actions (tests + lint) y contenedor de despliegue
- [ ] Soporte de hidratos en el motor de cálculo
- [ ] Paginación y ordenamiento en listados
