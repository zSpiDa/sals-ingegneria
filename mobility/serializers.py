from rest_framework import serializers
from .models import Utente, Mezzo, Area_Urbana, Corsa, Segnalazione, PosizioneGPS

class UtenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utente
        fields = ['id', 'nome', 'cognome', 'documento', 'patente_verificata', 'sospensione']

class MezzoSerializer(serializers.ModelSerializer):
    stato_critico = serializers.SerializerMethodField()
    autonomia_km = serializers.SerializerMethodField() # NUOVO CAMPO

    class Meta:
        model = Mezzo
        fields = ['id', 'tipo', 'stato', 'latitudine', 'longitudine', 'batteria', 'stato_critico', 'autonomia_km']

    def get_stato_critico(self, obj):
        return obj.batteria < 10

    def get_autonomia_km(self, obj):
        # Stima: 1% di batteria = 0.5km per scooter, 0.8km per bici, 1.5km per auto
        moltiplicatori = {'BICI': 0.8, 'SCOOTER': 0.5, 'AUTO': 1.5}
        return round(obj.batteria * moltiplicatori.get(obj.tipo, 0.5), 1)

class AreaUrbanaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area_Urbana
        fields = '__all__'

class SegnalazioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segnalazione
        fields = ['id', 'utente', 'mezzo', 'descrizione', 'data_segnalazione', 'risolta']
        read_only_fields = ['data_segnalazione', 'risolta']

class PosizioneGPSSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(format="%H:%M:%S", read_only=True)
    
    class Meta:
        model = PosizioneGPS
        fields = ['latitudine', 'longitudine', 'timestamp']

class CorsaSerializer(serializers.ModelSerializer):
    inizio = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    fine = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)

    utente_dettagli = UtenteSerializer(source='utente', read_only=True)
    mezzo_dettagli = MezzoSerializer(source='mezzo', read_only=True)
    # Lista delle coordinate GPS nella risposta
    percorso = PosizioneGPSSerializer(source='percorso_gps', many=True, read_only=True)

    class Meta:
        model = Corsa
        fields = [
            'id', 'utente', 'mezzo', 'inizio', 
            'fine', 'costo_totale',
            'utente_dettagli', 'mezzo_dettagli', 'percorso'
        ]
        read_only_fields = ['costo_totale']

    def validate(self, data):
        utente = data.get('utente')
        if utente and utente.sospensione:
            raise serializers.ValidationError("L'account utente è sospeso per vandalismi o insoluti.")
        return data