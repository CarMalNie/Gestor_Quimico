from django.urls import reverse_lazy
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db import transaction 
from decimal import Decimal 
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.db.models import Prefetch, Q, Count
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from .utils import CalculadoraPM # Clase de utilidad para el cálculo

from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, DetailView
)

from .models import (
    Industria, ElementoQuimico, DetalleElemento, 
    CompuestoQuimico, Aplicacion, CompuestoAplicacion, ElementoCompuesto
)

from .forms import (
    IndustriaForm, ElementoQuimicoForm, DetalleElementoForm, 
    CompuestoQuimicoForm, AplicacionForm, CompuestoAplicacionForm,
    ElementoFilterForm, CompuestoFilterForm, RegistroForm
)


# =========================== #
# VISTA BIENVENIDA Y HANDLERS #
# =========================== #

class HomeView(TemplateView):
    """Renderiza la página de bienvenida del sistema."""
    template_name = 'app_quimico/home.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_bienvenida'] = "Sistema de Gestión y Cálculo Químico"
        return context

def error_404_handler(request, exception):
    """Maneja el error 404 (Página no encontrada)."""
    return render(request, 'error_404.html', {}, status=404) 

def error_403_handler(request, exception):
    """Maneja el error 403 (Permiso denegado/Prohibido)."""
    return render(request, 'error_403.html', {}, status=403)


# ======================= #
# VISTAS DE AUTENTICACIÓN #
# ======================= #

class RegistroView(CreateView):
    """
    Permite el registro de un nuevo usuario y lo asigna automáticamente 
    al grupo 'Quimicos' por defecto.
    """
    form_class = RegistroForm
    success_url = reverse_lazy('login')
    template_name = 'app_quimico/autenticacion/registro.html' 

    def form_valid(self, form):
        # 1. Guardar el usuario
        response = super().form_valid(form)
        user = form.instance # Obtener el usuario recién creado
        
        # 2. Lógica CRÍTICA: Asignación automática al grupo 'Quimicos'
        try:
            quimicos_group = Group.objects.get(name='Quimicos')
            user.groups.add(quimicos_group)
        except Group.DoesNotExist:
            messages.warning(self.request, "Advertencia: El grupo 'Quimicos' no existe en la BD. Por favor, créelo.")
            
        messages.success(self.request, "¡Registro exitoso! Por favor, inicia sesión.")
        return response


# ============================================= #
# AÑADIR VISTAS PERSONALIZADAS DE AUTENTICACIÓN #
# ============================================= #

# 1. VISTA DE LOGIN PERSONALIZADA (Añade mensaje al iniciar sesión)
class CustomLoginView(LoginView):
    # Asume que tu template de login se llama 'autenticacion/login.html'
    template_name = 'app_quimico/autenticacion/login.html' 
    
    def form_valid(self, form):
        # 1. Ejecutar el login del padre (lo hace internamente)
        response = super().form_valid(form)
        
        # 2. Agregar el mensaje de éxito DESPUÉS de loguear
        messages.success(self.request, f"¡Bienvenido(a) de nuevo, {self.request.user.username}! Has iniciado sesión con éxito.")
        
        return response

# 2. VISTA DE LOGOUT PERSONALIZADA (Añade mensaje al cerrar sesión)
def custom_logout_view(request):
    # 1. Agregar el mensaje de éxito ANTES de cerrar sesión (para que el mensaje se conserve)
    messages.info(request, "Has cerrado sesión con éxito. ¡Vuelve pronto!")
    
    # 2. Cerrar la sesión del usuario
    logout(request)
    
    # 3. Redirigir al inicio (o donde desees)
    return redirect('home')


# =========================================== #
# CRUD para INDUSTRIA (ACCESO RESTRINGIDO)    #
# Regla: Admin/Colaborador (CRU); Admin (D)   #
# =========================================== #

# C - CREATE (Crear Industria)
class IndustriaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'app_quimico.add_industria' # Admin / Colaborador
    model = Industria
    form_class = IndustriaForm
    template_name = 'app_quimico/industria/industria_form.html' 
    success_url = reverse_lazy('industria_lista') 

    def form_valid(self, form):
        messages.success(self.request, "La industria ha sido registrada exitosamente.")
        return super().form_valid(form)

