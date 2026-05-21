from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
# 1. IMPORTANTE: Importiamo il modello User nativo di Django per l'autenticazione JWT
from django.contrib.auth.models import User
import math

class Utente(models.Model):
    # Opzioni per il metodo di pagamento
    METODI_PAGAMENTO = [
        ('CARTA', 'Carta di Credito/Debito'),
        ('PAYPAL', 'PayPal'),
        ('APPLE_PAY', 'Apple Pay'),
        ('GOOGLE_PAY', 'Google Pay'),
    ]

    # 2. IMPORTANTE: Creiamo il collegamento biunivoco (OneToOne) con l'User di Django
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profilo_utente'
    )

    nome = models.CharField(max_length=50)
    cognome = models.CharField(max_length=50)
    documento = models.CharField(max_length=20, unique=True, help_text="Codice Fiscale o Carta d'Identità")
    patente_verificata = models.BooleanField(default=False)
    sospensione = models.BooleanField(default=False, help_text="Se True, l'utente non può noleggiare mezzi")
    metodo_pagamento = models.CharField(max_length=20, choices=METODI_PAGAMENTO, default='CARTA')
    data_creazione = models.DateTimeField(auto_now_add=True)
    ultimo_accesso = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Utenti"

    def __str__(self):
        return f"{self.nome} {self.cognome} - [{self.documento}]"


class Mezzo(models.Model):
    TIPI_MEZZO = [
        ('BICI', 'Bicicletta Elettrica'),
        ('AUTO', 'Automobile'),
        ('SCOOTER', 'E-Scooter'),
    ]
    
    STATI_MEZZO = [
        ('DISPONIBILE', 'Disponibile'),
        ('PRENOTATO', 'Prenotato'),
        ('IN_USO', 'In Uso'),
        ('MANUTENZIONE', 'In Manutenzione'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPI_MEZZO)
    stato = models.CharField(max_length=20, choices=STATI_MEZZO, default='DISPONIBILE')
    batteria = models.IntegerField(help_text="Percentuale di carica (0-100)")
    latitudine = models.FloatField()
    longitudine = models.FloatField()
    targa = models.CharField(max_length=20, unique=True, null=True, blank=True)
    data_ultimo_check = models.DateTimeField(auto_now=True)
    sbloccato = models.BooleanField(default=False, help_text="Indica se il mezzo è sbloccato")

    class Meta:
        verbose_name_plural = "Mezzi"

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.id} ({self.batteria}% - {self.get_stato_display()})"
    
    def distanza_da(self, lat, lng):
        """Calcola la distanza in km usando la formula di Haversine."""
        R = 6371  # Raggio terrestre in km
        lat1_rad = math.radians(self.latitudine)
        lat2_rad = math.radians(lat)
        delta_lat = math.radians(lat - self.latitudine)
        delta_lng = math.radians(lng - self.longitudine)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


class Area_Urbana(models.Model):
    TIPI_AREA = [
        ('PARCHEGGIO', 'Area di Parcheggio Consentita'),
        ('VIETATA', 'Zona a Traffico Limitato / Divieto'),
        ('CANTIERE', 'Cantiere / Strada Chiusa'),
    ]

    nome_zona = models.CharField(max_length=100)
    tipologia = models.CharField(max_length=20, choices=TIPI_AREA)
    latitudine_centro = models.FloatField()
    longitudine_centro = models.FloatField()
    raggio_m = models.IntegerField(default=100, help_text="Raggio in metri")

    class Meta:
        verbose_name = "Area Urbana"
        verbose_name_plural = "Aree Urbane"

    def __str__(self):
        return f"{self.nome_zona} ({self.get_tipologia_display()})"
    
    def contiene_punto(self, lat, lng):
        """Verifica se le coordinate lat/lng rientrano nell'area."""
        mezzo_temp = Mezzo(latitudine=lat, longitudine=lng)
        distanza_km = mezzo_temp.distanza_da(self.latitudine_centro, self.longitudine_centro)
        return distanza_km * 1000 <= self.raggio_m


class Corsa(models.Model):
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='corse')
    mezzo = models.ForeignKey(Mezzo, on_delete=models.CASCADE, related_name='corse')
    inizio = models.DateTimeField(default=timezone.now)
    fine = models.DateTimeField(null=True, blank=True)
    costo_totale = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    latitudine_inizio = models.FloatField(null=True, blank=True)
    longitudine_inizio = models.FloatField(null=True, blank=True)
    latitudine_fine = models.FloatField(null=True, blank=True)
    longitudine_fine = models.FloatField(null=True, blank=True)
    metodo_pagamento_utilizzato = models.CharField(max_length=20, choices=Utente.METODI_PAGAMENTO, null=True, blank=True)
    sbloccato = models.BooleanField(default=False, help_text="Se il mezzo è stato sbloccato via app")

    class Meta: 
        verbose_name_plural = "Corse"
        ordering = ['-inizio']

    @classmethod
    def avvia_corsa(cls, utente, mezzo, lat_inizio=None, lng_inizio=None):
        """Controlla i requisiti e avvia una nuova corsa."""
        if utente.sospensione:
            raise ValidationError("Impossibile avviare la corsa: l'account utente è sospeso.")
        
        if mezzo.stato != 'DISPONIBILE':
            raise ValidationError(f"Il mezzo selezionato non è disponibile (Stato attuale: {mezzo.stato}).")
            
        if mezzo.tipo == 'AUTO' and not utente.patente_verificata:
            raise ValidationError("È richiesta la patente verificata per noleggiare un'auto.")
            
        if mezzo.batteria < 10:
            raise ValidationError("Batteria troppo bassa per avviare il noleggio.")

        mezzo.stato = 'IN_USO'
        mezzo.save()

        corsa = cls.objects.create(
            utente=utente, 
            mezzo=mezzo,
            latitudine_inizio=lat_inizio,
            longitudine_inizio=lng_inizio,
            metodo_pagamento_utilizzato=utente.metodo_pagamento
        )
        return corsa

    def termina_corsa(self, lat_fine=None, lng_fine=None):
        """Termina la corsa, calcola i minuti e il costo totale."""
        if self.fine is not None:
            raise ValidationError("Questa corsa è già stata terminata.")

        self.fine = timezone.now()
        self.latitudine_fine = lat_fine
        self.longitudine_fine = lng_fine
        
        # Validazione geofencing - controllo zona parcheggio/vietata
        if lat_fine and lng_fine:
            aree_vietate = Area_Urbana.objects.filter(tipologia='VIETATA')
            for area in aree_vietate:
                if area.contiene_punto(lat_fine, lng_fine):
                    raise ValidationError(f"Non è consentito parcheggiare in '{area.nome_zona}'")
        
        durata_secondi = (self.fine - self.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)

        tariffe = {
            'BICI': 0.15,
            'SCOOTER': 0.20,
            'AUTO': 0.35
        }
        
        tariffa_applicata = tariffe.get(self.mezzo.tipo, 0.20)
        costo = durata_minuti * tariffa_applicata
        self.costo_totale = round(costo, 2)
        self.save()

        self.mezzo.stato = 'DISPONIBILE'
        self.mezzo.sbloccato = False
        self.mezzo.save()

    def costo_corrente(self):
        """Calcola il costo parziale in tempo reale."""
        if self.fine:
            return self.costo_totale
        
        durata_secondi = (timezone.now() - self.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)
        
        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
        tariffa_applicata = tariffe.get(self.mezzo.tipo, 0.20)
        return round(durata_minuti * tariffa_applicata, 2)

    def __str__(self): 
        return f"Corsa #{self.id} - {self.utente} su {self.mezzo.tipo}"
    