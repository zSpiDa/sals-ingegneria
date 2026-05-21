from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
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

    class Meta:
        verbose_name_plural = "Mezzi"

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.id} ({self.batteria}% - {self.get_stato_display()})"


class Area_Urbana(models.Model):
    TIPI_AREA = [
        ('PARCHEGGIO', 'Area di Parcheggio Consentita'),
        ('VIETATA', 'Zona a Traffico Limitato / Divieto'),
        ('CANTIERE', 'Cantiere / Strada Chiusa'),
    ]

    nome_zona = models.CharField(max_length=100)
    tipologia = models.CharField(max_length=20, choices=TIPI_AREA)
    latitudine = models.FloatField(default=0.0)
    longitudine = models.FloatField(default=0.0)
    raggio_metri = models.IntegerField(default=100, help_text="Raggio di estensione dell'area in metri")

    class Meta:
        verbose_name = "Area Urbana"
        verbose_name_plural = "Aree Urbane"

    def __str__(self):
        return f"{self.nome_zona} ({self.get_tipologia_display()})"


class Segnalazione(models.Model):
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='segnalazioni')
    mezzo = models.ForeignKey(Mezzo, on_delete=models.CASCADE, related_name='segnalazioni')
    descrizione = models.TextField(help_text="Descrizione del guasto o del problema")
    data_segnalazione = models.DateTimeField(default=timezone.now)
    risolta = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Mettiamo il mezzo in manutenzione in automatico se la segnalazione è nuova
        if not self.pk and not self.risolta:
            self.mezzo.stato = 'MANUTENZIONE'
            self.mezzo.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Guasto su {self.mezzo} segnalato da {self.utente.nome}"


class Corsa(models.Model):
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='corse')
    mezzo = models.ForeignKey(Mezzo, on_delete=models.CASCADE, related_name='corse')
    inizio = models.DateTimeField(default=timezone.now)
    fine = models.DateTimeField(null=True, blank=True)
    costo_totale = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta: 
        verbose_name_plural = "Corse"

    @classmethod
    def avvia_corsa(cls, utente, mezzo):
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

        return cls.objects.create(utente=utente, mezzo=mezzo)

    def termina_corsa(self, lat_rilascio=None, lng_rilascio=None):
        """Termina la corsa applicando vincoli di geofencing e calcolando il costo."""
        if self.fine is not None:
            raise ValidationError("Questa corsa è già stata terminata.")

        # --- GEOFENCING: Controlla se la posizione di rilascio è in un'Area Vietata ---
        if lat_rilascio and lng_rilascio:
            aree_vietate = Area_Urbana.objects.filter(tipologia='VIETATA')
            for area in aree_vietate:
                # Approssimazione equirettangolare per la distanza
                dy = (float(lat_rilascio) - area.latitudine) * 111000
                dx = (float(lng_rilascio) - area.longitudine) * 80000
                distanza_metri = math.sqrt(dx**2 + dy**2)
                
                if distanza_metri <= area.raggio_metri:
                    raise ValidationError(f"Non puoi terminare la corsa in una zona vietata: {area.nome_zona}")

        self.fine = timezone.now()
        
        durata_secondi = (self.fine - self.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0) # Almeno 1 minuto

        tariffe = {
            'BICI': 0.15,
            'SCOOTER': 0.20,
            'AUTO': 0.35
        }
        
        tariffa_applicata = tariffe.get(self.mezzo.tipo, 0.20)
        
        costo = durata_minuti * tariffa_applicata
        self.costo_totale = round(costo, 2)
        self.save()

        # Libera il mezzo aggiornando la posizione
        self.mezzo.stato = 'DISPONIBILE'
        if lat_rilascio and lng_rilascio:
            self.mezzo.latitudine = float(lat_rilascio)
            self.mezzo.longitudine = float(lng_rilascio)
        self.mezzo.save()

    def __str__(self): 
        return f"Corsa #{self.id} - {self.utente} su {self.mezzo.tipo}"
    

# Aggiungi questa classe in fondo al file models.py
class PosizioneGPS(models.Model):
    """Storico delle posizioni inviate dal veicolo durante una corsa (IF-O04)"""
    corsa = models.ForeignKey(Corsa, on_delete=models.CASCADE, related_name='percorso_gps')
    latitudine = models.FloatField()
    longitudine = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Posizioni GPS"
        ordering = ['timestamp']

    def __str__(self):
        return f"Corsa #{self.corsa.id} - Lat: {self.latitudine}, Lng: {self.longitudine}"