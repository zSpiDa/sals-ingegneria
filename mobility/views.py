from django.contrib.auth.models import User
import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta

from .models import Utente, Mezzo, Area_Urbana, Corsa, Segnalazione, PosizioneGPS, Promozione, ChatTicket
from .serializers import UtenteSerializer, MezzoSerializer, AreaUrbanaSerializer, CorsaSerializer, SegnalazioneSerializer, PromozioneSerializer, ChatTicketSerializer
from .services import RoutingService, MeteoService, GatewayPagamento

# IF-A04: coefficiente medio di emissione di un'auto privata a benzina (kg di CO2 per km)
CO2_AUTO_KG_PER_KM = 0.120


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

    @action(detail=True, methods=['post'])
    def sospendi(self, request, pk=None):
        """IF-O08: sospende l'account utente (vandalismo o pagamenti insoluti)."""
        utente = self.get_object()
        utente.sospensione = True
        utente.save()
        motivo = request.data.get('motivo', 'non specificato')
        return Response(
            {'status': f'Utente {utente.nome} {utente.cognome} sospeso. Motivo: {motivo}.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def riattiva(self, request, pk=None):
        """IF-O08: riattiva un account precedentemente sospeso."""
        utente = self.get_object()
        utente.sospensione = False
        utente.save()
        return Response(
            {'status': f'Utente {utente.nome} {utente.cognome} riattivato con successo.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def salva_carta(self, request, pk=None):
        """IF-U13: salva un metodo di pagamento tokenizzato (gateway simulato).

        Il numero carta e il CVV NON vengono mai memorizzati: si conserva solo
        il token e le ultime 4 cifre, come con un vero gateway PCI-DSS.
        """
        utente = self.get_object()
        numero = request.data.get('numero')
        scadenza = request.data.get('scadenza')
        try:
            dati = GatewayPagamento().tokenizza_carta(numero, scadenza)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        utente.metodo_pagamento = 'CARTA'
        utente.pagamento_token = dati['token']
        utente.pagamento_ultime4 = dati['ultime4']
        utente.pagamento_circuito = dati['circuito']
        utente.save()
        return Response(
            {'status': 'Metodo di pagamento salvato.',
             'circuito': dati['circuito'],
             'carta': f"**** **** **** {dati['ultime4']}"},
            status=status.HTTP_200_OK
        )


class MezzoViewSet(viewsets.ModelViewSet):
    serializer_class = MezzoSerializer
    search_fields = ['tipo']

    def get_queryset(self):
        queryset = Mezzo.objects.all()
        # Il filtro "solo disponibili" vale per la lista pubblica sulla mappa;
        # le azioni di dettaglio (prenota, blocca_remoto, ecc.) devono poter
        # raggiungere i mezzi in qualsiasi stato.
        if self.action == 'list':
            mostra_tutti = self.request.query_params.get('mostra_tutti', 'false').lower() == 'true'
            if not mostra_tutti:
                return queryset.filter(stato='DISPONIBILE')
        return queryset

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
        mezzo = self.get_object()
        if mezzo.stato != 'DISPONIBILE':
            return Response(
                {'error': f'Impossibile prenotare il mezzo: stato attuale {mezzo.stato}.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        mezzo.stato = 'PRENOTATO'
        mezzo.scadenza_prenotazione = timezone.now() + timedelta(minutes=15)
        mezzo.save()
        return Response({'status': 'Mezzo prenotato con successo per 15 minuti.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def mappa_flotta(self, request):
        mezzi = Mezzo.objects.all()
        serializer = self.get_serializer(mezzi, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def blocca_remoto(self, request, pk=None):
        """IF-O09: l'operatore immobilizza il mezzo da remoto (furto o uscita da zone consentite)."""
        mezzo = self.get_object()
        if mezzo.stato == 'BLOCCATO':
            return Response({'error': 'Il mezzo è già bloccato.'}, status=status.HTTP_400_BAD_REQUEST)
        mezzo.stato = 'BLOCCATO'
        mezzo.save()
        motivo = request.data.get('motivo', 'sospetto furto')
        return Response(
            {'status': f"Mezzo #{mezzo.id} immobilizzato da remoto. Motivo: {motivo}."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def sblocca_remoto(self, request, pk=None):
        """IF-O09: l'operatore rimuove il blocco remoto e rimette il mezzo disponibile."""
        mezzo = self.get_object()
        if mezzo.stato != 'BLOCCATO':
            return Response({'error': 'Il mezzo non è in stato bloccato.'}, status=status.HTTP_400_BAD_REQUEST)
        mezzo.stato = 'DISPONIBILE'
        mezzo.save()
        return Response({'status': f'Mezzo #{mezzo.id} sbloccato e rimesso in servizio.'}, status=status.HTTP_200_OK)


class AreaUrbanaViewSet(viewsets.ModelViewSet):
    queryset = Area_Urbana.objects.all()
    serializer_class = AreaUrbanaSerializer

    @action(detail=False, methods=['get'])
    def zone_vietate(self, request):
        """IF-U16 / IF-A03: aree dove circolazione o parcheggio sono proibiti (VIETATA + CANTIERE)."""
        aree = Area_Urbana.objects.filter(tipologia__in=['VIETATA', 'CANTIERE'])
        serializer = self.get_serializer(aree, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def aree_parcheggio(self, request):
        """IF-O03: aree designate dove è consentito rilasciare il mezzo."""
        aree = Area_Urbana.objects.filter(tipologia='PARCHEGGIO')
        serializer = self.get_serializer(aree, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PromozioneViewSet(viewsets.ModelViewSet):
    """IF-U08: gestione e validazione dei codici sconto."""
    queryset = Promozione.objects.all()
    serializer_class = PromozioneSerializer

    @action(detail=False, methods=['post'])
    def valida(self, request):
        """Verifica un codice promozionale e ne restituisce i dettagli se valido."""
        codice = str(request.data.get('codice', '')).strip()
        if not codice:
            return Response({'valida': False, 'error': 'Inserisci un codice.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            promo = Promozione.objects.get(codice=codice)
        except Promozione.DoesNotExist:
            return Response({'valida': False, 'error': 'Codice inesistente.'}, status=status.HTTP_404_NOT_FOUND)
        if not promo.is_valida():
            return Response({'valida': False, 'error': 'Codice scaduto o non più attivo.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'valida': True, 'codice': promo.codice, 'tipo_sconto': promo.tipo_sconto, 'valore': str(promo.valore)},
            status=status.HTTP_200_OK
        )


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

    @action(detail=True, methods=['post'])
    def risolvi(self, request, pk=None):
        """IF-O07: l'operatore chiude la segnalazione e rimette il mezzo disponibile."""
        segnalazione = self.get_object()
        segnalazione.risolta = True
        segnalazione.save()
        # Se non ci sono altre segnalazioni aperte sul mezzo, lo si rimette in servizio
        altre_aperte = Segnalazione.objects.filter(mezzo=segnalazione.mezzo, risolta=False).exists()
        if not altre_aperte and segnalazione.mezzo.stato == 'MANUTENZIONE':
            segnalazione.mezzo.stato = 'DISPONIBILE'
            segnalazione.mezzo.save()
        return Response(
            {'status': f'Segnalazione #{segnalazione.id} risolta.',
             'mezzo_rimesso_in_servizio': not altre_aperte},
            status=status.HTTP_200_OK
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
        codice_promo = request.data.get('codice_promo')
        guasto_certificato = bool(request.data.get('guasto_certificato', False))

        # IF-U08: risoluzione dell'eventuale codice promozionale
        promozione = None
        if codice_promo:
            try:
                promozione = Promozione.objects.get(codice=str(codice_promo).strip())
            except Promozione.DoesNotExist:
                return Response({'error': 'Codice promozionale inesistente.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            corsa.termina_corsa(
                lat_rilascio=lat,
                lng_rilascio=lng,
                promozione=promozione,
                guasto_certificato=guasto_certificato,
            )
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

        return Response({'status': 'Posizione registrata.'}, status=status.HTTP_201_CREATED)

# ==========================================================================
#  BLOCCO 2 - Amministrazione & Analytics (IF-A01, IF-A02, IF-A04, IF-O05, IF-O07)
# ==========================================================================

def _zona_di(corsa):
    """Ricava la zona/quartiere di una corsa: area di rilascio se nota,
    altrimenti l'Area_Urbana più vicina alla posizione attuale del mezzo."""
    if corsa.area_rilascio_id:
        return corsa.area_rilascio.nome_zona
    mezzo = corsa.mezzo
    aree = list(Area_Urbana.objects.all())
    if not aree or mezzo.latitudine is None or mezzo.longitudine is None:
        return 'Sconosciuta'
    def dist(a):
        dy = (mezzo.latitudine - a.latitudine) * 111000
        dx = (mezzo.longitudine - a.longitudine) * 80000
        return math.sqrt(dx ** 2 + dy ** 2)
    return min(aree, key=dist).nome_zona


class AnalyticsCO2View(APIView):
    """IF-A04: CO2 risparmiata rispetto all'uso di auto private."""
    def get(self, request):
        corse = Corsa.objects.filter(fine__isnull=False)
        km_per_tipo = {}
        for c in corse.select_related('mezzo'):
            km_per_tipo[c.mezzo.tipo] = km_per_tipo.get(c.mezzo.tipo, 0.0) + (c.distanza_km or 0.0)
        km_green = km_per_tipo.get('BICI', 0.0) + km_per_tipo.get('SCOOTER', 0.0)
        co2_risparmiata = round(km_green * CO2_AUTO_KG_PER_KM, 2)
        return Response({
            'km_totali': round(sum(km_per_tipo.values()), 2),
            'km_green': round(km_green, 2),
            'coefficiente_kg_per_km': CO2_AUTO_KG_PER_KM,
            'co2_risparmiata_kg': co2_risparmiata,
            'dettaglio_km_per_tipo': {k: round(v, 2) for k, v in km_per_tipo.items()},
        }, status=status.HTTP_200_OK)


class AnalyticsUtilizzoView(APIView):
    """IF-A01: dati per i grafici di utilizzo (per tipo mezzo, fascia oraria, zona)."""
    def get(self, request):
        corse = Corsa.objects.select_related('mezzo', 'area_rilascio').all()

        per_tipo = dict(
            Corsa.objects.values_list('mezzo__tipo').annotate(n=Count('id')).order_by()
        )

        per_ora = [0] * 24
        per_zona = {}
        for c in corse:
            per_ora[timezone.localtime(c.inizio).hour] += 1
            z = _zona_di(c)
            per_zona[z] = per_zona.get(z, 0) + 1

        return Response({
            'corse_per_tipo': per_tipo,
            'corse_per_ora': per_ora,
            'corse_per_zona': per_zona,
            'totale_corse': corse.count(),
        }, status=status.HTTP_200_OK)


class AnalyticsReportView(APIView):
    """IF-A02: report periodico (ricavi, incidenti, efficienza). Parametro ?giorni=N (default 30)."""
    def get(self, request):
        try:
            giorni = int(request.query_params.get('giorni', 30))
        except ValueError:
            giorni = 30
        da = timezone.now() - timedelta(days=giorni)

        corse_periodo = Corsa.objects.filter(inizio__gte=da)
        corse_concluse = corse_periodo.filter(fine__isnull=False)

        ricavi = corse_concluse.aggregate(tot=Sum('costo_totale'))['tot'] or 0
        n_corse = corse_periodo.count()
        n_segnalazioni = Segnalazione.objects.filter(data_segnalazione__gte=da).count()

        tot_mezzi = Mezzo.objects.count()
        in_manutenzione = Mezzo.objects.filter(stato='MANUTENZIONE').count()
        durata_media_min = None
        if corse_concluse.exists():
            durate = [ (c.fine - c.inizio).total_seconds() / 60.0 for c in corse_concluse ]
            durata_media_min = round(sum(durate) / len(durate), 1)

        return Response({
            'periodo_giorni': giorni,
            'ricavi_totali_eur': round(float(ricavi), 2),
            'numero_corse': n_corse,
            'numero_segnalazioni': n_segnalazioni,
            'efficienza': {
                'corse_per_mezzo': round(n_corse / tot_mezzi, 2) if tot_mezzi else 0,
                'percentuale_flotta_in_manutenzione': round(100 * in_manutenzione / tot_mezzi, 1) if tot_mezzi else 0,
                'durata_media_corsa_min': durata_media_min,
            },
        }, status=status.HTTP_200_OK)


class OperatoreAllerteView(APIView):
    """IF-O05: notifiche automatiche su batteria scarica e mezzi guasti. ?soglia_batteria=N (default 10)."""
    def get(self, request):
        try:
            soglia = int(request.query_params.get('soglia_batteria', 10))
        except ValueError:
            soglia = 10

        batteria_scarica = Mezzo.objects.filter(batteria__lt=soglia).exclude(stato='MANUTENZIONE')
        guasti = Mezzo.objects.filter(stato='MANUTENZIONE')

        allerte = []
        for m in batteria_scarica:
            allerte.append({'tipo': 'BATTERIA_SCARICA', 'mezzo_id': m.id,
                            'messaggio': f"{m.tipo} #{m.id}: batteria al {m.batteria}%",
                            'latitudine': m.latitudine, 'longitudine': m.longitudine})
        for m in guasti:
            allerte.append({'tipo': 'GUASTO', 'mezzo_id': m.id,
                            'messaggio': f"{m.tipo} #{m.id}: in manutenzione",
                            'latitudine': m.latitudine, 'longitudine': m.longitudine})
        return Response({'totale': len(allerte), 'allerte': allerte}, status=status.HTTP_200_OK)


class OperatoreConsoleView(APIView):
    """IF-O07: riepilogo operatore (segnalazioni aperte, chat aperte, allerte attive)."""
    def get(self, request):
        segnalazioni = Segnalazione.objects.filter(risolta=False).order_by('-data_segnalazione')
        chat_aperte = ChatTicket.objects.filter(risolto=False).order_by('-timestamp')

        soglia = 10
        n_allerte = (Mezzo.objects.filter(batteria__lt=soglia).exclude(stato='MANUTENZIONE').count()
                     + Mezzo.objects.filter(stato='MANUTENZIONE').count())

        return Response({
            'segnalazioni_aperte': SegnalazioneSerializer(segnalazioni, many=True).data,
            'chat_aperte_count': chat_aperte.count(),
            'allerte_attive_count': n_allerte,
        }, status=status.HTTP_200_OK)


# ==========================================================================
#  BLOCCO 3 - Routing, Meteo, Chat (IF-U06, IF-U07, IF-U09)
# ==========================================================================

class RoutingView(APIView):
    """IF-U06: percorso più breve tra due punti, evitando le zone vietate.

    POST { "origine": [lat, lng], "destinazione": [lat, lng], "tipo_mezzo": "BICI" }
    """
    def post(self, request):
        origine = request.data.get('origine')
        destinazione = request.data.get('destinazione')
        tipo_mezzo = request.data.get('tipo_mezzo', 'SCOOTER')
        if not (isinstance(origine, list) and isinstance(destinazione, list)
                and len(origine) == 2 and len(destinazione) == 2):
            return Response(
                {'error': 'Fornire origine e destinazione come [latitudine, longitudine].'},
                status=status.HTTP_400_BAD_REQUEST
            )
        aree_vietate = list(Area_Urbana.objects.filter(tipologia__in=['VIETATA', 'CANTIERE']))
        percorso = RoutingService().calcola_percorso(
            [float(origine[0]), float(origine[1])],
            [float(destinazione[0]), float(destinazione[1])],
            tipo_mezzo=tipo_mezzo,
            aree_vietate=aree_vietate,
        )
        return Response(percorso, status=status.HTTP_200_OK)


class MeteoSuggerimentoView(APIView):
    """IF-U07: meteo attuale e mezzo consigliato in base a meteo e distanza.
    Parametri opzionali: ?condizione=PIOGGIA  ?distanza_km=3.5
    """
    def get(self, request):
        giorno_anno = timezone.now().timetuple().tm_yday
        condizione = request.query_params.get('condizione')
        distanza = request.query_params.get('distanza_km')
        try:
            distanza = float(distanza) if distanza is not None else None
        except ValueError:
            distanza = None
        dati = MeteoService().get_meteo(giorno_anno, condizione=condizione, distanza_km=distanza)
        return Response(dati, status=status.HTTP_200_OK)


class ChatTicketViewSet(viewsets.ModelViewSet):
    """IF-U09 / IF-O07: messaggistica di assistenza utente <-> operatore/chatbot (polling REST)."""
    queryset = ChatTicket.objects.all()
    serializer_class = ChatTicketSerializer

    # Risposte automatiche del chatbot in base a parole chiave
    RISPOSTE_BOT = [
        (('sblocc', 'qr', 'codice'), "Per sbloccare il mezzo inquadra il QR o inserisci il codice a 6 cifre. Se non funziona, un operatore ti risponderà a breve."),
        (('pagament', 'carta', 'addebito'), "Per i pagamenti controlla il metodo salvato nel profilo. Un operatore verificherà eventuali addebiti errati."),
        (('batteria', 'scarica'), "Se la batteria è scarica termina la corsa in un'area di parcheggio: non verrai penalizzato."),
        (('incidente', 'caduta', 'danno'), "Mi dispiace! Se sei ferito chiama il 112. Per i danni al mezzo usa la funzione 'Segnala guasto'. Un operatore ti contatterà."),
    ]

    def get_queryset(self):
        qs = ChatTicket.objects.all()
        utente_id = self.request.query_params.get('utente')
        if utente_id:
            qs = qs.filter(utente_id=utente_id)
        if self.request.query_params.get('aperti') == 'true':
            qs = qs.filter(risolto=False)
        return qs

    def create(self, request, *args, **kwargs):
        """Messaggio dell'utente; genera anche una risposta automatica del chatbot."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = serializer.save(operatore=None, da_bot=False)

        bot = self._risposta_bot(msg.messaggio)
        bot_msg = ChatTicket.objects.create(utente=msg.utente, messaggio=bot, da_bot=True)

        return Response(
            {'messaggio_utente': self.get_serializer(msg).data,
             'risposta_bot': self.get_serializer(bot_msg).data},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def rispondi(self, request, pk=None):
        """IF-O07: un operatore risponde al ticket di un utente.

        L'operatore è determinato, in ordine: id passato nel body ('operatore'),
        utente autenticato, oppure primo account staff disponibile.
        """
        ticket = self.get_object()
        testo = request.data.get('messaggio')
        if not testo:
            return Response({'error': 'Messaggio mancante.'}, status=status.HTTP_400_BAD_REQUEST)

        operatore = None
        op_id = request.data.get('operatore')
        if op_id:
            operatore = User.objects.filter(pk=op_id).first()
        elif request.user.is_authenticated:
            operatore = request.user
        if operatore is None:
            operatore = User.objects.filter(is_staff=True).first() or User.objects.first()

        risposta = ChatTicket.objects.create(utente=ticket.utente, operatore=operatore, messaggio=testo)
        return Response(self.get_serializer(risposta).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def risolvi(self, request, pk=None):
        """Chiude l'intera conversazione dell'utente collegato al ticket."""
        ticket = self.get_object()
        aggiornati = ChatTicket.objects.filter(utente=ticket.utente, risolto=False).update(risolto=True)
        return Response({'status': f'Conversazione chiusa ({aggiornati} messaggi).'}, status=status.HTTP_200_OK)

    def _risposta_bot(self, testo):
        t = (testo or '').lower()
        for chiavi, risposta in self.RISPOSTE_BOT:
            if any(k in t for k in chiavi):
                return risposta
        return "Grazie per averci contattato. La tua richiesta è stata registrata: un operatore ti risponderà al più presto."
