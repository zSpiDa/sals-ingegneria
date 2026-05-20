from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Utente, Mezzo, Area_Urbana, Corsa
from .serializers import UtenteSerializer, MezzoSerializer, AreaUrbanaSerializer, CorsaSerializer


class UtenteViewSet(viewsets.ModelViewSet):
    """
    Endpoint per gestire gli utenti del sistema di mobilità.
    Fornisce automaticamente GET, POST, PUT, DELETE.
    """
    queryset = Utente.objects.all()
    serializer_class = UtenteSerializer
    search_fields = ['nome', 'cognome', 'documento']


class MezzoViewSet(viewsets.ModelViewSet):
    """
    Endpoint per la gestione della flotta dei veicoli (Bici, Scooter, Auto).
    """
    serializer_class = MezzoSerializer
    search_fields = ['tipo']

    def get_queryset(self):
        """
        Filtra i mezzi: di default mostra solo quelli 'DISPONIBILE'.
        Se viene passato il parametro ?mostra_tutti=true mostra l'intera flotta.
        """
        queryset = Mezzo.objects.all()
        mostra_tutti = self.request.query_params.get('mostra_tutti', 'false').lower() == 'true'
        if mostra_tutti:
            return queryset
        return queryset.filter(stato='DISPONIBILE')

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
        """
        Azione personalizzata: POST /api/mezzi/{id}/prenota/
        Cambia lo stato del mezzo in PRENOTATO se era disponibile.
        """
        mezzo = self.get_object()
        if mezzo.stato != 'DISPONIBILE':
            return Response(
                {'error': f'Impossibile prenotare il mezzo: stato attuale {mezzo.stato}.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        mezzo.stato = 'PRENOTATO'
        mezzo.save()
        return Response({'status': 'Mezzo prenotato con successo per 15 minuti.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def mappa_flotta(self, request):
        """
        Azione personalizzata: GET /api/mezzi/mappa_flotta/
        Restituisce le coordinate di tutti i mezzi per la mappa dell'applicazione.
        """
        mezzi = Mezzo.objects.all()
        serializer = self.get_serializer(mezzi, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AreaUrbanaViewSet(viewsets.ModelViewSet):
    """
    Endpoint per la gestione delle geo-fencing (Aree Parcheggio, Cantieri, Zone Vietate).
    """
    queryset = Area_Urbana.objects.all()
    serializer_class = AreaUrbanaSerializer


class CorsaViewSet(viewsets.ModelViewSet):
    """
    Endpoint core per la gestione dei noleggi attivi e dello storico corse.
    """
    queryset = Corsa.objects.all().order_by('-inizio')
    serializer_class = CorsaSerializer

    @action(detail=False, methods=['post'])
    def avvia(self, request):
        """
        Azione personalizzata: POST /api/corse/avvia/
        Innesca la logica di business definita nel modello per iniziare un noleggio.
        Richiede un JSON: {"utente": id, "mezzo": id}
        """
        utente_id = request.data.get('utente')
        mezzo_id = request.data.get('mezzo')

        if not utente_id or not mezzo_id:
            return Response({'error': 'Fornire identificativi validi per utente e mezzo.'}, status=status.HTTP_400_BAD_REQUEST)

        utente = get_object_or_404(Utente, id=utente_id)
        mezzo = get_object_or_404(Mezzo, id=mezzo_id)

        try:
            # Richiama i vincoli e le validazioni scritte nei modelli
            corsa = Corsa.avvia_corsa(utente=utente, mezzo=mezzo)
            serializer = self.get_serializer(corsa)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def termina(self, request, pk=None):
        """
        Azione personalizzata: POST /api/corse/{id}/termina/
        Conclude la corsa calcolando il prezzo e aggiornando l'ultima posizione GPS del mezzo.
        Accetta opzionalmente nel body: {"latitudine": 41.12, "longitudine": 16.86}
        """
        corsa = self.get_object()
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        try:
            # Calcola tempo, tariffe e chiude il noleggio
            corsa.termina_corsa()
            
            # Se l'app mobile invia le nuove coordinate di rilascio, aggiorna il veicolo
            if lat and lng:
                corsa.mezzo.latitudine = float(lat)
                corsa.mezzo.longitudine = float(lng)
                corsa.mezzo.save()

            serializer = self.get_serializer(corsa)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def costo_corrente(self, request, pk=None):
        """
        Azione personalizzata: GET /api/corse/{id}/costo_corrente/
        Fornisce una stima del costo in Euro accumulato fino al secondo corrente.
        Utile per l'applicazione mobile durante la corsa.
        """
        corsa = self.get_object()
        if corsa.fine:
            return Response({'costo_totale': corsa.costo_totale, 'stato': 'conclusa'}, status=status.HTTP_200_OK)

        # Calcola la durata parziale
        durata_secondi = (timezone.now() - corsa.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)

        # Applica lo specchietto tariffe del Product Backlog
        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
        tariffa_applicata = tariffe.get(corsa.mezzo.tipo, 0.20)
        costo_attuale = round(durata_minuti * tariffa_applicata, 2)

        return Response({
            'corsa_id': corsa.id,
            'minuti_trascorsi': int(durata_minuti),
            'costo_stimato_corrente': costo_attuale
        }, status=status.HTTP_200_OK)