from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, UtenteViewSet, MezzoViewSet, AreaUrbanaViewSet, CorsaViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'utenti', UtenteViewSet, basename='utente')
router.register(r'mezzi', MezzoViewSet, basename='mezzo')
router.register(r'aree-urbane', AreaUrbanaViewSet, basename='area_urbana')
router.register(r'corse', CorsaViewSet, basename='corsa')

urlpatterns = [
    path('', include(router.urls)),
]