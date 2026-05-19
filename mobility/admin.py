from django.contrib import admin
from .models import Utente, Mezzo, Area_Urbana, Corsa

@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    # Quali colonne mostrare nella tabella
    list_display = ('nome', 'cognome', 'documento', 'patente_verificata', 'sospensione', 'metodo_pagamento')
    # Barra di ricerca: in quali campi cercare quando scrivi qualcosa
    search_fields = ('nome', 'cognome', 'documento')
    # Filtri laterali: crea un menu a tendina a destra per filtrare velocemente
    list_filter = ('patente_verificata', 'sospensione', 'metodo_pagamento')

@admin.register(Mezzo)
class MezzoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'stato', 'batteria', 'latitudine', 'longitudine')
    search_fields = ('id', 'tipo')
    list_filter = ('tipo', 'stato')
    # Extra: Ordina i mezzi dal più scarico al più carico per la manutenzione
    ordering = ('batteria',) 

@admin.register(Area_Urbana)
class AreaUrbanaAdmin(admin.ModelAdmin):
    list_display = ('nome_zona', 'tipologia')
    search_fields = ('nome_zona',)
    list_filter = ('tipologia',)

@admin.register(Corsa)
class CorsaAdmin(admin.ModelAdmin):
    list_display = ('id', 'utente', 'mezzo', 'inizio', 'fine', 'costo_totale')
    # Il doppio underscore __ permette di cercare nei campi delle Foreign Key (es. cerca il cognome dell'utente della corsa)
    search_fields = ('utente__cognome', 'utente__documento', 'mezzo__id')
    # Filtra per data e per tipo di mezzo usato
    list_filter = ('inizio', 'mezzo__tipo')