from django.urls import path
from django.contrib.auth import views as auth_views
from app_quimico.views import CustomLoginView, custom_logout_view, HomeView
from app_quimico import mfa_views
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

# ========================================== #
# URLs de VERIFICACIÓN EN DOS PASOS (MFA)    #
# ========================================== #
# django-otp: inscripción opcional (setup) y segundo paso del login (verify).

# 1) Inscripción: QR + confirmación del primer código.
path('accounts/mfa/setup/', mfa_views.mfa_setup, name='mfa_setup'),

# 2) Segundo paso: código del dispositivo ya confirmado.
path('accounts/mfa/verify/', mfa_views.mfa_verify, name='mfa_verify'),

# ===================================== #
# URLs de RECUPERACIÓN DE CONTRASEÑA    #
# ===================================== #
# Vistas nativas de django.contrib.auth. Los nombres de ruta se mantienen
# canónicos (password_reset*) porque los success_url por defecto de las vistas
# dependen de ellos; cada ruta apunta a las plantillas propias de la app.

# 1) Solicitud: formulario con el correo para enviar el enlace.
path(
    'accounts/password_reset/',
    auth_views.PasswordResetView.as_view(
        template_name='app_quimico/autenticacion/password_reset_form.html',
        email_template_name='app_quimico/autenticacion/password_reset_email.html',
        subject_template_name='app_quimico/autenticacion/password_reset_subject.txt',
    ),
    name='password_reset',
),

# 2) Confirmación de envío (sin revelar si el correo existe).
path(
    'accounts/password_reset/done/',
    auth_views.PasswordResetDoneView.as_view(
        template_name='app_quimico/autenticacion/password_reset_done.html',
    ),
    name='password_reset_done',
),

# 3) Enlace del correo: definir la nueva contraseña (uidb64 + token).
path(
    'accounts/reset/<uidb64>/<token>/',
    auth_views.PasswordResetConfirmView.as_view(
        template_name='app_quimico/autenticacion/password_reset_confirm.html',
    ),
    name='password_reset_confirm',
),

# 4) Cambio completado.
path(
    'accounts/reset/done/',
    auth_views.PasswordResetCompleteView.as_view(
        template_name='app_quimico/autenticacion/password_reset_complete.html',
    ),
    name='password_reset_complete',
),

# =============================================== #
# URLs de CAMBIO DE CONTRASEÑA (usuario con sesión) #
# =============================================== #
# Vistas nativas de django.contrib.auth. PasswordChangeView incluye el check
# de la contraseña actual, aplica AUTH_PASSWORD_VALIDATORS y rota el hash con
# update_session_auth_hash (la sesión sobrevive al cambio). Tanto esta vista
# como la de confirmación aplican login_required en su dispatch.
# El nombre `password_change_done` es obligatorio: es el success_url por
# defecto de PasswordChangeView.

# 1) Formulario: contraseña actual + nueva + confirmación.
path(
    'accounts/password-change/',
    auth_views.PasswordChangeView.as_view(
        template_name='app_quimico/autenticacion/password_change_form.html',
    ),
    name='password_change',
),

# 2) Cambio completado (también requiere sesión activa).
path(
    'accounts/password-change/done/',
    auth_views.PasswordChangeDoneView.as_view(
        template_name='app_quimico/autenticacion/password_change_done.html',
    ),
    name='password_change_done',
),

# PERFIL PERSONAL (Target de LOGIN_REDIRECT_URL)
path('perfil/', views.HomeView.as_view(template_name='app_quimico/autenticacion/perfil_personal.html'), name='perfil_personal'),

]