# R - READ (Lista Industrias)
class IndustriaListView(LoginRequiredMixin, ListView):
    # Requiere login (Químicos/Colaboradores/Admin)
    model = Industria
    template_name = 'app_quimico/industria/industria_lista.html' 
    context_object_name = 'industrias'

# U - UPDATE (Actualizar Industria)
class IndustriaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'app_quimico.change_industria' # Admin / Colaborador
    model = Industria
    form_class = IndustriaForm
    template_name = 'app_quimico/industria/industria_form.html' 
    success_url = reverse_lazy('industria_lista')

    def form_valid(self, form):
        messages.success(self.request, "La industria ha sido actualizada exitosamente.")
        return super().form_valid(form)

# D - DELETE (Eliminar Industria)
class IndustriaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'app_quimico.delete_industria' # Solo Admin
    model = Industria
    template_name = 'app_quimico/industria/industria_eliminar.html' 
    success_url = reverse_lazy('industria_lista')
    
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        messages.success(request, f"La industria '{obj.nombre_industria}' ha sido eliminada exitosamente.")
        return redirect(self.success_url)


# ============================================================ #
# CRUD para ELEMENTO QUÍMICO Y DETALLE (ACCESO RESTRINGIDO)    #
# Regla: Lectura abierta. CRUD restringido.                    #
# ============================================================ #

