from django.db import models
from django.db.models import UniqueConstraint
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.contrib.auth import get_user_model

import networkx as nx
from pysmiles import read_smiles

# Obtener el modelo de usuario activo
User = get_user_model() 

# ================================ #
# DEFINICIONES DE CHOICES Y RANGOS #
# ================================ #

# Opciones para Grupos (1 al 18)
GRUPO_CHOICES = [(i, str(i)) for i in range(1, 19)]

# Opciones para Períodos (1 al 7)
PERIODO_CHOICES = [(i, str(i)) for i in range(1, 8)]

# Opciones para Categoría (10 categorías reales: sin choices muertos como
# 'Metales' u 'Otros No Metales', que no tenían ningún elemento asignado).
CATEGORIA_CHOICES = [
    ('No Metales', 'No Metales'),
    ('Alcalinos', 'Alcalinos'),
    ('Alcalinos-térreos', 'Alcalinos-térreos'),
    ('Lantánidos', 'Lantánidos'),
    ('Actínidos', 'Actínidos'),
    ('Metales de Transición', 'Metales de Transición'),
    ('Otros Metales', 'Otros Metales'),
    ('Metaloides', 'Metaloides'),
    ('Halógenos', 'Halógenos'),
    ('Gases Nobles', 'Gases Nobles'),
]

# Familia didáctica "Metales": agrupa las categorías metálicas (los metaloides
# NO cuentan como metales). Debe coincidir exactamente con los valores de
# categoria_elemento usados en app_quimico/data/detalles_elementos.py.
FAMILIA_METALES = (
    'Alcalinos',
    'Alcalinos-térreos',
    'Metales de Transición',
    'Otros Metales',
    'Lantánidos',
    'Actínidos',
)

# Familia didáctica "No metales": No Metales + Halógenos + Gases Nobles.
FAMILIA_NO_METALES = (
    'No Metales',
    'Halógenos',
    'Gases Nobles',
)

# Opciones para Tipos de Concentración
CONCENTRACION_CHOICES = [
    ('%p/p', '% Peso en Peso (p/p)'),
    ('%p/v', '% Peso en Volumen (p/v)'),
    ('ppm', 'Partes por Millón (ppm)'),
    ('[M]', 'Molaridad [M]'),
    ('[N]', 'Normalidad [N]'),
    ('otra', 'Otra Unidad'),
]


# ============================== #
# TABLAS INDEPENDIENTES / PADRES #
# ============================== #

# (1) Tabla industrias
class Industria(models.Model):
    nombre_industria = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nombre de la Industria"
    )

    class Meta:
        verbose_name = "Industria"
        verbose_name_plural = "Industrias"

    def __str__(self):
        return self.nombre_industria


# (2) Tabla elementos_quimicos (Tabla Periódica)
class ElementoQuimico(models.Model):
    nombre_elemento = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nombre del Elemento"
    )
    simbolo_elemento = models.CharField(
        max_length=3, 
        unique=True, 
        verbose_name="Símbolo"
    )
    # Número Atómico (Z): [1, 118]
    numero_atomico_elemento = models.IntegerField(
        unique=True, 
        validators=[
            MinValueValidator(1, message="El Número Atómico (Z) debe ser mayor que cero (1 o superior)"),
            MaxValueValidator(118, message="El valor máximo permitido es 118.") 
        ],
        verbose_name="Número Atómico (Z)"
    )
    # Peso Atómico: [1.0070, 294.0000]
    peso_atomico_elemento = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        validators=[
            MinValueValidator(Decimal('1.0070'), message="El valor mínimo es 1.0070 g/mol (Hidrógeno)"),
            MaxValueValidator(Decimal('294.0000'), message="El valor máximo es 294 g/mol.")
        ],
        verbose_name="Peso Atómico"
    )

    class Meta:
        verbose_name = "Elemento Químico"
        verbose_name_plural = "Elementos Químicos"

    def __str__(self):
        return f"{self.simbolo_elemento} - {self.nombre_elemento}"


# (3) Tabla compuestos_quimicos

