from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from mobility.models import Utente, Mezzo, Area_Urbana
import random

class Command(BaseCommand):
    help = 'Popola il database con dati di test'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Inizio popolazione database ==='))

        # Crea utenti di test
        users_data = [
            {'username': 'mario.rossi', 'email': 'mario@test.it', 'password': 'Test1234!', 'nome': 'Mario', 'cognome': 'Rossi'},
            {'username': 'anna.bianchi', 'email': 'anna@test.it', 'password': 'Test1234!', 'nome': 'Anna', 'cognome': 'Bianchi'},
            {'username': 'luca.verdi', 'email': 'luca@test.it', 'password': 'Test1234!', 'nome': 'Luca', 'cognome': 'Verdi'},
        ]

        for user_data in users_data:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['nome'],
                    last_name=user_data['cognome']
                )
                Utente.objects.create(
                    user=user,
                    nome=user_data['nome'],
                    cognome=user_data['cognome'],
                    documento=f"DOCUMENTO{user.id:03d}",
                    patente_verificata=True if user.id > 1 else False,
                    metodo_pagamento='CARTA' if user.id % 2 == 0 else 'PAYPAL'
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Creato utente: {user_data['username']}"))

        # Crea mezzi
        tipi_mezzi = [('BICI', 'Bicicletta Elettrica'), ('SCOOTER', 'E-Scooter'), ('AUTO', 'Automobile')]
        coordinate_test = [
            (41.1151, 16.8644),  # Bari centro
            (41.1200, 16.8700),
            (41.1100, 16.8600),
            (41.1160, 16.8680),
            (41.1180, 16.8620),
        ]

        for i, (tipo, _) in enumerate(tipi_mezzi * 2):  # 6 mezzi totali
            if not Mezzo.objects.filter(id=i+1).exists():
                mezzo = Mezzo.objects.create(
                    tipo=tipo,
                    stato='DISPONIBILE',
                    batteria=random.randint(20, 100),
                    latitudine=coordinate_test[i % 5][0],
                    longitudine=coordinate_test[i % 5][1],
                    targa=f"BRI{1000+i}"
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Creato mezzo: {mezzo} - Batteria: {mezzo.batteria}%"))

        # Crea aree urbane
        aree_data = [
            {'nome': 'Piazza Libertà', 'tipologia': 'PARCHEGGIO', 'lat': 41.1151, 'lng': 16.8644, 'raggio': 200},
            {'nome': 'Via Manzoni', 'tipologia': 'PARCHEGGIO', 'lat': 41.1200, 'lng': 16.8700, 'raggio': 150},
            {'nome': 'ZTL Centro Storico', 'tipologia': 'VIETATA', 'lat': 41.1100, 'lng': 16.8600, 'raggio': 300},
        ]

        for area_data in aree_data:
            if not Area_Urbana.objects.filter(nome_zona=area_data['nome']).exists():
                area = Area_Urbana.objects.create(
                    nome_zona=area_data['nome'],
                    tipologia=area_data['tipologia'],
                    latitudine_centro=area_data['lat'],
                    longitudine_centro=area_data['lng'],
                    raggio_m=area_data['raggio']
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Creata area: {area.nome_zona} ({area.get_tipologia_display()})"))

        self.stdout.write(self.style.SUCCESS('=== Database popolato con successo ==='))
