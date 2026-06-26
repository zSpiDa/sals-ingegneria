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

    # IF-U13: dati di pagamento salvati in forma tokenizzata (mai il numero completo, no CVV)
    pagamento_token = models.CharField(max_length=64, blank=True, default='', help_text="Token restituito dal gateway")
    pagamento_ultime4 = models.CharField(max_length=4, blank=True, default='', help_text="Ultime 4 cifre della carta")
    pagamento_circuito = models.CharField(max_length=20, blank=True, default='', help_text="Es. VISA, Mastercard, PayPal")

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
        ('BLOCCATO', 'Bloccato da Remoto'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPI_MEZZO)
    stato = models.CharField(max_length=20, choices=STATI_MEZZO, default='DISPONIBILE')
    batteria = models.IntegerField(help_text="Percentuale di carica (0-100)")
    latitudine = models.FloatField()
    longitudine = models.FloatField()
    codice_sblocco = models.CharField(max_length=6, unique=True, null=True, blank=True, help_text="Codice di 6 cifre o ID QR Code")
    scadenza_prenotazione = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Mezzi"

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.id} ({self.batteria}% - {self.get_stato_display()})"


class Area_Urbana(models.Model):
    TIPI_AREA = [
        ('PARCHEGGIO', 'Area di Parcheggio Consentita'),
        ('VIETATA', 'Zona a Traffico Limitato / Divieto'),
        ('CANTIERE', 'Cantiere / Strada Chiusa'),
        ('RICARICA', 'Stazione di Ricarica'),
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
    CATEGORIE = [
        ('FRENI', 'Freni'),
        ('GOMME', 'Gomme / Ruote'),
        ('BATTERIA', 'Batteria'),
        ('TELAIO', 'Telaio / Struttura'),
        ('VANDALISMO', 'Vandalismo'),
        ('ALTRO', 'Altro'),
    ]

    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='segnalazioni')
    mezzo = models.ForeignKey(Mezzo, on_delete=models.CASCADE, related_name='segnalazioni')
    categoria = models.CharField(max_length=20, choices=CATEGORIE, default='ALTRO', help_text="Tipo di problema segnalato")
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

    # --- Campi aggiunti nello Sprint 3 ---
    # IF-U08: promozione eventualmente applicata alla corsa
    promozione = models.ForeignKey(
        'Promozione', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='corse'
    )
    # IF-O03: area (di tipo PARCHEGGIO) in cui il mezzo è stato rilasciato
    area_rilascio = models.ForeignKey(
        Area_Urbana, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rilasci'
    )
    # IF-A04 / IF-A02: distanza percorsa, usata per CO2 risparmiata e reportistica
    distanza_km = models.FloatField(default=0.0)

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

    @staticmethod
    def _distanza_metri(lat, lng, area):
        """Distanza approssimata (equirettangolare) in metri tra un punto e il centro di un'area."""
        dy = (float(lat) - area.latitudine) * 111000
        dx = (float(lng) - area.longitudine) * 80000
        return math.sqrt(dx ** 2 + dy ** 2)

    def _calcola_distanza_percorsa(self, durata_minuti):
        """Distanza in km: somma dei punti GPS registrati, o stima da durata e velocità media."""
        punti = list(self.percorso_gps.all())
        if len(punti) >= 2:
            metri = 0.0
            for i in range(1, len(punti)):
                dy = (punti[i].latitudine - punti[i - 1].latitudine) * 111000
                dx = (punti[i].longitudine - punti[i - 1].longitudine) * 80000
                metri += math.sqrt(dx ** 2 + dy ** 2)
            return round(metri / 1000.0, 3)
        # Fallback: stima da durata e velocità media urbana
        velocita = {'BICI': 12.0, 'SCOOTER': 15.0, 'AUTO': 25.0}
        v_media = velocita.get(self.mezzo.tipo, 15.0)
        return round(v_media * (durata_minuti / 60.0), 3)

    def termina_corsa(self, lat_rilascio=None, lng_rilascio=None, promozione=None, guasto_certificato=False):
        """Termina la corsa applicando geofencing, promozione e calcolo costo/distanza.

        - Blocca il rilascio in aree VIETATA o CANTIERE.
        - IF-O03: se esistono aree PARCHEGGIO, il rilascio deve avvenire all'interno di una di esse,
          salvo guasto certificato (guasto_certificato=True).
        - IF-U08: applica un'eventuale promozione valida al costo finale.
        """
        if self.fine is not None:
            raise ValidationError("Questa corsa è già stata terminata.")

        if lat_rilascio and lng_rilascio:
            # 1) Blocco aree non consentite (VIETATA / CANTIERE)
            for area in Area_Urbana.objects.filter(tipologia__in=['VIETATA', 'CANTIERE']):
                if self._distanza_metri(lat_rilascio, lng_rilascio, area) <= area.raggio_metri:
                    raise ValidationError(f"Non puoi terminare la corsa in una zona non consentita: {area.nome_zona}")

            # 2) IF-O03: rilascio consentito solo dentro un'area PARCHEGGIO (se ne esistono)
            aree_parcheggio = list(Area_Urbana.objects.filter(tipologia='PARCHEGGIO'))
            if aree_parcheggio and not guasto_certificato:
                area_trovata = next(
                    (a for a in aree_parcheggio if self._distanza_metri(lat_rilascio, lng_rilascio, a) <= a.raggio_metri),
                    None
                )
                if area_trovata is None:
                    raise ValidationError("Spostati nell'area designata per parcheggiare e terminare la corsa.")
                self.area_rilascio = area_trovata

        self.fine = timezone.now()

        durata_secondi = (self.fine - self.inizio).total_seconds()
        durata_minuti = max(durata_secondi / 60.0, 1.0)  # Almeno 1 minuto

        tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
        tariffa_applicata = tariffe.get(self.mezzo.tipo, 0.20)
        costo = durata_minuti * tariffa_applicata

        # Distanza percorsa (per CO2 e reportistica)
        self.distanza_km = self._calcola_distanza_percorsa(durata_minuti)

        # IF-U08: applicazione promozione
        if promozione is not None:
            if not promozione.is_valida():
                raise ValidationError("Codice promozionale non valido o scaduto.")
            costo = promozione.applica_sconto(costo)
            self.promozione = promozione

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