# ==================================================================== #
# CLASIFICACIÓN DIDÁCTICA DEL ENLACE A PARTIR DEL SMILES (T7)
# ==================================================================== #

# Cargas pequeñas como superíndice unicode; una carga fuera de este rango
# simplemente no se muestra (la clasificación es orientativa, no un dato
# estructural).
_CARGA_SUPERINDICE = {
    1: '⁺', -1: '⁻',
    2: '²⁺', -2: '²⁻',
    3: '³⁺', -3: '³⁻',
}


def _superindice_carga(carga):
    """Superíndice unicode para una carga entera pequeña (0 -> '')."""
    if not carga:
        return ''
    return _CARGA_SUPERINDICE.get(carga, '')


def _etiqueta_especie(mol, nodos):
    """Resumen de una especie (un fragmento SMILES) en orden de Hill.

    Orden de Hill: C primero, H después, y el resto alfabético. Los hidrógenos
    implícitos que calcula pysmiles se cuentan para que un ion como OH⁻ no se
    muestre como un O⁻ engañoso. La carga neta del fragmento va como superíndice.
    """
    conteos = {}
    carga_neta = 0
    for nodo in nodos:
        datos = mol.nodes[nodo]
        elemento = datos.get('element')
        if elemento:
            conteos[elemento] = conteos.get(elemento, 0) + 1
        hidrogenos = datos.get('hcount') or 0
        if hidrogenos:
            conteos['H'] = conteos.get('H', 0) + hidrogenos
        carga_neta += datos.get('charge') or 0

    orden = sorted(
        conteos,
        key=lambda simbolo: (simbolo != 'C', simbolo != 'H', simbolo),
    )
    formula = ''.join(
        simbolo + (str(conteos[simbolo]) if conteos[simbolo] > 1 else '')
        for simbolo in orden
    )
    return formula + _superindice_carga(carga_neta)


class CompuestoQuimico(models.Model):
    nombre_compuesto = models.CharField(
        max_length=255, 
        verbose_name="Nombre del Compuesto"
    )
    formula_compuesto = models.CharField(
        max_length=255, 
        unique=False, 
        verbose_name="Fórmula Química"
    )
    # Clave foránea directa para la obligatoriedad en formulario (FIX de UX)
    id_industria = models.ForeignKey(
        'Industria',  
        on_delete=models.RESTRICT, 
        null=False,             
        blank=False,            
        verbose_name='Tipo de Industria'
    )
    # Clave foránea para el dueño del registro (Permisos)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='compuestos_creados',
        null=True, 
        blank=True,
        verbose_name='Usuario Creador'
    )
    peso_molecular_compuesto = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[MinValueValidator(Decimal('0.0001'))],
        blank=True, 
        null=True,
        verbose_name="Peso Molecular"
    )
    fecha_registro_compuesto = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )
    smiles = models.TextField(
        blank=True,
        null=True,
        verbose_name='Estructura SMILES',
        help_text='Notación SMILES opcional para mostrar la estructura 2D'
    )

    class Meta:
        verbose_name = "Compuesto Químico"
        verbose_name_plural = "Compuestos Químicos"
        constraints = [
            UniqueConstraint(
                fields=['formula_compuesto', 'usuario'], 
                name='unique_formula_per_user'
            )
        ]

    def __str__(self):
        return f"{self.formula_compuesto} ({self.nombre_compuesto})"

    def clasificar_enlace_smiles(self):
        """Caption didáctico del tipo de enlace derivado del SMILES.

        Devuelve ``None`` cuando no hay SMILES usable (vacío o no parseable),
        de modo que la plantilla no renderiza nada y nunca levanta excepción.
        Varios fragmentos desconectados (``.``) o una carga neta distinta de
        cero describen una especie iónica, y cada fragmento se lista como una
        etiqueta de especie deduplicada; un único fragmento neutro es
        covalente (aunque tenga cargas internas: zwitterión). Los enlaces
        covalentes internos de un ion poliatómico se ven en el propio dibujo y
        no se repiten acá. Sin caché a propósito: son unas pocas moléculas
        chicas por render, y así el modelo no acumula estado.
        """
        valor = (self.smiles or '').strip()
        if not valor:
            return None

        try:
            # ``zero_order_bonds=False`` mantiene los separadores '.' como
            # desconexiones reales; con el default pysmiles los une con un
            # enlace de orden 0 y todo fragmento parecería conectado.
            mol = read_smiles(valor, zero_order_bonds=False)
        except Exception:
            return None

        if mol is None or len(mol.nodes) == 0:
            return None

        fragmentos = sorted(nx.connected_components(mol), key=min)
        carga_neta = sum(
            (datos.get('charge') or 0) for _, datos in mol.nodes(data=True)
        )

        if len(fragmentos) > 1 or carga_neta != 0:
            especies = []
            for fragmento in fragmentos:
                etiqueta = _etiqueta_especie(mol, fragmento)
                if etiqueta and etiqueta not in especies:
                    especies.append(etiqueta)
            if not especies:
                return None
            return 'Estructura iónica: ' + ' · '.join(especies)

        return 'Enlace covalente'

    def smiles_para_render(self):
        """SMILES para el dibujo 2D, con los H de O/N/S explicitados.

        Solo alimenta ``data-smiles`` en las plantillas. El SMILES
        almacenado y ``clasificar_enlace_smiles`` no se tocan: la
        clasificación didáctica sigue leyendo el valor original. Sin SMILES
        devuelve cadena vacía (la plantilla no renderiza nada).
        """
        if not self.smiles:
            return ''
        # Import local: ``app_quimico.utils`` importa este módulo a nivel
        # superior, así que un import de módulo acá sería circular.
        from app_quimico.utils import expandir_heteroatomos

        return expandir_heteroatomos(self.smiles)


