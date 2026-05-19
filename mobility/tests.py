from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Utente, Mezzo, Corsa

class SmartMobilityTests(TestCase):
    def setUp(self):
        # Setup iniziale: creiamo dati di base per i test
        self.utente_ok = Utente.objects.create(
            nome="Luca", cognome="Bianchi", documento="DOC123", patente_verificata=True
        )
        self.utente_no_patente = Utente.objects.create(
            nome="Anna", cognome="Neri", documento="DOC456", patente_verificata=False
        )
        self.utente_sospeso = Utente.objects.create(
            nome="Marco", cognome="Rossi", documento="DOC789", sospensione=True
        )
        
        self.bici = Mezzo.objects.create(tipo='BICI', stato='DISPONIBILE', batteria=100, latitudine=45.0, longitudine=9.0)
        self.auto = Mezzo.objects.create(tipo='AUTO', stato='DISPONIBILE', batteria=80, latitudine=45.0, longitudine=9.0)
        self.scooter_scarico = Mezzo.objects.create(tipo='SCOOTER', stato='DISPONIBILE', batteria=5, latitudine=45.0, longitudine=9.0)

    def test_avvia_corsa_successo(self):
        """Testa l'avvio corretto di una corsa"""
        corsa = Corsa.avvia_corsa(utente=self.utente_ok, mezzo=self.bici)
        self.assertEqual(corsa.mezzo.stato, 'IN_USO')
        self.assertIsNone(corsa.fine)

    def test_avvia_corsa_utente_sospeso(self):
        """Un utente sospeso non deve poter avviare corse"""
        with self.assertRaises(ValidationError):
            Corsa.avvia_corsa(utente=self.utente_sospeso, mezzo=self.bici)

    def test_avvia_corsa_auto_senza_patente(self):
        """Non si può noleggiare un'auto senza patente verificata"""
        with self.assertRaises(ValidationError):
            Corsa.avvia_corsa(utente=self.utente_no_patente, mezzo=self.auto)

    def test_avvia_corsa_batteria_scarica(self):
        """Non si può noleggiare un mezzo con batteria < 10%"""
        with self.assertRaises(ValidationError):
            Corsa.avvia_corsa(utente=self.utente_ok, mezzo=self.scooter_scarico)

    def test_termina_corsa_calcolo_costo(self):
        """Testa la chiusura della corsa e il calcolo esatto del costo"""
        # Avviamo una corsa con lo scooter (0.20€ al minuto)
        scooter = Mezzo.objects.create(tipo='SCOOTER', stato='DISPONIBILE', batteria=100, latitudine=45.0, longitudine=9.0)
        corsa = Corsa.avvia_corsa(utente=self.utente_ok, mezzo=scooter)
        
        # Simuliamo che siano passati 10 minuti (modificando forzatamente l'inizio)
        corsa.inizio = timezone.now() - timedelta(minutes=10)
        corsa.save()
        
        # Terminiamo la corsa
        corsa.termina_corsa()
        
        # Verifiche
        self.assertIsNotNone(corsa.fine)
        self.assertEqual(corsa.mezzo.stato, 'DISPONIBILE')
        # 10 minuti * 0.20€ = 2.00€
        self.assertEqual(corsa.costo_totale, 2.00)
