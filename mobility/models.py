from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
# 1. IMPORTANTE: Importiamo il modello User nativo di Django per l'autenticazione JWT
from django.contrib.auth.models import User

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

    class Meta:
        verbose_name = "Area Urbana"
        verbose_name_plural = "Aree Urbane"

    def __str__(self):
        return f"{self.nome_zona} ({self.get_tipologia_display()})"


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

    def terminates_corsa(self):
        """Termina la corsa, calcola i minuti e il costo totale."""
        if self.fine is not None:
            raise ValidationError("Questa corsa è già stata terminata.")

        self.fine = timezone.now()
        
        durata_secondi = (self.fine - self.inizio).total_seconds()
        durata_minuti = durata_secondi / 60.0

        tariffe = {
            'BICI': 0.15,
            ('SCOOTER'): 0.20,
            ('AUTO'): 0.35
        }
        
        tariffa_applicata = tariffe.get(self.mezzo.tipo, 0.20)
        
        costo = durata_minuti * tariffa_applicata
        self.costo_totale = round(costo, 2)
        self.save()

        self.mezzo.stato = 'DISPONIBILE'
        self.mezzo.save()

    def __str__(self): 
        return f"Corsa #{self.id} - {self.utente} su {self.mezzo.tipo}"
    