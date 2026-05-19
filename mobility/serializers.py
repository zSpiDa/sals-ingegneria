from rest_framework import serializers
from .models import Utente, Mezzo, Area_Urbana, Corsa

class UtenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utente
        fields = ['id', 'nome', 'cognome', 'documento_identita', 'patente_verificata', 'sospensione']

class MezzoSerializer(serializers.ModelSerializer):
    # Formattazione aggiuntiva per lo stato della batteria
    stato_critico = serializers.SerializerMethodField()

    class Meta:
        model = Mezzo
        # QUI ABBIAMO CORRETTO 'id' e 'batteria'
        fields = ['id', 'tipo', 'stato', 'latitudine', 'longitudine', 'batteria', 'stato_critico']

    def get_stato_critico(self, obj):
        # QUI ABBIAMO CORRETTO 'obj.batteria'
        return obj.batteria < 10

class CorsaSerializer(serializers.ModelSerializer):
    # Formattazione date leggibili (Task Sviluppatore 1) [cite: 191]
    timestamp_inizio = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    timestamp_fine = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    
    # Dettagli in sola lettura per l'interfaccia utente [cite: 106, 182]
    utente_dettagli = UtenteSerializer(source='fk_utente', read_only=True)
    mezzo_dettagli = MezzoSerializer(source='fk_mezzo', read_only=True)

    class Meta:
        model = Corsa
        fields = [
            'id', 'fk_utente', 'fk_mezzo', 'timestamp_inizio', 
            'timestamp_fine', 'costo_totale', 'percorso_tracciato',
            'utente_dettagli', 'mezzo_dettagli'
        ]
        read_only_fields = ['costo_totale', 'percorso_tracciato']

    def validate(self, data):
        """
        Validazioni di business per lo Sviluppatore 1
        """
        # Esempio: IF-O03 - Impedire noleggio se l'utente è sospeso [cite: 246]
        utente = data.get('fk_utente')
        if utente and utente.sospensione:
            raise serializers.ValidationError("L'account utente è sospeso per vandalismi o insoluti.")
        return data