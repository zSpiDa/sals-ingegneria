from django.core.management.base import BaseCommand
from mobility.models import Utente, Mezzo, Area_Urbana, Corsa
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Popola il database con dati di test realistici'

    def handle(self, *args, **kwargs):
        self.stdout.write("Cancellazione dati esistenti...")
        Corsa.objects.all().delete()
        Utente.objects.all().delete()
        Mezzo.objects.all().delete()
        Area_Urbana.objects.all().delete()

        # 1. UTENTI
        self.stdout.write("Creazione Utenti...")
        utenti_creati = []
        for i in range(1, 11): # 10 Utenti
            utente = Utente.objects.create(
                nome=f"Utente{i}",
                cognome="Test",
                documento=f"DOC00{i}",
                patente_verificata=random.choice([True, False]),
                sospensione=random.choices([True, False], weights=[1, 9])[0] # 10% di probabilità di sospensione
            )
            utenti_creati.append(utente)

        # 2. MEZZI
        self.stdout.write("Creazione Mezzi...")
        mezzi_creati = []
        tipi = ['BICI', 'AUTO', 'SCOOTER']
        for _ in range(30):
            mezzo = Mezzo.objects.create(
                tipo=random.choice(tipi),
                batteria=random.randint(5, 100),
                latitudine=round(random.uniform(45.45, 45.48), 5), # Milano
                longitudine=round(random.uniform(9.15, 9.20), 5)
            )
            mezzi_creati.append(mezzo)

        # 3. AREE URBANE
        self.stdout.write("Creazione Aree Urbane...")
        Area_Urbana.objects.create(nome_zona="Piazza Duomo", tipologia="VIETATA")
        Area_Urbana.objects.create(nome_zona="Parcheggio Stazione", tipologia="PARCHEGGIO")
        Area_Urbana.objects.create(nome_zona="Lavori Via Roma", tipologia="CANTIERE")

        # 4. CORSE (Storico finto)
        self.stdout.write("Generazione Storico Corse...")
        for _ in range(15):
            utente = random.choice([u for u in utenti_creati if not u.sospensione])
            mezzo = random.choice(mezzi_creati)
            
            # Saltiamo controlli patente/batteria solo per forzare i dati finti nel DB
            corsa = Corsa.objects.create(
                utente=utente,
                mezzo=mezzo,
                inizio=timezone.now() - timedelta(days=random.randint(1, 10), minutes=random.randint(10, 120))
            )
            # Simuliamo la chiusura della corsa (durata da 5 a 60 min)
            corsa.fine = corsa.inizio + timedelta(minutes=random.randint(5, 60))
            durata_minuti = (corsa.fine - corsa.inizio).total_seconds() / 60
            tariffe = {'BICI': 0.15, 'SCOOTER': 0.20, 'AUTO': 0.35}
            corsa.costo_totale = round(durata_minuti * tariffe.get(mezzo.tipo, 0.20), 2)
            corsa.save()

        self.stdout.write(self.style.SUCCESS('Database popolato e test pronti! Ottimo lavoro.'))