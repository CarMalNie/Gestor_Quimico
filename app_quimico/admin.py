from django.contrib import admin
from .models import (
    Industria, Aplicacion, 
    ElementoQuimico, DetalleElemento, 
    CompuestoQuimico, CompuestoAplicacion
)

# ============================ #
# INDUSTRIA (Tabla Maestra)    #
# ============================ #

@admin.register(Industria)
class IndustriaAdmin(admin.ModelAdmin):
    # Muestra campos clave en el listado
    list_display = ('id', 'nombre_industria')
    # Permite buscar rápidamente por nombre
    search_fields = ('nombre_industria',)
    # Paginación
    list_per_page = 20

# ======================================= #
# APLICACIÓN (Relación 1:N con Industria) #
# ======================================= #

@admin.register(Aplicacion)
class AplicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre_uso', 'id_industria')
    search_fields = ('nombre_uso',)
    # Permite filtrar por la industria a la que pertenece
    list_filter = ('id_industria',)
    list_per_page = 20
    
# =========================== #
# ELEMENTO QUÍMICO Y DETALLES #
# =========================== #

# Definimos un Inline para ver los detalles dentro del Elemento (1:1)
class DetalleElementoInline(admin.StackedInline):
    model = DetalleElemento
    can_delete = False
    verbose_name_plural = 'Detalles Científicos'

@admin.register(ElementoQuimico)
class ElementoQuimicoAdmin(admin.ModelAdmin):
    # Muestra las propiedades clave en el listado
    list_display = ('simbolo_elemento', 'nombre_elemento', 'numero_atomico_elemento', 'peso_atomico_elemento')
    # Campos de búsqueda
    search_fields = ('simbolo_elemento', 'nombre_elemento', 'numero_atomico_elemento')
    # Filtro rápido por Número Atómico
    list_filter = ('numero_atomico_elemento',)
    ordering = ('numero_atomico_elemento',)
    # Muestra los detalles científicos en la misma página de edición
    inlines = (DetalleElementoInline,)
    list_per_page = 20

# ===================================== #
# COMPUESTO QUÍMICO (Cálculo Inmutable) #
# ===================================== #

@admin.register(CompuestoQuimico)
class CompuestoQuimicoAdmin(admin.ModelAdmin):
    list_display = ('formula_compuesto', 'nombre_compuesto', 'peso_molecular_compuesto', 'id_industria', 'usuario')
    search_fields = ('formula_compuesto', 'nombre_compuesto')
    list_filter = ('id_industria', 'usuario')
    ordering = ('nombre_compuesto',)
    
    # CRÍTICO para Integridad: PM y Fórmula son inmutables después de la creación
    readonly_fields = ('formula_compuesto', 'peso_molecular_compuesto', 'usuario')
    list_per_page = 20