# =========================== #
# TABLAS DEPENDIENTES / HIJAS #
# =========================== #

# (4) Tabla aplicaciones (Relación M:1 con Industrias)
class Aplicacion(models.Model):
    id_industria = models.ForeignKey(
        Industria, 
        on_delete=models.RESTRICT, 
        verbose_name="Industria"
    )
    nombre_uso = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name="Nombre del Uso/Aplicación"
    )

    class Meta:
        verbose_name = "Aplicación"
        verbose_name_plural = "Aplicaciones"

    def __str__(self):
        return self.nombre_uso


# (5) Tabla detalles_elementos (Relación 1:1 con ElementoQuimico)
class DetalleElemento(models.Model):
    id_elemento = models.OneToOneField(
        ElementoQuimico, 
        on_delete=models.CASCADE, 
        primary_key=True,
        verbose_name="Elemento Químico"
    )
    
    grupo_elemento = models.IntegerField(
        choices=GRUPO_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(18)],
        verbose_name="Grupo"
    )
    
    periodo_elemento = models.IntegerField(
        choices=PERIODO_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        verbose_name="Periodo"
    )
    
    categoria_elemento = models.CharField(
        max_length=50, 
        choices=CATEGORIA_CHOICES,
        verbose_name="Categoría"
    )
    
    # Electronegatividad: [0.70, 4.00]
    electronegatividad = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(Decimal('0.70'), message="El valor mínimo es 0.70 (Francio)"),
            MaxValueValidator(Decimal('4.00'), message="El valor máximo es 4.00 (Flúor)")
        ]
    )
    
    # Afinidad Electrónica: [-348.60, -0.0001]
    afinidad_electronica = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(Decimal('-348.60'), message="El valor mínimo es -348.60 kJ/mol (Cloro)"),
            MaxValueValidator(Decimal('-0.0001'), message="El valor máximo debe ser estrictamente negativo")
        ],
        verbose_name="Afinidad Electrónica"
    )
    
    # Energía de Ionización: [375.70, 2372.30]
    energia_de_ionizacion = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(Decimal('375.70'), message="El valor mínimo es 375.70 kJ/mol (Cesio)"),
            MaxValueValidator(Decimal('2372.30'), message="El valor máximo es 2372.30 kJ/mol (Helio)")
        ],
        verbose_name="Energía de Ionización"
    )
    
    # Radio Covalente: [0.32, 2.98]
    radio_covalente = models.DecimalField(
        max_digits=5, 
        decimal_places=3, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(Decimal('0.32'), message="El valor mínimo es 0.32 Å."),
            MaxValueValidator(Decimal('2.98'), message="El valor máximo es 2.98 Å.")
        ],
        verbose_name="Radio Covalente"
    )
    
    descripcion_elemento = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Descripción"
    )

    class Meta:
        verbose_name = "Detalle del Elemento"
        verbose_name_plural = "Detalles de Elementos"

    def __str__(self):
        return f"Detalles de {self.id_elemento.simbolo_elemento}"


