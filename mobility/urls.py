from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UtenteViewSet, MezzoViewSet, AreaUrbanaViewSet, CorsaViewSet,
    SegnalazioneViewSet, PromozioneViewSet,
    AnalyticsCO2View, AnalyticsUtilizzoView, AnalyticsReportView,
    OperatoreAllerteView, OperatoreConsoleView,
    RoutingView, MeteoSuggerimentoView, ChatTicketViewSet,
)

router = DefaultRouter()
router.register(r'utenti', UtenteViewSet, basename='utente')
router.register(r'mezzi', MezzoViewSet, basename='mezzo')
router.register(r'aree-urbane', AreaUrbanaViewSet, basename='area_urbana')
router.register(r'corse', CorsaViewSet, basename='corsa')
router.register(r'segnalazioni', SegnalazioneViewSet, basename='segnalazione')
router.register(r'promozioni', PromozioneViewSet, basename='promozione')
router.register(r'chat', ChatTicketViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
    # Blocco 2 - Analytics & Amministrazione
    path('analytics/co2/', AnalyticsCO2View.as_view(), name='analytics-co2'),
    path('analytics/utilizzo/', AnalyticsUtilizzoView.as_view(), name='analytics-utilizzo'),
    path('analytics/report/', AnalyticsReportView.as_view(), name='analytics-report'),
    # Blocco 2 - Console Operatore
    path('operatore/allerte/', OperatoreAllerteView.as_view(), name='operatore-allerte'),
    path('operatore/console/', OperatoreConsoleView.as_view(), name='operatore-console'),
    # Blocco 3 - Routing & Meteo
    path('routing/percorso/', RoutingView.as_view(), name='routing-percorso'),
    path('meteo/suggerimento/', MeteoSuggerimentoView.as_view(), name='meteo-suggerimento'),
]