# C - CREATE (Crear Elemento + Detalle)
class ElementoCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'app_quimico.add_elementoquimico'
    """Crea ElementoQuimico y DetalleElemento en una sola transacción."""
    template_name = 'app_quimico/elemento_quimico/elemento_form.html' 
    success_url = reverse_lazy('elemento_lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['elemento_form'] = ElementoQuimicoForm(self.request.POST if self.request.method == 'POST' else None)
        context['detalle_form'] = DetalleElementoForm(self.request.POST if self.request.method == 'POST' else None)
        return context

    def post(self, request, *args, **kwargs):
        elemento_form = ElementoQuimicoForm(request.POST)
        detalle_form = DetalleElementoForm(request.POST)
        
        context = {'elemento_form': elemento_form, 'detalle_form': detalle_form}

        if elemento_form.is_valid() and detalle_form.is_valid():
            try:
                with transaction.atomic():
                    elemento = elemento_form.save()
                    detalle = detalle_form.save(commit=False)
                    detalle.id_elemento = elemento 
                    detalle.save()

                messages.success(request, f"Elemento '{elemento.simbolo_elemento}' y sus detalles han sido creados exitosamente.")
                return redirect(self.success_url)

            except Exception as e:
                messages.error(request, f"Ocurrió un error al guardar los datos: {e}")
                
        return self.render_to_response(context)
        
# R - READ (Lista Elementos)
class ElementoListView(ListView):
    # Abierto a todos (visitantes no requieren LoginRequiredMixin)
    """Muestra una lista de todos los elementos químicos registrados en formato de tarjeta."""
    model = ElementoQuimico
    template_name = 'app_quimico/elemento_quimico/elemento_lista.html' 
    context_object_name = 'elementos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ElementoFilterForm(self.request.GET)
        return context

    def get_queryset(self):
        queryset = ElementoQuimico.objects.select_related('detalleelemento').all()
        form = ElementoFilterForm(self.request.GET)
        
        if form.is_valid():
            data = form.cleaned_data
            
            # Lógica de ORM para filtros:
            if data['busqueda_nombre']:
                queryset = queryset.filter(
                    Q(nombre_elemento__icontains=data['busqueda_nombre']) | 
                    Q(simbolo_elemento__icontains=data['busqueda_nombre'])
                )
            if data['categoria']:
                queryset = queryset.filter(detalleelemento__categoria_elemento__exact=data['categoria'])
            if data['min_peso_atomico']:
                queryset = queryset.filter(peso_atomico_elemento__gte=data['min_peso_atomico'])
                
        return queryset.order_by('numero_atomico_elemento')

# R - READ (Detalle)
class ElementoDetailView(DetailView):
    model = ElementoQuimico
    template_name = 'app_quimico/elemento_quimico/elemento_detalle.html'
    context_object_name = 'elemento'
    
    def get_queryset(self):
        return ElementoQuimico.objects.select_related('detalleelemento').prefetch_related(
            'elementocompuesto_set__id_compuesto',
            'elementoaplicacion_set__id_aplicacion__id_industria'
        )

# U - UPDATE (Actualizar Elemento)
class ElementoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'app_quimico.change_elementoquimico'
    """Actualiza ElementoQuimico y DetalleElemento en una sola transacción."""
    template_name = 'app_quimico/elemento_quimico/elemento_form.html' 
    success_url = reverse_lazy('elemento_lista')

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk') 
        return ElementoQuimico.objects.select_related('detalleelemento').get(pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        elemento = self.get_object()
        
        if self.request.method == 'POST':
            context['elemento_form'] = ElementoQuimicoForm(self.request.POST, instance=elemento)
            context['detalle_form'] = DetalleElementoForm(self.request.POST, instance=elemento.detalleelemento)
        else:
            context['elemento_form'] = ElementoQuimicoForm(instance=elemento)
            context['detalle_form'] = DetalleElementoForm(instance=elemento.detalleelemento)
            
        return context

    def post(self, request, *args, **kwargs):
        elemento = self.get_object()
        
        elemento_form = ElementoQuimicoForm(request.POST, instance=elemento)
        detalle_form = DetalleElementoForm(request.POST, instance=elemento.detalleelemento)
        
        context = self.get_context_data() 

        if elemento_form.is_valid() and detalle_form.is_valid():
            try:
                with transaction.atomic():
                    elemento_form.save()
                    detalle_form.save()

                messages.success(request, f"Elemento '{elemento.simbolo_elemento}' y sus detalles han sido actualizados exitosamente.")
                return redirect(self.success_url)

            except Exception as e:
                messages.error(request, f"Ocurrió un error al guardar los datos: {e}")
                
        return self.render_to_response(context)


# D - DELETE (Eliminar Elemento)
class ElementoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'app_quimico.delete_elementoquimico'
    model = ElementoQuimico
    template_name = 'app_quimico/elemento_quimico/elemento_eliminar.html' 
    success_url = reverse_lazy('elemento_lista')

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        messages.success(request, f"El elemento '{obj.simbolo_elemento} - {obj.nombre_elemento}' ha sido eliminado exitosamente.")
        return redirect(self.success_url)


# ====================================================================== #
# CRUD para COMPUESTO QUÍMICO (Cálculo y Selección Única de Aplicación)  #
# Regla: CRUD solo para el dueño O Administrador (Control Personalizado) #
# ====================================================================== #

# C - CREATE (Crear Compuesto)
class CompuestoCreateView(LoginRequiredMixin, TemplateView):
    """
    Crea un compuesto, calcula el PM, registra una única CompuestoAplicacion,
    y asigna el usuario creador (dueño).
    """
    template_name = 'app_quimico/compuesto_quimico/compuesto_form.html' 
    success_url = reverse_lazy('compuesto_lista') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['compuesto_form'] = CompuestoQuimicoForm(self.request.POST)
            context['relacion_form'] = CompuestoAplicacionForm(self.request.POST)
        else:
            context['compuesto_form'] = CompuestoQuimicoForm()
            context['relacion_form'] = CompuestoAplicacionForm()
        return context

    def post(self, request, *args, **kwargs):
        compuesto_form = CompuestoQuimicoForm(request.POST)
        relacion_form = CompuestoAplicacionForm(request.POST)
        
        context = self.get_context_data() 

        if compuesto_form.is_valid() and relacion_form.is_valid():
            try:
                with transaction.atomic():
                    
                    compuesto_obj = compuesto_form.save(commit=False) 
                    formula = compuesto_obj.formula_compuesto
                    
                    # ASIGNACIÓN DE DUEÑO
                    compuesto_obj.usuario = self.request.user 
                    
                    # Recalculo y asignación del PM
                    calculadora = CalculadoraPM()
                    pm_float, elementos_conteo = calculadora.analizar_formula(formula)
                    peso_calculado = Decimal(str(pm_float)).quantize(Decimal('0.0001'))
                    compuesto_obj.peso_molecular_compuesto = peso_calculado
                    
                    # Asignar Industria obligatoria
                    aplicacion_seleccionada = relacion_form.cleaned_data['id_aplicacion']
                    compuesto_obj.id_industria = aplicacion_seleccionada.id_industria
                    
                    compuesto_obj.save() 

                    # Lógica para Aplicacion y Relación M:N
                    relacion_obj = relacion_form.save(commit=False)
                    relacion_obj.id_compuesto = compuesto_obj
                    relacion_obj.save()

                    # Guardado de ElementoCompuesto
                    simbolos = elementos_conteo.keys()
                    elementos_bd = ElementoQuimico.objects.filter(simbolo_elemento__in=simbolos)
                    elementos_map = {e.simbolo_elemento: e for e in elementos_bd}
                    
                    elementos_a_crear = [
                        ElementoCompuesto(
                            id_compuesto=compuesto_obj,
                            id_elemento=elementos_map.get(simbolo),
                            cantidad_elem_en_comp=cantidad
                        )
                        for simbolo, cantidad in elementos_conteo.items()
                        if elementos_map.get(simbolo) is not None
                    ]
                    ElementoCompuesto.objects.bulk_create(elementos_a_crear)

                messages.success(request, f"Compuesto '{formula}' registrado con éxito y aplicación asignada.")
                return redirect(self.success_url)

            except ValueError as e:
                messages.error(request, f"Error Ingreso Fórmula Compuesto Químico: {e}")
                return self.render_to_response(context) 
            except Exception as e:
                messages.error(request, f"Error interno: {e}")
                return self.render_to_response(context)
        
        # Manejo de fallo de validación
        if compuesto_form.errors or relacion_form.errors:
            first_error = next(iter(compuesto_form.errors.values()))[0] if compuesto_form.errors else next(iter(relacion_form.errors.values()))[0]
            messages.error(request, f"Error de validación: {first_error}")
        return self.render_to_response(context)


# R - READ (Lista Compuestos)
class CompuestoListView(LoginRequiredMixin, ListView):
    model = CompuestoQuimico
    template_name = 'app_quimico/compuesto_quimico/compuesto_lista.html' 
    context_object_name = 'compuestos'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aseguramos que el formulario esté en el contexto
        context['filter_form'] = CompuestoFilterForm(self.request.GET)
        return context
    
    def get_queryset(self):
        # 1. Base de la consulta y anotación (funciona)
        queryset = CompuestoQuimico.objects.prefetch_related(
            'compuestoaplicacion_set' 
        ).annotate(
            total_aplicaciones=Count('compuestoaplicacion')
        )
        
        # FIX: Lógica de permisos corregida para incluir a Colaboradores en la vista global.
        is_global_manager = self.request.user.groups.filter(
            name__in=['Administradores', 'Colaboradores']
        ).exists()
        
        # 2. Filtro por Dueño (Solo aplicamos el filtro personal si NO es un gestor global)
        if self.request.user.is_authenticated and not is_global_manager:
            # Resultado: Químicos (usuario estándar) son los únicos que llegan aquí.
            queryset = queryset.filter(usuario=self.request.user)
            
        # 3. Aplicación de Filtros GET (Búsqueda y Rango)
        form = CompuestoFilterForm(self.request.GET)
        
        if form.is_valid():
            data = form.cleaned_data
            
            # A. Búsqueda por Nombre/Fórmula (usando Q objects)
            if data['busqueda_compuesto']:
                queryset = queryset.filter(
                    Q(nombre_compuesto__icontains=data['busqueda_compuesto']) | 
                    Q(formula_compuesto__icontains=data['busqueda_compuesto'])
                )

            # B. Peso Molecular Mínimo (usando __gte)
            if data['min_peso_molecular']:
                queryset = queryset.filter(peso_molecular_compuesto__gte=data['min_peso_molecular'])
                
            # C. Filtro por Industria (Clave foránea indirecta)
            if data['industria']:
                # CRÍTICO: Usamos .pk para obtener el ID del objeto Industria seleccionado
                industria_id = data['industria'].pk 
                queryset = queryset.filter(
                    compuestoaplicacion__id_aplicacion__id_industria=industria_id
                ).distinct()
                
        # Ordenamos por nombre del compuesto
        return queryset.order_by('nombre_compuesto')

# R - READ (Detalle Compuesto)
class CompuestoDetailView(LoginRequiredMixin, DetailView):
    model = CompuestoQuimico
    template_name = 'app_quimico/compuesto_quimico/compuesto_detalle.html'
    context_object_name = 'compuesto'

    def get_queryset(self):
        return CompuestoQuimico.objects.prefetch_related(
            Prefetch('elementocompuesto_set', 
                    queryset=ElementoCompuesto.objects.select_related('id_elemento').order_by('id_elemento__numero_atomico_elemento')),
            Prefetch('compuestoaplicacion_set', 
                    queryset=CompuestoAplicacion.objects.select_related('id_aplicacion__id_industria'))
        )

# U - UPDATE (Actualizar Compuesto)
class CompuestoUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Permite actualizar un Compuesto Químico y su única CompuestoAplicacion relacionada.
    """
    template_name = 'app_quimico/compuesto_quimico/compuesto_form.html' 
    success_url = reverse_lazy('compuesto_lista')

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk') 
        return get_object_or_404(CompuestoQuimico, pk=pk)
    
    def test_func(self):
        compuesto = self.get_object()
        # CRÍTICO: Permitir si es dueño O si pertenece al grupo Administradores
        return compuesto.usuario == self.request.user or self.request.user.groups.filter(name='Administradores').exists()

    def get_compuesto_data(self):
        """Obtiene el compuesto principal y sus relaciones asociadas."""
        pk = self.kwargs.get('pk') 
        compuesto = get_object_or_404(CompuestoQuimico, pk=pk)
        
        try:
            relacion = get_object_or_404(CompuestoAplicacion.objects.select_related('id_aplicacion__id_industria'), id_compuesto=compuesto)
        except CompuestoAplicacion.DoesNotExist:
            relacion = None
        
        return compuesto, relacion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compuesto, relacion = self.get_compuesto_data()
        
        initial_relacion = {}
        if relacion and relacion.id_aplicacion and relacion.id_aplicacion.id_industria:
            initial_relacion['tipo_industria'] = relacion.id_aplicacion.id_industria
        
        if self.request.method == 'POST':
            context['compuesto_form'] = CompuestoQuimicoForm(self.request.POST, instance=compuesto)
            context['relacion_form'] = CompuestoAplicacionForm(self.request.POST, instance=relacion)
        else:
            context['compuesto_form'] = CompuestoQuimicoForm(instance=compuesto)
            context['relacion_form'] = CompuestoAplicacionForm(instance=relacion, initial=initial_relacion)
            
        return context

    def post(self, request, *args, **kwargs):
        compuesto, relacion = self.get_compuesto_data()
        
        formula_post_data = request.POST.get('formula_compuesto', 'FIELD_NOT_FOUND') 
        
        compuesto_form = CompuestoQuimicoForm(request.POST, instance=compuesto)
        relacion_form = CompuestoAplicacionForm(request.POST, instance=relacion)
        
        context = self.get_context_data() 

        if compuesto_form.is_valid() and relacion_form.is_valid():
            try:
                with transaction.atomic():
                    
                    compuesto_obj = compuesto_form.save(commit=False) 
                    
                    formula_original = compuesto.formula_compuesto
                    
                    debe_recalcular = (
                        formula_post_data != formula_original or
                        compuesto_obj.peso_molecular_compuesto is None or
                        compuesto_obj.peso_molecular_compuesto == 0
                    )
                    
                    if debe_recalcular:
                        compuesto_obj.formula_compuesto = formula_post_data 
                        
                        calculadora = CalculadoraPM()
                        pm_float, elementos_conteo = calculadora.analizar_formula(formula_post_data)
                        peso_calculado = Decimal(str(pm_float)).quantize(Decimal('0.0001'))
                        
                        compuesto_obj.peso_molecular_compuesto = peso_calculado
                        
                        ElementoCompuesto.objects.filter(id_compuesto=compuesto_obj).delete()
                        
                        simbolos = elementos_conteo.keys()
                        elementos_bd = ElementoQuimico.objects.filter(simbolo_elemento__in=simbolos)
                        elementos_map = {e.simbolo_elemento: e for e in elementos_bd}
                        
                        elementos_a_crear = [
                            ElementoCompuesto(
                                id_compuesto=compuesto_obj,
                                id_elemento=elementos_map.get(simbolo),
                                cantidad_elem_en_comp=cantidad
                            )
                            for simbolo, cantidad in elementos_conteo.items()
                            if elementos_map.get(simbolo) is not None
                        ]
                        ElementoCompuesto.objects.bulk_create(elementos_a_crear)

                    aplicacion_seleccionada = relacion_form.cleaned_data['id_aplicacion']
                    compuesto_obj.id_industria = aplicacion_seleccionada.id_industria

                    compuesto_obj.save() 

                    relacion_form.save() 

                messages.success(request, f"Compuesto '{compuesto_obj.formula_compuesto}' y su aplicación han sido actualizados exitosamente. PM final: {compuesto_obj.peso_molecular_compuesto}.")
                return redirect(self.success_url)

            except ValueError as e:
                messages.error(request, f"Error Ingreso Fórmula Compuesto Químico: {e}")
                return self.render_to_response(context) 
            except Exception as e:
                messages.error(request, f"Error interno: {e}")
                return self.render_to_response(context)
        
        return self.render_to_response(context)

# D - DELETE (Borrar Compuesto)
class CompuestoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CompuestoQuimico
    template_name = 'app_quimico/compuesto_quimico/compuesto_eliminar.html' 
    success_url = reverse_lazy('compuesto_lista')

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk') 
        return get_object_or_404(CompuestoQuimico, pk=pk)

    def test_func(self):
        compuesto = self.get_object()
        # CRÍTICO: Permitir si es dueño O si pertenece al grupo Administradores
        return compuesto.usuario == self.request.user or self.request.user.groups.filter(name='Administradores').exists()

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_name = f"{obj.nombre_compuesto} ({obj.formula_compuesto})"
        obj.delete()
        messages.success(request, f"El compuesto '{obj_name}' ha sido eliminado exitosamente.")
        return redirect(self.success_url)


# ================================= #
# CRUD para APLICACION (C, R, U, D) #
# ================================= #

# C - CREATE (Crear Aplicación)
class AplicacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'app_quimico.add_aplicacion'
    model = Aplicacion
    form_class = AplicacionForm
    template_name = 'app_quimico/aplicacion/aplicacion_form.html'
    success_url = reverse_lazy('aplicacion_lista')
    def form_valid(self, form):
        messages.success(self.request, f"Aplicación '{form.instance.nombre_uso}' registrada exitosamente.")
        return super().form_valid(form)

# R - READ (Lista Aplicaciones)
class AplicacionListView(LoginRequiredMixin, ListView):
    model = Aplicacion
    template_name = 'app_quimico/aplicacion/aplicacion_lista.html'
    context_object_name = 'aplicaciones'
    queryset = Aplicacion.objects.select_related('id_industria').all().order_by('id_industria__nombre_industria', 'nombre_uso')

# R - UPDATE (Actualizar Aplicación)
class AplicacionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'app_quimico.change_aplicacion'
    model = Aplicacion
    form_class = AplicacionForm
    template_name = 'app_quimico/aplicacion/aplicacion_form.html'
    success_url = reverse_lazy('aplicacion_lista')
    def form_valid(self, form):
        messages.success(self.request, f"Aplicación '{form.instance.nombre_uso}' actualizada exitosamente.")
        return super().form_valid(form)

# R - DELETE (Eliminar Aplicación)
class AplicacionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'app_quimico.delete_aplicacion'
    model = Aplicacion
    template_name = 'app_quimico/aplicacion/aplicacion_eliminar.html'
    success_url = reverse_lazy('aplicacion_lista')
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_name = obj.nombre_uso
        obj.delete()
        messages.success(request, f"La aplicación '{obj_name}' ha sido eliminada.")
        return redirect(self.success_url)