class Promozione(models.Model):
    """IF-U08: Codice sconto applicabile al costo di una corsa."""
    TIPI_SCONTO = [
        ('PERCENTUALE', 'Sconto percentuale (%)'),
        ('FISSO', 'Sconto fisso (€)'),
    ]

    codice = models.CharField(max_length=20, unique=True, help_text="Codice da inserire in app (es. ESTATE25)")
    tipo_sconto = models.CharField(max_length=20, choices=TIPI_SCONTO, default='PERCENTUALE')
    valore = models.DecimalField(max_digits=10, decimal_places=2, help_text="Es: 20 = 20% oppure 2.50 = 2,50€")
    data_scadenza = models.DateTimeField(help_text="Oltre questa data il codice non è più valido")
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Promozione"
        verbose_name_plural = "Promozioni"

    def is_valida(self):
        """True se la promozione è attiva e non scaduta."""
        return self.attiva and self.data_scadenza >= timezone.now()

    def applica_sconto(self, costo):
        """Restituisce il costo scontato (mai negativo)."""
        costo = float(costo)
        if self.tipo_sconto == 'PERCENTUALE':
            scontato = costo * (1 - float(self.valore) / 100.0)
        else:  # FISSO
            scontato = costo - float(self.valore)
        return round(max(scontato, 0.0), 2)

    def __str__(self):
        return f"{self.codice} ({self.get_tipo_sconto_display()}: {self.valore})"


class ChatTicket(models.Model):
    """IF-U09 / IF-O07: messaggio di assistenza tra Utente e Operatore."""
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='messaggi_chat')
    operatore = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_gestiti',
        help_text="Operatore che ha preso in carico/risposto (vuoto se messaggio dell'utente)"
    )
    messaggio = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    risolto = models.BooleanField(default=False, help_text="True quando il ticket è considerato chiuso")
    da_bot = models.BooleanField(default=False, help_text="True se il messaggio è una risposta automatica del chatbot")

    class Meta:
        verbose_name = "Messaggio Chat / Ticket"
        verbose_name_plural = "Chat & Ticket"
        ordering = ['timestamp']

    @property
    def autore(self):
        """Indica chi ha scritto il messaggio: 'BOT', 'OPERATORE' o 'UTENTE'."""
        if self.da_bot:
            return 'BOT'
        return 'OPERATORE' if self.operatore_id else 'UTENTE'

    def __str__(self):
        return f"[{self.autore}] {self.utente.nome}: {self.messaggio[:30]}"