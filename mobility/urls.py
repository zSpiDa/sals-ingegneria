from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UtenteViewSet, MezzoViewSet, AreaUrbanaViewSet, CorsaViewSet,
    SegnalazioneViewSet, PromozioneViewSet,
    AnalyticsCO2View, AnalyticsUtilizzoView, AnalyticsReportView,
    OperatoreAllerteView, OperatoreConsoleView,
<<<<<<< HEAD
    RoutingView, MeteoView, ChatTicketViewSet,
=======
    RoutingView, MeteoSuggerimentoView, ChatTicketViewSet, MeteoView,
>>>>>>> 9dc3e03df850fd3a51e04c79251c5135f55cc619
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
<<<<<<< HEAD
    path('meteo/suggerimento/', MeteoView.as_view(), name='meteo-suggerimento'),
=======
    path('meteo/suggerimento/', MeteoSuggerimentoView.as_view(), name='meteo-suggerimento'),
    
>>>>>>> 9dc3e03df850fd3a51e04c79251c5135f55cc619
]