from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from mobility.models import Utente, Mezzo, Area_Urbana
import random

class Command(BaseCommand):
    help = 'Popola il database con dati di test perfetti'

    def handle(self, *args, **kwargs):
        self.stdout.write("Pulizia vecchi dati Mezzi e Aree in corso...")
        Mezzo.objects.all().delete()
        Area_Urbana.objects.all().delete()

        # 1. Recuperiamo o creiamo l'utente base (senza cancellarlo per non rompere chiavi esterne)
        auth_user, created = User.objects.get_or_create(
            username='utente1',
            defaults={'email': 'utente1@test.com'}
        )
        if created:
            auth_user.set_password('password123')
            auth_user.save()

        # 2. IL TRUCCO: Recuperiamo il profilo (che sia stato creato dal Signal o da noi)
        profilo, profile_created = Utente.objects.get_or_create(user=auth_user)
        
        # Aggiorniamo i dati del profilo pacificamente
        profilo.nome = 'Mario'
        profilo.cognome = 'Rossi'
        profilo.documento = 'DOC123'
        profilo.patente_verificata = True
        profilo.save()

        # Salviamo l'ID reale che il database gli ha assegnato
        id_reale = profilo.id

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
                codice_sblocco=str(i).zfill(6)
            )

        self.stdout.write(self.style.SUCCESS("✅ Database popolato con successo! Ambiente di test pronto."))
        self.stdout.write(self.style.WARNING(f"⚠️ ATTENZIONE: L'ID del tuo utente nel database è: {id_reale}"))
        self.stdout.write(self.style.WARNING(f"Se in index.html (riga 202) ID_UTENTE_ATTUALE non è {id_reale}, aggiornalo!"))