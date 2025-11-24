from django.urls import path
from django.contrib.auth import views as auth_views
from app_quimico.views import CustomLoginView, custom_logout_view, HomeView
from . import views 

urlpatterns = [

# ===================== #
# RUTA PRINCIPAL (HOME) #
# ===================== #

path('', views.HomeView.as_view(), name='home'),

# =================== #
# CRUD para INDUSTRIA #
# =================== #

# C - CREATE
path('industrias/crear/', views.IndustriaCreateView.as_view(), name='industria_crear'),

# R - READ (Lista)
path('industrias/', views.IndustriaListView.as_view(), name='industria_lista'),

# U - UPDATE
path('industrias/modificar/<int:pk>/', views.IndustriaUpdateView.as_view(), name='industria_actualizar'),

# D - DELETE (Borrar)
path('industrias/eliminar/<int:pk>/', views.IndustriaDeleteView.as_view(), name='industria_eliminar'),

# ============================ #
# CRUD para ELEMENTOS QUÍMICOS #
# ============================ #

# C - CREATE
path('elementos/crear/', views.ElementoCreateView.as_view(), name='elemento_crear'),

# R - READ (Lista)
path('elementos/', views.ElementoListView.as_view(), name='elemento_lista'),

# R - READ (Detalle)
path('elementos/<int:pk>/detalle/', views.ElementoDetailView.as_view(), name='elemento_detalle'),

# U - UPDATE
path('elementos/modificar/<int:pk>/', views.ElementoUpdateView.as_view(), name='elemento_actualizar'),

# D - DELETE
path('elementos/eliminar/<int:pk>/', views.ElementoDeleteView.as_view(), name='elemento_eliminar'),

# ============================= #
# CRUD para COMPUESTOS QUÍMICOS #
# ============================= #

# C - CREATE
path('compuestos/crear/', views.CompuestoCreateView.as_view(), name='compuesto_crear'),

# R - READ (Lista)
path('compuestos/', views.CompuestoListView.as_view(), name='compuesto_lista'),

# R - READ (Detalle)
path('compuestos/<int:pk>/detalle/', views.CompuestoDetailView.as_view(), name='compuesto_detalle'),

# U - UPDATE
path('compuestos/modificar/<int:pk>/', views.CompuestoUpdateView.as_view(), name='compuesto_actualizar'),

# D - DELETE
path('compuestos/eliminar/<int:pk>/', views.CompuestoDeleteView.as_view(), name='compuesto_eliminar'),

# ====================== #
# CRUD para APLICACIONES # 
# ====================== #

# C - CREATE
path('aplicaciones/crear/', views.AplicacionCreateView.as_view(), name='aplicacion_crear'),

# R - READ (Lista)
path('aplicaciones/', views.AplicacionListView.as_view(), name='aplicacion_lista'),

# U - UPDATE
path('aplicaciones/modificar/<int:pk>/', views.AplicacionUpdateView.as_view(), name='aplicacion_actualizar'),

# D - DELETE
path('aplicaciones/eliminar/<int:pk>/', views.AplicacionDeleteView.as_view(), name='aplicacion_eliminar'),

# ===================== #
# URLs de AUTENTICACIÓN #
# ===================== #

# REGISTRO
path('registro/', views.RegistroView.as_view(), name='registro'),

# LOGIN
path('login/', CustomLoginView.as_view(), name='login'),

# LOGOUT
path('logout/', custom_logout_view, name='logout'),

# PERFIL PERSONAL (Target de LOGIN_REDIRECT_URL)
path('perfil/', views.HomeView.as_view(template_name='app_quimico/autenticacion/perfil_personal.html'), name='perfil_personal'),

]