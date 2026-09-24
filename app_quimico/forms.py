from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Fieldset, Row, Column
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.models import User
from .models import (
    ElementoQuimico, DetalleElemento, Industria, 
    CompuestoQuimico, Aplicacion, CompuestoAplicacion, 
    ElementoCompuesto, ElementoAplicacion,
    CATEGORIA_CHOICES
)
from decimal import Decimal

from pysmiles import read_smiles


# User-facing message shared by every SMILES validation failure.
SMILES_ERROR = (
    "La notación SMILES no es válida. Ejemplo válido: CCO (etanol)."
)


# ================ #
# Elemento Químico #
# ================ #
class ElementoQuimicoForm(forms.ModelForm):
    class Meta:
        model = ElementoQuimico
        fields = '__all__'
        
        widgets = {
            'peso_atomico_elemento': forms.NumberInput(attrs={
                'placeholder': 'g/mol'
            }),
            'simbolo_elemento': forms.TextInput(attrs={
                'placeholder': 'Ej: Na, Cl o Se'
            }),
            'nombre_elemento': forms.TextInput(attrs={
                'placeholder': 'Ej: Sodio, Cloro o Selenio'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()


# ===================== #
# Detalles del Elemento #
# ===================== #
class DetalleElementoForm(forms.ModelForm):
    class Meta:
        model = DetalleElemento
        exclude = ('id_elemento',) 
        
        widgets = {
            'electronegatividad': forms.NumberInput(attrs={
                'placeholder': 'Escala Pauling'
            }),
            'afinidad_electronica': forms.NumberInput(attrs={
                'placeholder': 'kJ/mol'
            }),
            'energia_de_ionizacion': forms.NumberInput(attrs={
                'placeholder': 'kJ/mol'
            }),
            'radio_covalente': forms.NumberInput(attrs={
                'placeholder': 'Å (Angstroms)'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()


# ========= #
# Industria #
# ========= #
class IndustriaForm(forms.ModelForm):
    class Meta:
        model = Industria
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nombre_industria',
            Submit('submit', 'Guardar Industria', css_class='btn-primary')
        )


# ========== #
# Aplicación #
# ========== #
class AplicacionForm(forms.ModelForm):
    class Meta:
        model = Aplicacion
        fields = '__all__'
        widgets = {
            'id_industria': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['id_industria'].label = "Industria Principal" 


# ================= #
# Compuesto Químico #
# ================= #
class CompuestoQuimicoForm(forms.ModelForm):
    class Meta:
        model = CompuestoQuimico
        # PM incluido para persistencia
        fields = ['nombre_compuesto', 'formula_compuesto', 'smiles']
        widgets = {
            'formula_compuesto': forms.TextInput(attrs={
                'placeholder': 'Ej: H2O, Ca(OH)2 o [Co(NH3)6]Cl3',
                'class': 'form-control', 
                'readonly': False, 
                'disabled': False,
            }),
            'smiles': forms.TextInput(attrs={
                'placeholder': 'Ej.: CCO (etanol)',
                'class': 'form-control',
            }),
            'peso_molecular_compuesto': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Fieldset(
                'Datos del Compuesto',
                'nombre_compuesto', 
                'formula_compuesto', 
                'smiles',
            ),
        )

    def clean_smiles(self):
        """Validate the optional SMILES notation.

        Empty input is a valid opt-out (the diagram is simply not rendered) and
        is normalized to ``None`` so the DB stores NULL instead of an empty
        string. A non-empty value is parsed with pysmiles; malformed notation
        raises a user-facing Spanish error. Internal whitespace is rejected
        explicitly because pysmiles parses ``"C C"`` as two disconnected atoms
        instead of failing.
        """
        value = self.cleaned_data.get('smiles')
        if value is None:
            return None

        value = value.strip()
        if not value:
            return None

        if any(char.isspace() for char in value):
            raise forms.ValidationError(SMILES_ERROR)

        try:
            read_smiles(value)
        except Exception:
            raise forms.ValidationError(SMILES_ERROR)

        return value


# ======================================= #
# Tablas Intermedias (Para Detail/Update) #
# ======================================= #
class ElementoCompuestoForm(forms.ModelForm):
    class Meta:
        model = ElementoCompuesto
        fields = ['id_elemento', 'cantidad_elem_en_comp']

class ElementoAplicacionForm(forms.ModelForm):
    class Meta:
        model = ElementoAplicacion
        fields = ['id_elemento', 'id_aplicacion', 'notas_uso']


# ==================== #
# Compuesto Aplicacion #
# ==================== #
class CompuestoAplicacionForm(forms.ModelForm):
    
    # CAMPO 1: Tipo Industria (requerido=True por defecto)
    tipo_industria = forms.ModelChoiceField(
        queryset=Industria.objects.all().order_by('nombre_industria'),
        label="Tipo Industria",
        empty_label="--- Seleccione una Industria ---"
    )
    
    # CAMPO 2: id_aplicacion (requerido=True por defecto)
    id_aplicacion = forms.ModelChoiceField(
        queryset=Aplicacion.objects.all().order_by('nombre_uso'),
        label="Uso/Aplicación",
        empty_label="--- Seleccione una Aplicación ---"
    )

    class Meta:
        model = CompuestoAplicacion
        fields = ['id_aplicacion', 'concentracion_minima', 'tipo_concentracion'] 

        widgets = {
            'concentracion_minima': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['concentracion_minima'].label = "Concentración Mínima Uso" 

    def clean(self):
        cleaned_data = super().clean()
        industria = cleaned_data.get('tipo_industria')
        aplicacion = cleaned_data.get('id_aplicacion')
        if industria and aplicacion and aplicacion.id_industria_id != industria.pk:
            raise forms.ValidationError("La aplicación seleccionada no pertenece a la industria indicada")
        return cleaned_data


# ==================================== #
# FORMULARIO DE FILTROS PARA ELEMENTOS #
# ==================================== #
class ElementoFilterForm(forms.Form):
    # 1. Búsqueda por Nombre/Símbolo (usando __icontains)
    busqueda_nombre = forms.CharField(
        required=False, 
        label="Buscar por Nombre/Símbolo",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Sodio, Cloro', 'class': 'form-control'})
    )
    
    # 2. Por Categoría (Dropdown)
    categoria = forms.ChoiceField(
        required=False, 
        label="Por Categoría",
        choices=[('', '--- Todas las Categorías ---')] + CATEGORIA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # 3. Peso Atómico Mínimo (Mayor o Igual que)
    min_peso_atomico = forms.DecimalField(
        required=False, 
        label="Peso Atómico ≥",
        min_value=0.01,
        widget=forms.NumberInput(attrs={'placeholder': 'Ej: 50.00', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('busqueda_nombre', css_class='form-group col-md-4 mb-0'),
                Column('categoria', css_class='form-group col-md-4 mb-0'),
                Column('min_peso_atomico', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            )
        )

# ===================================== #
# FORMULARIO DE FILTROS PARA COMPUESTOS #
# ===================================== #

class CompuestoFilterForm(forms.Form):
    # 1. Búsqueda por Nombre/Fórmula (usando __icontains)
    busqueda_compuesto = forms.CharField(
        required=False, 
        label="Nombre / Fórmula",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Ácido, Sal, H2O', 'class': 'form-control'})
    )
    
    # 2. Peso Molecular Mínimo (≥) (usando __gte)
    min_peso_molecular = forms.DecimalField(
        required=False, 
        label="PM Mínimo (≥)",
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'placeholder': 'Ej: 50.00', 'class': 'form-control', 'step': '0.01'})
    )
    
    # 3. Filtro por Industria (Selección por FK)
    industria = forms.ModelChoiceField(
        queryset=Industria.objects.all().order_by('nombre_industria'),
        required=False, 
        label="Filtrar por Industria",
        empty_label="--- Mostrar Todas las Industrias ---",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('busqueda_compuesto', css_class='form-group col-md-4 mb-0'),
                Column('min_peso_molecular', css_class='form-group col-md-4 mb-0'),
                Column('industria', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            )
        )


# ====================== #
# FORMULARIO DE REGISTRO #
# ====================== #
class RegistroForm(UserCreationForm):
    """Formulario customizado para el registro de nuevos usuarios."""
    
    # Django's User.email is not unique at the DB level; the registration flow
    # enforces it here (case-insensitive) to prevent ambiguous accounts.
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        # Exponemos solo los campos necesarios para crear la cuenta
        fields = ('username', 'email', 'first_name', 'last_name') 
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = 'tu@correo.com'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Datos de Registro',
                'username',
                'email',
                Row(
                    Column('first_name', css_class='form-group col-md-6 mb-0'),
                    Column('last_name', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Submit('submit', 'Crear Cuenta', css_class='btn-success') 
        )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo electrónico."
            )
        return email