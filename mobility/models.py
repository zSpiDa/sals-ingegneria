from django.db import models
from django.utils import timezone

class Utente(models.Model):
    # Opzioni per il metodo di pagamento (puoi espanderle in futuro)
    METODI_PAGAMENTO = [
        ('CARTA', 'Carta di Credito/Debito'),
        ('PAYPAL', 'PayPal'),
        ('APPLE_PAY', 'Apple Pay'),
        ('GOOGLE_PAY', 'Google Pay'),
    ]

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
        ('MANUTENZIONE', 'In Manutenzione'), # Aggiunto come 'best practice' per mezzi guasti
    ]

    tipo = models.CharField(max_length=20, choices=TIPI_MEZZO)
    stato = models.CharField(max_length=20, choices=STATI_MEZZO, default='DISPONIBILE')
    batteria = models.IntegerField(help_text="Percentuale di carica (0-100)")
    latitudine = models.FloatField()
    longitudine = models.FloatField()

    class Meta:
        verbose_name_plural = "Mezzi" # Evita che Django scriva "Mezzos" nel pannello admin

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
    # on_delete=models.CASCADE significa che se elimini un utente, elimini anche lo storico delle sue corse. 
    # (In un'app reale si userebbe models.SET_NULL per non perdere i dati contabili, ma per ora va benissimo così).
    utente = models.ForeignKey(Utente, on_delete=models.CASCADE, related_name='corse')
    mezzo = models.ForeignKey(Mezzo, on_delete=models.CASCADE, related_name='corse')
    
    # default=timezone.now registra automaticamente l'ora esatta in cui viene creata la corsa
    inizio = models.DateTimeField(default=timezone.now)
    
    # null=True, blank=True sono fondamentali: quando la corsa inizia, non ha ancora una fine!
    fine = models.DateTimeField(null=True, blank=True)
    
    # Usiamo DecimalField per i soldi per evitare errori di arrotondamento che si hanno con FloatField
    costo_totale = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Corse"

    def __str__(self):
        stato_corsa = "In corso" if not self.fine else f"Terminata - {self.costo_totale}€"
        return f"Corsa #{self.id}: {self.utente.cognome} su {self.mezzo.tipo} [{stato_corsa}]"