# (6) Tabla elementos_compuestos (Tabla intermedia M:N)
class ElementoCompuesto(models.Model):
    id_elemento = models.ForeignKey(
        ElementoQuimico, 
        on_delete=models.CASCADE, 
        verbose_name="Elemento"
    )
    id_compuesto = models.ForeignKey(
        CompuestoQuimico, 
        on_delete=models.CASCADE, 
        verbose_name="Compuesto"
    )
    cantidad_elem_en_comp = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )

    class Meta:
        verbose_name = "Elemento en Compuesto"
        verbose_name_plural = "Elementos en Compuestos"
        constraints = [
            UniqueConstraint(
                fields=['id_elemento', 'id_compuesto'],
                name='unique_elemento_por_compuesto',
            ),
        ]

    def __str__(self):
        return f"{self.id_elemento.simbolo_elemento} en {self.id_compuesto.formula_compuesto}"


# (7) Tabla elementos_aplicaciones (Tabla intermedia M:N)
class ElementoAplicacion(models.Model):
    id_elemento = models.ForeignKey(
        ElementoQuimico, 
        on_delete=models.CASCADE, 
        verbose_name="Elemento"
    )
    id_aplicacion = models.ForeignKey(
        Aplicacion, 
        on_delete=models.CASCADE, 
        verbose_name="Aplicación"
    )
    notas_uso = models.CharField(
        max_length=255, 
        verbose_name="Notas de Uso"
    )

    class Meta:
        verbose_name = "Elemento en Aplicación"
        verbose_name_plural = "Elementos en Aplicaciones"
        constraints = [
            UniqueConstraint(
                fields=['id_elemento', 'id_aplicacion'],
                name='unique_elemento_por_aplicacion',
            ),
        ]

    def __str__(self):
        return f"{self.id_elemento.simbolo_elemento} - {self.id_aplicacion.nombre_uso}"


# (8) Tabla compuestos_aplicaciones (Relación M:N simplificada a Concentración)
class CompuestoAplicacion(models.Model):
    id_compuesto = models.ForeignKey(
        CompuestoQuimico, 
        on_delete=models.CASCADE, 
        verbose_name="Compuesto"
    )
    
    id_aplicacion = models.ForeignKey(
        Aplicacion, 
        on_delete=models.CASCADE, 
        verbose_name="Aplicación"
    )
    
    concentracion_minima = models.DecimalField(
        max_digits=10, 
        decimal_places=2,  
        validators=[MinValueValidator(Decimal('0.01'), message="La concentración mínima debe ser mayor o igual a 0.01")],
        verbose_name="Concentración Mínima"
    )
    
    tipo_concentracion = models.CharField(
        max_length=5, 
        choices=CONCENTRACION_CHOICES, 
        default='%p/p',
        verbose_name="Tipo de Concentración"
    )

    class Meta:
        verbose_name = "Compuesto en Aplicación"
        verbose_name_plural = "Compuestos en Aplicaciones"
        constraints = [
            UniqueConstraint(
                fields=['id_compuesto', 'id_aplicacion'],
                name='unique_compuesto_por_aplicacion',
            ),
        ]

    def __str__(self):
        return f"{self.id_compuesto.formula_compuesto} en Concentración"