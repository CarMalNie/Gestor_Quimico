
-----

# ⚛️ Gestor Químico

## Descripción y Arquitectura del Proyecto

El **Gestor Químico** es una aplicación web empresarial (MVT/Django) diseñada para la administración centralizada y segura de la Tabla Periódica, el cálculo de pesos moleculares y el control de inventario de usos industriales.

Este sistema permite a los usuarios registrados (**Químicos**, **Colaboradores** y **Administradores**) crear, listar, modificar y eliminar entidades clave, asegurando la integridad de los datos químicos y aplicando estrictas reglas de autorización y permisos por rol.

### Contexto Formativo: Consolidación del Desarrollo FullStack

Este proyecto es la **culminación de la fase final del recorrido formativo**. Representa la integración de los siguientes módulos:

  * **Fase 1 y 2: Lógica de Negocio Química:** La implementación de la $\text{Calculadora de Peso Molecular Avanzada}$ (que incluye el *parsing* de fórmulas complejas) se integra como la lógica central de cálculo en `views.py` y `utils.py`.
  * **Fase 3: Base de Datos Relacional:** El diseño de la base de datos se basa en relaciones $\text{M:N}$ y $\text{1:1}$ para modelar entidades científicas (`Elemento`, `DetalleElemento`, `Compuesto`).
  * **Fase 4: Aplicación Web (Gestor Químico):** Consolidación de todos los conceptos anteriores en un entorno web $\text{Django}$ funcional, demostrando $\text{MVT}$, $\text{ORM}$ y seguridad.

-----

### Paleta de Colores

El diseño utiliza un tema con alto contraste y sigue la siguiente paleta de colores:

| Nombre | Código Hex | Rol de Contraste |
| :--- | :--- | :--- |
| **Deep Space Blue** | `#023047` | Fondo Principal, Barras de Navegación y Footer. |
| **Blue-Green** | `#219ebc` | Acento Primario, Enlaces, Texto de Fórmula. |
| **Amber Flame** | `#ffb703` | Botones de Éxito y Acentos Cálidos. |
| **Princeton Orange** | `#fb8500` | Botones de Advertencia/Modificación. |
| **Sky Blue Light** | `#8ecae6` | Enlaces Secundarios y Texto de Contraste. |

-----

## Flujo de Trabajo y Funcionalidades Clave

### 1\. Gestión de Compuestos (Catálogo Personal)

  * **Lógica Principal:** La **Fórmula Química** es el identificador inmutable (Identidad) del compuesto.
  * **Cálculo PM:** El Peso Molecular ($\text{PM}$) se calcula automáticamente en la creación.
  * **Segregación de Datos:**
      * **Químicos (Usuarios Regulares):** Solo ven y gestionan los compuestos que **ellos mismos crearon** (Catálogo Privado).
      * **Administradores/Colaboradores:** Ven el **Catálogo Completo** (vista maestra) para auditoría y gestión.

### 2\. Gestión de Elementos (Tabla Periódica)

  * **Propósito:** Almacenar datos de elementos químicos con validadores de rango estricto ($\text{IUPAC}$).
  * **Seguridad:** El $\text{CRUD}$ está reservado a $\text{Administradores}$ y $\text{Colaboradores}$.

-----

## Configuración Inicial y Notas CRÍTICAS (Lectura Obligatoria)

### 1\. Configuración de Grupos de Permisos (Obligatorio)

Es **OBLIGATORIO** que un superusuario cree los siguientes grupos de permisos a través del Panel de Administración (`/admin`) antes de que cualquier usuario registrado interactúe con el sitio:

  * **Administradores**
  * **Colaboradores**
  * **Químicos** (CRÍTICO: Este grupo es el asignado por defecto a los nuevos registros.)

### 2\. Integridad de Datos Maestros

  * **IMPORTANTE PARA ADMINISTRADORES/COLABORADORES:** Deben crear las **Industrias** y **Aplicaciones** en el panel de administración **ANTES** de que los Químicos puedan crear Compuestos. De lo contrario, los formularios fallarán.
  * Se debe mantener la **congruencia lógica de los datos**.

### 3\. Lógica Avanzada de PM

  * Este proyecto utiliza un archivo **`utils.py`** donde reside la **lógica de cálculo avanzada del Peso Molecular** de los compuestos.

-----

## Pasos para la Implementación (Desde GitHub)

### Prerrequisitos

  * Python 3.10 o superior.
  * Git instalado.
  * Base de datos MySQL o PostgreSQL configurada y accesible (según tu `settings.py`).

### 1\. Clonar el Repositorio

```bash
git clone [URL_DEL_REPOSITORIO] gestor_quimico
cd gestor_quimico
```

### 2\. Crear y Activar el Entorno Virtual

```bash
python -m venv venv

# Activar el entorno (Windows)
.\venv\Scripts\activate
```

### 3\. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4\. Configuración de Base de Datos y Migraciones

```bash
# Aplicar migraciones iniciales a la base de datos
python manage.py migrate

# Crear Superusuario y configurar Grupos
python manage.py createsuperuser
```

### 5\. Ejecutar el Servidor

```bash
python manage.py runserver
```

La aplicación estará accesible en `http://127.0.0.1:8000/`.

-----

## Requisitos Cumplidos

### I. Fundamentos de Desarrollo de Aplicaciones Web con Python y Django

| Requisito Cumplido | Evidencia en el Código |
| :--- | :--- |
| **Uso de Herramientas Administrativas** | Configuración de proyecto con `manage.py` y estructura estándar de $\text{Django}$. |
| **Implementación con Templates Dinámicos** | Uso de $\text{DTL}$ en `elemento_detalle.html` y `compuesto_lista.html` para renderizar datos dinámicos con lógica condicional. |
| **Implementación de Formularios** | Uso de **`ModelForm`** en todas las $\text{CBVs}$ de $\text{CRUD}$ para la captura, validación de rangos y almacenamiento de datos. **CRÍTICO:** Utilizamos **`django-crispy-forms`** para dar formato a todos los formularios. |
| **Autenticación y Autorización** | Uso de `django.contrib.auth` para $\text{Login}$/$\text{Logout}$ y `LoginRequiredMixin`. Control de acceso estricto mediante filtros por dueño (`user.groups.filter()`) para segregar vistas y botones. |
| **Módulo de Administración de Permisos** | Configuración del $\text{Admin}$ para gestionar usuarios y la creación de grupos con permisos específicos. |

### II. Acceso a Datos en Aplicaciones Python y Django

| Requisito Cumplido | Evidencia en el Código |
| :--- | :--- |
| **Modelado de Relaciones (1:1, 1:N, M:N)** | **1:1:** `DetalleElemento` $\leftrightarrow$ `ElementoQuimico`. **1:N:** $\text{Compuestos}$ $\leftrightarrow$ `Usuario`. **M:N (Avanzado):** $\text{Composición Atómica}$ con `ElementoCompuesto`. |
| **Uso de Migraciones** | Uso de `makemigrations` y `migrate` para propagar todos los cambios del modelo. |
| **Consultas de Filtrado y Personalizadas** | Uso avanzado del $\text{ORM}$ en `get_queryset()`: Filtrado por dueño, $\text{Q}$ objects y el uso de **`annotate(Count)`** para cálculos estadísticos. |
| **Implementación de Operaciones CRUD** | $\text{CRUD}$ completo implementado y protegido para todas las entidades principales utilizando $\text{CBVs}$. |
| **Reconocimiento de Aplicaciones Preinstaladas** | Uso de **`django.contrib.admin`** y **`django.contrib.auth`** como base fundamental del proyecto. |

```
```