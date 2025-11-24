
-----

# ⚛️ Gestor Químico

## Descripción del Proyecto

El **Gestor Químico** es una aplicación web empresarial desarrollada con el framework Django y Python, diseñada para la administración integral de elementos y compuestos químicos.

Este sistema permite a los usuarios registrados (Químicos, Colaboradores y Administradores) crear, listar, modificar y eliminar entidades clave, asegurando la integridad de los datos químicos y aplicando estrictas reglas de autorización y permisos por rol.

### 🎨 Paleta de Colores

El diseño utiliza un tema con alto contraste para asegurar la legibilidad y sigue la siguiente paleta de colores:

| Nombre | Código Hex | Uso Principal |
| :--- | :--- | :--- |
| **Deep Space Blue** | `#023047` | Fondo de Navbar y Footer, Texto de Contenido. |
| **Blue-Green** | `#219ebc` | Acento Primario, Enlaces, Texto de Fórmula. |
| **Amber Flame** | `#ffb703` | Botones de Éxito, Hover de Enlaces. |
| **Princeton Orange** | `#fb8500` | Botones de Advertencia/Modificación. |
| **Sky Blue Light** | `#8ecae6` | Enlaces Secundarios. |

---

## 🔑 Configuración Inicial y Notas CRÍTICAS (Lectura Obligatoria)

La operatividad completa del sistema depende de la correcta configuración de grupos y datos maestros **antes** de que los usuarios Químicos comiencen a trabajar.

### 1. Configuración de Grupos de Permisos (Obligatorio)

Es **OBLIGATORIO** que un superusuario cree los siguientes grupos de permisos a través del Panel de Administración (`/admin`) antes de que cualquier usuario registrado interactúe con el sitio:

* **Administradores**
* **Colaboradores**
* **Químicos** (CRÍTICO: Este grupo es el asignado por defecto a los nuevos registros.)

### 2. Trazabilidad y Visibilidad del Catálogo

La visibilidad de los datos está segregada por grupo:

* **Administradores y Colaboradores:** Podrán ver **TODO** el catálogo de compuestos químicos creado por cualquier usuario. Esto les permite gestionar y auditar la base de datos completa.
* **Químicos:** Solo podrán ver y gestionar los compuestos químicos que **ellos mismos hayan creado**.

### 3. Integridad de Datos Maestros

Los usuarios con permisos de creación de compuestos (Químicos) dependen de los datos maestros:

* **IMPORTANTE PARA ADMINISTRADORES/COLABORADORES:** Deben crear las **Industrias** y **Aplicaciones** en el panel de administración **ANTES** de que los Químicos puedan crear Compuestos. De lo contrario, los formularios fallarán.
* Se debe mantener la congruencia lógica de los datos. Por ejemplo, la combinación `Industria: Farmacéutica` con `Uso: Electrodo de Soldadura` generará inconsistencias en la base de datos.

### 4. Lógica Avanzada de Peso Molecular (PM)

* Este proyecto utiliza un archivo **`utils.py`** donde reside la **lógica de cálculo avanzada del Peso Molecular** de los compuestos ingresados por el usuario.
* El $\text{PM}$ de un compuesto se calcula automáticamente al crearse y es **inmutable** una vez guardado, asegurando la integridad de la fórmula química en la base de datos.

---

## 🛠️ Pasos para la Implementación (Desde GitHub)

Para poner en funcionamiento el **Gestor Químico** en tu entorno local, sigue los siguientes pasos:

### Prerrequisitos
* Python 3.10 o superior.
* Git instalado.

### 1. Clonar el Repositorio
```bash
git clone [URL_DEL_REPOSITORIO] gestor_quimico
cd gestor_quimico
```

### 2. Crear y Activar el Entorno Virtual

```bash
# Crear el entorno
python -m venv venv

# Activar el entorno (Windows)
.\venv\Scripts\activate
# Activar el entorno (Linux/macOS)
source venv/bin/activate
```

### 3. Instalar Dependencias

