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
    Gestione Utenti - Supporta l'associazione dei metodi di pagamento (IF-U13).
    """
    queryset = Utente.objects.all()
    serializer_class = UtenteSerializer
    search_fields = ['nome', 'cognome', 'documento']


class MezzoViewSet(viewsets.ModelViewSet):
    """
    Gestione Parco Mezzi - Soddisfa la ricerca (IF-U01), visualizzazione batteria (IF-U11),
    la prenotazione (IF-U02) e il monitoraggio logistico della flotta (IF-O02).
    """
    serializer_class = MezzoSerializer

    def get_queryset(self):
        """
        [IF-U01] Di base mostra solo i mezzi disponibili all'utente sulla mappa.
        Esclude i veicoli in uso, prenotati o in manutenzione.
        """
        queryset = Mezzo.objects.all()
        # Se richiesto esplicitamente dal pannello operatore, mostra l'intera flotta
        mostra_tutti = self.request.query_params.get('mostra_tutti', 'false').lower() == 'true'
        if mostra_tutti:
            return queryset
        return queryset.filter(stato='DISPONIBILE')

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
        """
        [IF-U02] Endpoint per prenotare un mezzo specifico per un massimo di 15 minuti.
        Invocazione: POST /api/mezzi/{id}/prenota/
        """
        mezzo = self.get_object()
        if mezzo.stato != 'DISPONIBILE':
            return Response(
                {'error': f'Impossibile prenotare: il mezzo è in stato {mezzo.stato}.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Modifica lo stato del mezzo per bloccarlo temporaneamente agli altri utenti
        mezzo.stato = 'PRENOTATO'
        mezzo.save()
        
        return Response(
            {'status': 'Mezzo prenotato con successo. Hai 15 minuti di tempo per sbloccarlo.'}, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def mappa_flotta(self, request):
        """
        [IF-O02] Console Operatore: Restituisce la distribuzione geografica di tutta la flotta.
        Invocazione: GET /api/mezzi/mappa_flotta/
        """
        mezzi = Mezzo.objects.all()
        serializer = self.get_serializer(mezzi, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AreaUrbanaViewSet(viewsets.ModelViewSet):
    """
    Gestione Aree Urbane.
    """
    queryset = Area_Urbana.objects.all()
    serializer_class = AreaUrbanaSerializer


class CorsaViewSet(viewsets.ModelViewSet):
    """
    Gestione Ciclo Corsa - Gestisce l'avvio tramite scansione/sblocco (IF-U12),
    la chiusura con rilevamento posizione (IF-U05, IF-O04) e il monitoraggio dei costi (IF-U03, IF-U04).
    """
    queryset = Corsa.objects.all().order_by('-inizio')
    serializer_class = CorsaSerializer

    @action(detail=False, methods=['post'])
    def avvia(self, request):
        """
        [IF-U12] Avvia il noleggio tramite sblocco app (Payload: {"utente": id, "mezzo": id}).
        Invocazione: POST /api/corse/avvia/
        """
        utente_id = request.data.get('utente')
        mezzo_id = request.data.get('mezzo')

        if not utente_id or not mezzo_id:
            return Response({'error': 'Dati incompleti per l\'avvio.'}, status=status.HTTP_400_BAD_REQUEST)

        utente = get_object_or_404(Utente, id=utente_id)
        mezzo = get_object_or_404(Mezzo, id=mezzo_id)

        try:
            corsa = Corsa.avvia_corsa(utente=utente, mezzo=mezzo)
            serializer = self.get_serializer(corsa)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def termina(self, request, pk=None):
        """
        [IF-U05 / IF-O04] Termina il noleggio corrente aggiornando la posizione GPS finale inviata dal mezzo.
        Invocazione: POST /api/corse/{id}/termina/
        Payload opzionale: {"latitudine": 41.123, "longitudine": 16.456}
        """
        corsa = self.get_object()
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        try:
            # Esegue i calcoli finanziari di chiusura definiti nel modello
            corsa.termina_corsa()
            
            # Se il frontend passa la posizione di chiusura del mezzo, aggiorna la telemetria del veicolo
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
        [IF-U04] Calcola e restituisce il costo accumulato in tempo reale ogni 60 secondi durante il tragitto.
        Invocazione: GET /api/corse/{id}/costo_corrente/
        """
        corsa = self.get_object()
        if corsa.fine:
            return Response({'costo_totale': corsa.costo_totale, 'stato': 'conclusa'})

        # Calcolo dinamico temporaneo della durata
        durata_secondi = (timezone.now() - corsa.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0) # Almeno 1 minuto di conteggio minimo

        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
        tariffa_applicata = tariffe.get(corsa.mezzo.tipo, 0.20)
        costo_attuale = round(durata_minuti * tariffa_applied, 2)

        return Response({
            'corsa_id': corsa.id,
            'minuti_trascorsi': int(durata_minuti),
            'costo_stimato_corrente': costo_attuale
        }, status=status.HTTP_200_OK)