from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UtenteViewSet, MezzoViewSet, AreaUrbanaViewSet, CorsaViewSet, SegnalazioneViewSet

router = DefaultRouter()
router.register(r'utenti', UtenteViewSet, basename='utente')
router.register(r'mezzi', MezzoViewSet, basename='mezzo')
router.register(r'aree-urbane', AreaUrbanaViewSet, basename='area_urbana')
router.register(r'corse', CorsaViewSet, basename='corsa')
router.register(r'segnalazioni', SegnalazioneViewSet, basename='segnalazione')

urlpatterns = [
    path('', include(router.urls)),
]