Instala todos los paquetes Python necesarios listados en `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Configuración de Base de Datos y Migraciones

Asegúrate de que la configuración de la base de datos en `core/settings.py` sea correcta (SQLite por defecto).

```bash
# Aplicar migraciones iniciales a la base de datos
python manage.py migrate

# (Opcional) Crear un Superusuario para acceder al Panel de Administración
python manage.py createsuperuser
```

### 5. Configuración Crítica de Permisos y Datos Maestros

Accede al Panel de Administración (`/admin`) con el Superusuario y realiza los siguientes pasos **OBLIGATORIOS**:

1.  **Crear Grupos:** Crea los grupos **Administradores**, **Colaboradores**, y **Químicos**.
2.  **Crear Datos Maestros:** Crea algunas instancias de **Industrias** y **Aplicaciones**.

### 6. Ejecutar el Servidor

```bash
python manage.py runserver
```

La aplicación estará accesible en `http://127.0.0.1:8000/`.

-----

## Requisitos Cumplidos

Este proyecto demuestra el dominio de las competencias técnicas, divididas en las siguientes áreas:

### I. Fundamentos de Desarrollo de Aplicaciones Web con Python y Django

| Requisito Cumplido | Evidencia en el Código |
| :--- | :--- |
| **Uso de Herramientas Administrativas** | Configuración de proyecto con `manage.py` y estructura de directorios estándar de $\text{Django}$. |
| **Implementación con Templates Dinámicos** | Uso del Sistema de Plantillas de $\text{Django}$ ($\text{DTL}$) en `elemento_detalle.html` y `compuesto_lista.html` para renderizar datos de la $\text{DB}$ con lógica condicional (`{% if user.is_authenticated %}`). |
| **Implementación de Formularios** | Uso de **`ModelForm`** en todas las $\text{CBVs}$ de $\text{CRUD}$ para la captura, validación de rangos y almacenamiento de datos. |
| **Autenticación y Autorización** | Uso de `django.contrib.auth` para $\text{Login}$/$\text{Logout}$ y la implementación de `LoginRequiredMixin`. Control de acceso estricto mediante filtros por `user.groups.filter()` para segregar vistas y botones. |
| **Módulo de Administración de Permisos** | Configuración y personalización del $\text{Admin}$ para gestionar usuarios y la creación de los grupos **Administradores**, **Colaboradores** y **Químicos** con permisos específicos. |

### II. Acceso a Datos en Aplicaciones Python y Django

| Requisito Cumplido | Evidencia en el Código |
| :--- | :--- |
| **Integración con Bases de Datos (ORM)** | El proyecto está configurado para utilizar el $\text{ORM}$ de $\text{Django}$ (en `settings.py`) para todas las operaciones de datos, eliminando la necesidad de $\text{SQL}$ manual. |
| **Modelado de Relaciones (1:1, 1:N, M:N)** | **1:1:** `ElementoQuimico` con `DetalleElemento`. **1:N:** `CompuestoQuimico` con `Usuario` (dueño). **M:N (Avanzado):** `ElementoQuimico` y `CompuestoQuimico` unidos por la tabla intermedia `ElementoCompuesto` (con atributo extra `cantidad_elem_en_comp`). |
| **Uso de Migraciones** | El sistema utiliza `makemigrations` y `migrate` para propagar los cambios del modelo ($\text{PM}$ calculado, nuevas relaciones) al esquema de la $\text{DB}$. |
| **Consultas de Filtrado y Personalizadas** | Uso avanzado del $\text{ORM}$ en `get_queryset()`: Filtrado por dueño (`usuario=self.request.user`), filtros complejos (`Q` objects) y el uso de **`annotate(Count)`** para calcular el número de aplicaciones en la vista de lista. |
| **Implementación de Operaciones CRUD** | Implementación completa de $\text{CRUD}$ (Crear, Leer, Actualizar, Eliminar) para las entidades principales (`ElementoQuimico` y `CompuestoQuimico`) utilizando $\text{CBVs}$ genéricas. |
| **Reconocimiento de Aplicaciones Preinstaladas** | Uso de **`django.contrib.admin`** y **`django.contrib.auth`** como base fundamental del proyecto. |

-----
