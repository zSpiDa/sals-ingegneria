from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Utente, Mezzo, Area_Urbana, Corsa, Segnalazione
from .serializers import UtenteSerializer, MezzoSerializer, AreaUrbanaSerializer, CorsaSerializer, SegnalazioneSerializer


class UtenteViewSet(viewsets.ModelViewSet):
    queryset = Utente.objects.all()
    serializer_class = UtenteSerializer
    search_fields = ['nome', 'cognome', 'documento']


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

        if not utente_id or not mezzo_id:
            return Response({'error': 'Fornire identificativi validi per utente e mezzo.'}, status=status.HTTP_400_BAD_REQUEST)

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
        """Mette in pausa il veicolo mantenendo la corsa attiva."""
        corsa = self.get_object()
        if corsa.fine:
            return Response({'error': 'La corsa è già terminata.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Usa PRENOTATO come stato per indicare che è temporaneamente inaccessibile ad altri
        corsa.mezzo.stato = 'PRENOTATO' 
        corsa.mezzo.save()
        
        return Response({'status': 'Pausa attiva. Tariffazione in corso.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def sblocco_temporaneo(self, request, pk=None):
        """Riprende la marcia dopo la pausa."""
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