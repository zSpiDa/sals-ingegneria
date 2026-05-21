from rest_framework import serializers
from .models import Utente, Mezzo, Area_Urbana, Corsa
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class UtenteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    metodo_pagamento_display = serializers.CharField(source='get_metodo_pagamento_display', read_only=True)
    
    class Meta:
        model = Utente
        fields = ['id', 'user', 'nome', 'cognome', 'documento', 'patente_verificata', 
                  'sospensione', 'metodo_pagamento', 'metodo_pagamento_display', 'data_creazione', 'ultimo_accesso']

class MezzoSerializer(serializers.ModelSerializer):
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    stato_critico = serializers.SerializerMethodField()
    distanza_km = serializers.SerializerMethodField()

    class Meta:
        model = Mezzo
        fields = ['id', 'tipo', 'tipo_display', 'stato', 'stato_display', 'latitudine', 
                  'longitudine', 'batteria', 'stato_critico', 'targa', 'sbloccato', 'distanza_km']

    def get_stato_critico(self, obj):
        return obj.batteria < 10
    
    def get_distanza_km(self, obj):
        lat = self.context.get('latitude')
        lng = self.context.get('longitude')
        if lat and lng:
            return round(obj.distanza_da(lat, lng), 2)
        return None

class AreaUrbanaSerializer(serializers.ModelSerializer):
    tipologia_display = serializers.CharField(source='get_tipologia_display', read_only=True)
    
    class Meta:
        model = Area_Urbana
        fields = ['id', 'nome_zona', 'tipologia', 'tipologia_display', 'latitudine_centro', 
                  'longitudine_centro', 'raggio_m']

class CorsaSerializer(serializers.ModelSerializer):
    inizio = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    fine = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    costo_corrente = serializers.SerializerMethodField()

    utente_dettagli = UtenteSerializer(source='utente', read_only=True)
    mezzo_dettagli = MezzoSerializer(source='mezzo', read_only=True)
    
    metodo_pagamento_display = serializers.CharField(source='get_metodo_pagamento_utilizzato_display', read_only=True)

    class Meta:
        model = Corsa
        fields = [
            'id', 'utente', 'mezzo', 'inizio', 'fine', 'costo_totale', 'costo_corrente',
            'latitudine_inizio', 'longitudine_inizio', 'latitudine_fine', 'longitudine_fine',
            'metodo_pagamento_utilizzato', 'metodo_pagamento_display', 'sbloccato',
            'utente_dettagli', 'mezzo_dettagli'
        ]
        read_only_fields = ['costo_totale', 'costo_corrente', 'inizio', 'fine']

    def get_costo_corrente(self, obj):
        return obj.costo_corrente()

    def validate(self, data):
        utente = data.get('utente')
        if utente and utente.sospensione:
            raise serializers.ValidationError("L'account utente è sospeso per vandalismi o insoluti.")
        return data