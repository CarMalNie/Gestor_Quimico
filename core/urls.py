from django.contrib import admin
from django.urls import path, include
from app_quimico.views import error_404_handler, error_403_handler
from django.conf import settings            # Necesario para manejar los archivos estáticos en desarrollo/simulación producción
from django.conf.urls.static import static  # Necesario para manejar los archivos estáticos en desarrollo/simulación producción

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_quimico.urls'))
]

# Handler personalizado para el error 403. 
# Muestra la falta de permisos al intentar realizar una acción no autorizada
handler403 = error_403_handler

# Handler personalizado para el error 404. 
# Solo se activa automáticamente cuando DEBUG = False (entorno de producción)
handler404 = error_404_handler

# Bloque condicional para usar los archivos estáticos en el entorno de producción simulado/local (DEBUG=False)
if settings.DEBUG: 
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)