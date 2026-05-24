import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from .models import Utente, Mezzo, Area_Urbana, Corsa, Segnalazione, PosizioneGPS
from .serializers import UtenteSerializer, MezzoSerializer, AreaUrbanaSerializer, CorsaSerializer, SegnalazioneSerializer


class UtenteViewSet(viewsets.ModelViewSet):
    queryset = Utente.objects.all()
    serializer_class = UtenteSerializer
    search_fields = ['nome', 'cognome', 'documento']
    @action(detail=True, methods=['post'])
    def aggiorna_metodo_pagamento(self, request, pk=None):
        """
        IF-U13: Permette all'utente di salvare un nuovo metodo di pagamento nel profilo.
        """
        utente = self.get_object()
        nuovo_metodo = request.data.get('metodo_pagamento')
        
        # Recupera la lista dei metodi validi direttamente dal modello
        metodi_validi = [m[0] for m in Utente.METODI_PAGAMENTO]
        
        if nuovo_metodo not in metodi_validi:
            return Response(
                {'error': f'Metodo non valido. Scegli tra: {metodi_validi}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        utente.metodo_pagamento = nuovo_metodo
        utente.save()
        
        return Response(
            {'status': f'Metodo di pagamento salvato con successo: {nuovo_metodo}'}, 
            status=status.HTTP_200_OK
        )


class MezzoViewSet(viewsets.ModelViewSet):
    serializer_class = MezzoSerializer
    search_fields = ['tipo']

    def get_queryset(self):
        queryset = Mezzo.objects.all()
        mostra_tutti = self.request.query_params.get('mostra_tutti', 'false').lower() == 'true'
        if mostra_tutti:
            return queryset
        return queryset.filter(stato='DISPONIBILE')

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
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
        mezzi = Mezzo.objects.all()
        serializer = self.get_serializer(mezzi, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AreaUrbanaViewSet(viewsets.ModelViewSet):
    queryset = Area_Urbana.objects.all()
    serializer_class = AreaUrbanaSerializer


class SegnalazioneViewSet(viewsets.ModelViewSet):
    queryset = Segnalazione.objects.all().order_by('-data_segnalazione')
    serializer_class = SegnalazioneSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Segnalazione ricevuta. Il mezzo è in manutenzione."},
            status=status.HTTP_201_CREATED
        )


class CorsaViewSet(viewsets.ModelViewSet):
    queryset = Corsa.objects.all().order_by('-inizio')
    serializer_class = CorsaSerializer

    @action(detail=False, methods=['post'])
    def avvia(self, request):
        utente_id = request.data.get('utente')
        mezzo_id = request.data.get('mezzo')
        codice_inserito = request.data.get('codice_sblocco')

        if not utente_id or not mezzo_id:
            return Response({'error': 'Fornire identificativi validi per utente e mezzo.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.shortcuts import get_object_or_404
        utente = get_object_or_404(Utente, id=utente_id)
        mezzo = get_object_or_404(Mezzo, id=mezzo_id)

        # Controllo robusto del codice (rimuove spazi invisibili accidentali)
        codice_reale = str(mezzo.codice_sblocco).strip() if mezzo.codice_sblocco else ""
        codice_inviato = str(codice_inserito).strip() if codice_inserito else ""

        if not codice_reale:
            return Response({'error': 'Questo veicolo non ha un codice configurato nel database.'}, status=status.HTTP_400_BAD_REQUEST)

        if codice_inviato != codice_reale:
            return Response({'error': 'Codice di sblocco errato! Riprova.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            corsa = Corsa.avvia_corsa(utente=utente, mezzo=mezzo)
            return Response({'status': 'Corsa avviata', 'id': corsa.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Cattura in modo sicuro qualsiasi errore interno (es. geofencing, mezzo in uso, ecc.)
            error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def termina(self, request, pk=None):
        corsa = self.get_object()
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        try:
            corsa.termina_corsa(lat_rilascio=lat, lng_rilascio=lng)
            serializer = self.get_serializer(corsa)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def blocco_temporaneo(self, request, pk=None):
        corsa = self.get_object()
        if corsa.fine:
            return Response({'error': 'La corsa è già terminata.'}, status=status.HTTP_400_BAD_REQUEST)
        
        corsa.mezzo.stato = 'PRENOTATO' 
        corsa.mezzo.save()
        return Response({'status': 'Pausa attiva. Tariffazione in corso.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def sblocco_temporaneo(self, request, pk=None):
        corsa = self.get_object()
        if corsa.mezzo.stato == 'PRENOTATO' and not corsa.fine:
            corsa.mezzo.stato = 'IN_USO'
            corsa.mezzo.save()
            return Response({'status': 'Mezzo sbloccato. Puoi ripartire.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Azione non valida.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def costo_corrente(self, request, pk=None):
        corsa = self.get_object()
        if corsa.fine:
            return Response({'costo_totale': corsa.costo_totale, 'stato': 'conclusa'}, status=status.HTTP_200_OK)

        durata_secondi = (timezone.now() - corsa.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)

        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
        tariffa_applicata = tariffe.get(corsa.mezzo.tipo, 0.20)
        costo_attuale = round(durata_minuti * tariffa_applicata, 2)

        return Response({
            'corsa_id': corsa.id,
            'minuti_trascorsi': int(durata_minuti),
            'costo_stimato_corrente': costo_attuale
        }, status=status.HTTP_200_OK)

    # ==========================================
    # NUOVE FUNZIONI AGGIUNTE (PUNTO 3)
    # ==========================================
    
    @action(detail=False, methods=['post'])
    def stima_preventiva(self, request):
        """
        IF-U03: Calcola preventivo in base a punto A, punto B e tipo di mezzo.
        """
        lat_a = float(request.data.get('lat_partenza', 0))
        lng_a = float(request.data.get('lng_partenza', 0))
        lat_b = float(request.data.get('lat_destinazione', 0))
        lng_b = float(request.data.get('lng_destinazione', 0))
        tipo_mezzo = request.data.get('tipo_mezzo', 'SCOOTER').upper()

        if not all([lat_a, lng_a, lat_b, lng_b]):
            return Response({'error': 'Coordinate di partenza e destinazione obbligatorie.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calcolo distanza (Haversine approssimato)
        dy = (lat_b - lat_a) * 111000
        dx = (lng_b - lng_a) * 80000
        distanza_metri = math.sqrt(dx**2 + dy**2)
        distanza_km = distanza_metri / 1000.0

        # Velocità medie stimate in città (km/h)
        velocita = {'BICI': 12.0, 'SCOOTER': 15.0, 'AUTO': 25.0}
        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}

        vel_media = velocita.get(tipo_mezzo, 15.0)
        tariffa = tariffe.get(tipo_mezzo, 0.20)

        # Calcolo tempo (in minuti) e costo
        tempo_ore = distanza_km / vel_media
        tempo_minuti = max(tempo_ore * 60.0, 1.0) # minimo 1 minuto
        costo_stimato = round(tempo_minuti * tariffa, 2)

        return Response({
            'distanza_km': round(distanza_km, 2),
            'tempo_stimato_minuti': int(tempo_minuti),
            'costo_stimato': costo_stimato,
            'mezzo_scelto': tipo_mezzo
        }, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'])
    def aggiorna_posizione_gps(self, request, pk=None):
        """
        IF-O04: Endpoint che il sensore hardware chiama ogni 10 secondi per inviare la posizione attuale.
        """
        corsa = self.get_object()
        if corsa.fine:
            return Response({'error': 'Corsa terminata. Impossibile tracciare.'}, status=status.HTTP_400_BAD_REQUEST)

        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        if lat is None or lng is None:
            return Response({'error': 'Latitudine e longitudine mancanti.'}, status=status.HTTP_400_BAD_REQUEST)

        PosizioneGPS.objects.create(
            corsa=corsa,
            latitudine=float(lat),
            longitudine=float(lng)
        )

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
        mezzo = self.get_object()
        if mezzo.stato != 'DISPONIBILE':
            return Response({'error': 'Mezzo non disponibile.'}, status=status.HTTP_400_BAD_REQUEST)
        
        mezzo.stato = 'PRENOTATO'
        mezzo.scadenza_prenotazione = timezone.now() + timedelta(minutes=15)
        mezzo.save()
        return Response({'status': 'Mezzo prenotato per 15 minuti.'}, status=status.HTTP_200_OK)

        return Response({'status': 'Posizione registrata.'}, status=status.HTTP_201_CREATED)