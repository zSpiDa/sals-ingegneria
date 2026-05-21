from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Utente, Mezzo, Area_Urbana, Corsa
from .serializers import UtenteSerializer, MezzoSerializer, AreaUrbanaSerializer, CorsaSerializer, UserSerializer


class AuthViewSet(viewsets.ViewSet):
    """Endpoint per autenticazione e registrazione."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def registrazione(self, request):
        """
        POST /api/auth/registrazione/
        Crea un nuovo utente con profilo Utente associato.
        Body: {
            "username": "mario.rossi",
            "email": "mario@email.com",
            "password": "SecurePass123",
            "first_name": "Mario",
            "last_name": "Rossi",
            "nome": "Mario",
            "cognome": "Rossi",
            "documento": "RSSMRA80A01H501Y"
        }
        """
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        nome = request.data.get('nome', first_name)
        cognome = request.data.get('cognome', last_name)
        documento = request.data.get('documento')

        if not all([username, email, password, documento]):
            return Response({'error': 'Fornire username, email, password e documento.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username già in uso.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if Utente.objects.filter(documento=documento).exists():
            return Response({'error': 'Documento già registrato.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        utente = Utente.objects.create(
            user=user,
            nome=nome,
            cognome=cognome,
            documento=documento
        )

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profilo': UtenteSerializer(utente).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        POST /api/auth/login/
        Restituisce i token JWT per l'autenticazione.
        Body: {"username": "mario.rossi", "password": "SecurePass123"}
        """
        from rest_framework_simplejwt.tokens import RefreshToken
        
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Fornire username e password.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Credenziali non valide.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'error': 'Credenziali non valide.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        
        # Aggiorna ultimo_accesso
        try:
            utente = user.profilo_utente
            utente.ultimo_accesso = timezone.now()
            utente.save()
        except:
            pass

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class UtenteViewSet(viewsets.ModelViewSet):
    """
    Endpoint per gestire gli utenti del sistema di mobilità.
    Fornisce automaticamente GET, POST, PUT, DELETE.
    """
    queryset = Utente.objects.all()
    serializer_class = UtenteSerializer
    search_fields = ['nome', 'cognome', 'documento', 'user__username']
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def profilo(self, request):
        """GET /api/utenti/profilo/ - Restituisce il profilo dell'utente loggato."""
        try:
            utente = request.user.profilo_utente
            serializer = self.get_serializer(utente)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Utente.DoesNotExist:
            return Response({'error': 'Profilo utente non trovato.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['put'])
    def aggiorna_profilo(self, request):
        """PUT /api/utenti/aggiorna_profilo/ - Aggiorna il profilo dell'utente loggato."""
        try:
            utente = request.user.profilo_utente
            serializer = self.get_serializer(utente, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Utente.DoesNotExist:
            return Response({'error': 'Profilo utente non trovato.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['put'])
    def cambia_metodo_pagamento(self, request, pk=None):
        """PUT /api/utenti/{id}/cambia_metodo_pagamento/ - Cambia il metodo di pagamento."""
        utente = self.get_object()
        metodo = request.data.get('metodo_pagamento')
        
        if metodo not in dict(Utente.METODI_PAGAMENTO):
            return Response({'error': f'Metodo di pagamento non valido: {metodo}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        utente.metodo_pagamento = metodo
        utente.save()
        serializer = self.get_serializer(utente)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MezzoViewSet(viewsets.ModelViewSet):
    """
    Endpoint per la gestione della flotta dei veicoli (Bici, Scooter, Auto).
    IF-U01: Visualizzazione mezzi disponibili
    IF-U11: Visualizzazione stato di carica
    """
    serializer_class = MezzoSerializer
    search_fields = ['tipo', 'targa']
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filtra i mezzi: di default mostra solo quelli 'DISPONIBILE'.
        Se viene passato il parametro ?mostra_tutti=true mostra l'intera flotta.
        ?filtro_batteria=LOW mostra solo batteria < 20%
        """
        queryset = Mezzo.objects.all()
        mostra_tutti = self.request.query_params.get('mostra_tutti', 'false').lower() == 'true'
        filtro_batteria = self.request.query_params.get('filtro_batteria', '')
        filtro_tipo = self.request.query_params.get('tipo', '')
        
        if not mostra_tutti:
            queryset = queryset.filter(stato='DISPONIBILE')
        
        if filtro_batteria == 'LOW':
            queryset = queryset.filter(batteria__lt=20)
        elif filtro_batteria == 'CRITICAL':
            queryset = queryset.filter(batteria__lt=10)
        
        if filtro_tipo:
            queryset = queryset.filter(tipo=filtro_tipo)
        
        return queryset.order_by('-batteria')

    @action(detail=True, methods=['post'])
    def prenota(self, request, pk=None):
        """
        POST /api/mezzi/{id}/prenota/
        IF-U02: Prenotazione mezzi disponibili
        Cambia lo stato del mezzo in PRENOTATO se era disponibile per 15 minuti.
        """
        mezzo = self.get_object()
        if mezzo.stato != 'DISPONIBILE':
            return Response(
                {'error': f'Impossibile prenotare il mezzo: stato attuale {mezzo.stato}.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        mezzo.stato = 'PRENOTATO'
        mezzo.save()
        return Response({
            'status': 'Mezzo prenotato con successo per 15 minuti.',
            'mezzo': self.get_serializer(mezzo).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def mappa_flotta(self, request):
        """
        GET /api/mezzi/mappa_flotta/
        IF-O02: Monitoraggio distribuzione flotta
        Restituisce le coordinate di tutti i mezzi per la mappa dell'applicazione.
        """
        mezzi = Mezzo.objects.all()
        serializer = self.get_serializer(mezzi, many=True)
        return Response({
            'totale_mezzi': mezzi.count(),
            'disponibili': mezzi.filter(stato='DISPONIBILE').count(),
            'in_uso': mezzi.filter(stato='IN_USO').count(),
            'prenotati': mezzi.filter(stato='PRENOTATO').count(),
            'manutenzione': mezzi.filter(stato='MANUTENZIONE').count(),
            'mezzi': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def statistiche(self, request):
        """GET /api/mezzi/statistiche/ - Restituisce statistiche sulla flotta."""
        totale = Mezzo.objects.count()
        disponibili = Mezzo.objects.filter(stato='DISPONIBILE').count()
        batteria_media = Mezzo.objects.all().aggregate(batteria_media=__import__('django.db.models', fromlist=['Avg']).Avg('batteria'))
        
        return Response({
            'totale_mezzi': totale,
            'disponibili': disponibili,
            'percentuale_disponibilita': round(disponibili / totale * 100, 2) if totale > 0 else 0,
            'per_tipo': {
                'BICI': Mezzo.objects.filter(tipo='BICI').count(),
                'SCOOTER': Mezzo.objects.filter(tipo='SCOOTER').count(),
                'AUTO': Mezzo.objects.filter(tipo='AUTO').count(),
            }
        }, status=status.HTTP_200_OK)


class AreaUrbanaViewSet(viewsets.ModelViewSet):
    """
    Endpoint per la gestione delle geo-fencing (Aree Parcheggio, Cantieri, Zone Vietate).
    Usato per la validazione di parcheggio e fine corsa.
    """
    queryset = Area_Urbana.objects.all()
    serializer_class = AreaUrbanaSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def valida_punto(self, request):
        """
        POST /api/aree-urbane/valida_punto/
        Valida se un punto (lat, lng) è dentro una zona vietata o consentita.
        Body: {"latitudine": 41.12, "longitudine": 16.86}
        """
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')
        
        if not lat or not lng:
            return Response({'error': 'Fornire latitudine e longitudine.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        aree_vietate = Area_Urbana.objects.filter(tipologia='VIETATA')
        aree_parcheggio = Area_Urbana.objects.filter(tipologia='PARCHEGGIO')
        
        zone_vietate = [area for area in aree_vietate if area.contiene_punto(lat, lng)]
        zone_consentite = [area for area in aree_parcheggio if area.contiene_punto(lat, lng)]
        
        return Response({
            'in_zona_vietata': len(zone_vietate) > 0,
            'zone_vietate': AreaUrbanaSerializer(zone_vietate, many=True).data,
            'in_zona_consentita': len(zone_consentite) > 0,
            'zone_consentite': AreaUrbanaSerializer(zone_consentite, many=True).data,
        }, status=status.HTTP_200_OK)


class CorsaViewSet(viewsets.ModelViewSet):
    """
    Endpoint core per la gestione dei noleggi attivi e dello storico corse.
    IF-U03: Stima costo corsa
    IF-U04: Visualizzazione costo in tempo reale
    IF-U05: Chiusura corsa e costo finale
    IF-U12: Sblocco mezzo tramite app
    IF-O04: Rilevamento posizione a fine corsa
    """
    queryset = Corsa.objects.all().order_by('-inizio')
    serializer_class = CorsaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def avvia(self, request):
        """
        POST /api/corse/avvia/
        IF-U03: Stima costo corsa + Inizio corsa
        Innesca la logica di business per iniziare un noleggio.
        Body: {
            "mezzo_id": 1,
            "latitudine": 41.12,
            "longitudine": 16.86
        }
        """
        utente = request.user.profilo_utente
        mezzo_id = request.data.get('mezzo_id')
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        if not mezzo_id:
            return Response({'error': 'Fornire l\'ID del mezzo.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        mezzo = get_object_or_404(Mezzo, id=mezzo_id)

        try:
            corsa = Corsa.avvia_corsa(utente=utente, mezzo=mezzo, lat_inizio=lat, lng_inizio=lng)
            serializer = self.get_serializer(corsa)
            return Response({
                'corsa': serializer.data,
                'stima_costo_al_minuto': 0.15 if mezzo.tipo == 'BICI' else (0.20 if mezzo.tipo == 'SCOOTER' else 0.35)
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sblocca(self, request, pk=None):
        """
        POST /api/corse/{id}/sblocca/
        IF-U12: Sblocco mezzo tramite app
        Sblocca il mezzo con validazione GPS (l'utente deve essere vicino).
        Body: {"latitudine": 41.12, "longitudine": 16.86}
        """
        corsa = self.get_object()
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        if not lat or not lng:
            return Response({'error': 'Fornire coordinate GPS.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Validazione: l'utente deve essere entro 100m dal mezzo
        distanza = corsa.mezzo.distanza_da(lat, lng)
        if distanza > 0.1:  # > 100m
            return Response({
                'error': f'Sei troppo lontano dal mezzo ({distanza*1000:.0f}m). Deve essere entro 100m.',
                'distanza_m': round(distanza * 1000, 2)
            }, status=status.HTTP_400_BAD_REQUEST)

        if corsa.sbloccato:
            return Response({'error': 'Il mezzo è già sbloccato.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        corsa.sbloccato = True
        corsa.mezzo.sbloccato = True
        corsa.mezzo.save()
        corsa.save()

        serializer = self.get_serializer(corsa)
        return Response({
            'status': 'Mezzo sbloccato con successo!',
            'corsa': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def costo_corrente(self, request, pk=None):
        """
        GET /api/corse/{id}/costo_corrente/
        IF-U04: Visualizzazione costo in tempo reale
        Fornisce una stima del costo in Euro accumulato fino al secondo corrente.
        Utile per l'applicazione mobile durante la corsa.
        """
        corsa = self.get_object()
        
        if corsa.fine:
            return Response({
                'corsa_id': corsa.id,
                'costo_totale': float(corsa.costo_totale),
                'stato': 'conclusa',
                'durata_minuti': int((corsa.fine - corsa.inizio).total_seconds() / 60)
            }, status=status.HTTP_200_OK)

        durata_secondi = (timezone.now() - corsa.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)
        costo_attuale = corsa.costo_corrente()

        return Response({
            'corsa_id': corsa.id,
            'minuti_trascorsi': int(durata_minuti),
            'secondi_trascorsi': int(durata_secondi),
            'costo_stimato_corrente': float(costo_attuale),
            'stato': 'in_corso'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def termina(self, request, pk=None):
        """
        POST /api/corse/{id}/termina/
        IF-U05: Chiusura corsa e costo finale
        IF-O04: Rilevamento posizione a fine corsa
        Conclude la corsa calcolando il prezzo e aggiornando l'ultima posizione GPS del mezzo.
        Body: {"latitudine": 41.12, "longitudine": 16.86}
        """
        corsa = self.get_object()
        lat = request.data.get('latitudine')
        lng = request.data.get('longitudine')

        try:
            corsa.termina_corsa(lat_fine=lat, lng_fine=lng)
            
            serializer = self.get_serializer(corsa)
            return Response({
                'status': 'Corsa terminata con successo!',
                'corsa': serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def mie_corse(self, request):
        """GET /api/corse/mie_corse/ - Restituisce la storia delle corse dell'utente loggato."""
        try:
            utente = request.user.profilo_utente
            corse = Corsa.objects.filter(utente=utente).order_by('-inizio')
            
            page = self.paginate_queryset(corse)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(corse, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Utente.DoesNotExist:
            return Response({'error': 'Profilo utente non trovato.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def corsa_attiva(self, request):
        """GET /api/corse/corsa_attiva/ - Restituisce la corsa attiva dell'utente (se esiste)."""
        try:
            utente = request.user.profilo_utente
            corsa = Corsa.objects.filter(utente=utente, fine__isnull=True).first()
            
            if not corsa:
                return Response({
                    'corsa_attiva': False,
                    'messaggio': 'Nessuna corsa attiva'
                }, status=status.HTTP_200_OK)
            
            serializer = self.get_serializer(corsa)
            return Response({
                'corsa_attiva': True,
                'corsa': serializer.data
            }, status=status.HTTP_200_OK)
        except Utente.DoesNotExist:
            return Response({'error': 'Profilo utente non trovato.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def statistiche_utente(self, request):
        """GET /api/corse/statistiche_utente/ - Statistiche personali dell'utente."""
        try:
            utente = request.user.profilo_utente
            corse = Corsa.objects.filter(utente=utente)
            corse_completate = corse.filter(fine__isnull=False)
            
            total_cost = sum(float(c.costo_totale) for c in corse_completate if c.costo_totale)
            total_duration = sum((c.fine - c.inizio).total_seconds() for c in corse_completate if c.fine)
            
            return Response({
                'totale_corse': corse.count(),
                'corse_completate': corse_completate.count(),
                'costo_totale_speso': round(total_cost, 2),
                'durata_totale_minuti': int(total_duration / 60),
                'costo_medio_corsa': round(total_cost / corse_completate.count(), 2) if corse_completate.count() > 0 else 0,
                'mezzo_preferito': corse_completate.values('mezzo__tipo').annotate(__import__('django.db.models', fromlist=['Count']).Count('id')).order_by('-id__count').first()
            }, status=status.HTTP_200_OK)
        except Utente.DoesNotExist:
            return Response({'error': 'Profilo utente non trovato.'}, status=status.HTTP_404_NOT_FOUND)