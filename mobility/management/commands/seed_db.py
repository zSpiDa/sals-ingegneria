from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from mobility.models import Utente, Mezzo, Area_Urbana
import random

class Command(BaseCommand):
    help = 'Popola il database con dati di test perfetti'

    def handle(self, *args, **kwargs):
        self.stdout.write("Pulizia del database in corso...")
        Mezzo.objects.all().delete()
        Area_Urbana.objects.all().delete()

        # LA MAGIA È QUI: Cancelliamo l'utente di test se esiste già, così non ci sono mai conflitti di ID!
        User.objects.filter(username='utente1').delete()
        Utente.objects.filter(id=1).delete()

        # 1. Creazione dell'Account Base di Django pulito
        auth_user = User.objects.create_user(username='utente1', email='utente1@test.com', password='password123')

        # 2. Creazione del Profilo Utente forzando l'ID 1 (necessario per il nostro frontend)
        Utente.objects.create(
            id=1,
            user=auth_user,
            nome='Mario', 
            cognome='Rossi', 
            documento='DOC123', 
            patente_verificata=True
        )

        # 3. Creazione Aree Urbane 
        Aree = [
            {'nome': 'Parcheggio Porto', 'tipo': 'PARCHEGGIO', 'lat': 41.1270, 'lng': 16.8680, 'r': 150},
            {'nome': 'Divieto Centro Storico', 'tipo': 'DIVIETO', 'lat': 41.1255, 'lng': 16.8720, 'r': 200},
            {'nome': 'Colonnina Stazione', 'tipo': 'RICARICA', 'lat': 41.1171, 'lng': 16.8718, 'r': 100},
        ]
        for a in Aree:
            Area_Urbana.objects.create(nome_zona=a['nome'], tipologia=a['tipo'], latitudine=a['lat'], longitudine=a['lng'], raggio_metri=a['r'])

        # 4. Creazione Flotta Mezzi (Codici univoci perfetti!)
        tipi = ['SCOOTER', 'BICI', 'AUTO']
        for i in range(1, 16):
            Mezzo.objects.create(
                tipo=random.choice(tipi),
                stato='DISPONIBILE',
                latitudine=41.1200 + random.uniform(-0.01, 0.01),
                longitudine=16.8700 + random.uniform(-0.01, 0.01),
                batteria=random.randint(40, 100),
                codice_sblocco=str(i).zfill(6) # Genera: 000001, 000002...
            )

        self.stdout.write(self.style.SUCCESS("Database popolato con successo! Ambiente di test pronto."))