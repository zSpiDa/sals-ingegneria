from django.core.management.base import BaseCommand
from mobility.models import Utente, Mezzo, Area_Urbana, Corsa
# IMPORTANTE: Importiamo la tabella User nativa per la sicurezza
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Popola il database con dati di test realistici'

    def handle(self, *args, **kwargs):
        self.stdout.write("Cancellazione dati esistenti...")
        Corsa.objects.all().delete()
        Utente.objects.all().delete()
        # Puliamo anche la tabella User nativa di Django
        User.objects.filter(is_superuser=False).delete()
        Mezzo.objects.all().delete()
        Area_Urbana.objects.all().delete()

        # 1. UTENTI
        self.stdout.write("Creazione Utenti con credenziali di login...")
        utenti_creati = []
        for i in range(1, 11): # 10 Utenti
            # Prima generiamo l'utente di credenziali per l'autenticazione JWT dello Sviluppatore 3
            user_auth = User.objects.create_user(
                username=f"utente{i}",
                email=f"utente{i}@zootropolis.it",
                password="password123",
                first_name=f"Nome{i}",
                last_name="Test"
            )
            
            # Recuperiamo il relativo profilo Utente (generato automaticamente dai segnali o aggiornato qui)
            # Per evitare conflitti con post_save.py, aggiorniamo i dati del profilo associato
            utente = user_auth.profilo_utente
            utente.documento = f"DOC00{i}"
            utente.patente_verificata = random.choice([True, False])
            utente.sospensione = random.choices([True, False], weights=[1, 9])[0] # 10% di probabilità di sospensione
            utente.save()
            
            utenti_creati.append(utente)

        # 2. MEZZI
        self.stdout.write("Creazione Mezzi...")
        mezzi_creati = []
        tipi = ['BICI', 'AUTO', 'SCOOTER']
        for _ in range(30):
            mezzo = Mezzo.objects.create(
                tipo=random.choice(tipi),
                batteria=random.randint(5, 100),
                latitudine=round(random.uniform(41.11, 41.14), 5), # Coordinate fittizie costiere
                longitudine=round(random.uniform(16.85, 16.89), 5)
            )
            mezzi_creati.append(mezzo)

        # 3. AREE URBANE
        self.stdout.write("Creazione Aree Urbane...")
        Area_Urbana.objects.create(nome_zona="Piazza Garibaldi", tipologia="VIETATA")
        Area_Urbana.objects.create(nome_zona="Parcheggio Stazione Centrale", tipologia="PARCHEGGIO")
        Area_Urbana.objects.create(nome_zona="Lavori Cantiere Lungomare", tipologia="CANTIERE")

        # 4. CORSE (Storico finto)
        self.stdout.write("Generazione Storico Corse...")
        for _ in range(15):
            utente = random.choice([u for u in utenti_creati if not u.sospensione])
            mezzo = random.choice(mezzi_creati)
            
            corsa = Corsa.objects.create(
                utente=utente,
                mezzo=mezzo,
                inizio=timezone.now() - timedelta(days=random.randint(1, 10), minutes=random.randint(10, 120))
            )
            corsa.fine = corsa.inizio + timedelta(minutes=random.randint(5, 60))
            durata_minuti = (corsa.fine - corsa.inizio).total_seconds() / 60
            tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
            corsa.costo_totale = round(durata_minuti * tariffe.get(mezzo.tipo, 0.20), 2)
            corsa.save()

        self.stdout.write(self.style.SUCCESS('Database popolato e test pronti! Ottimo lavoro.'))