from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from mobility.models import Utente, Mezzo, Area_Urbana, Corsa
from datetime import timedelta


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registrazione_utente(self):
        """Test registrazione di un nuovo utente."""
        data = {
            'username': 'test.user',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'nome': 'Test',
            'cognome': 'User',
            'documento': 'TESTDOC001'
        }
        response = self.client.post('/api/auth/registrazione/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'test.user')

    def test_login_utente(self):
        """Test login di un utente registrato."""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@test.com'
        )
        Utente.objects.create(
            user=user,
            nome='Test',
            cognome='User',
            documento='TESTDOC001'
        )
        
        data = {'username': 'testuser', 'password': 'TestPass123!'}
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class MezzoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mezzo_bici = Mezzo.objects.create(
            tipo='BICI',
            stato='DISPONIBILE',
            batteria=80,
            latitudine=41.1151,
            longitudine=16.8644
        )
        self.mezzo_auto = Mezzo.objects.create(
            tipo='AUTO',
            stato='DISPONIBILE',
            batteria=60,
            latitudine=41.1200,
            longitudine=16.8700
        )

    def test_lista_mezzi_disponibili(self):
        """Test GET /api/mezzi/ - Lista mezzi disponibili."""
        response = self.client.get('/api/mezzi/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_prenota_mezzo(self):
        """Test POST /api/mezzi/{id}/prenota/ - Prenotazione mezzo."""
        response = self.client.post(f'/api/mezzi/{self.mezzo_bici.id}/prenota/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mezzo_bici.refresh_from_db()
        self.assertEqual(self.mezzo_bici.stato, 'PRENOTATO')

    def test_mappa_flotta(self):
        """Test GET /api/mezzi/mappa_flotta/ - Mappa flotta."""
        response = self.client.get('/api/mezzi/mappa_flotta/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totale_mezzi'], 2)
        self.assertEqual(response.data['disponibili'], 2)

    def test_filtro_batteria_bassa(self):
        """Test filtro batteria bassa."""
        Mezzo.objects.create(
            tipo='SCOOTER',
            stato='DISPONIBILE',
            batteria=5,
            latitudine=41.1151,
            longitudine=16.8644
        )
        response = self.client.get('/api/mezzi/?filtro_batteria=CRITICAL')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class CorsaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@test.com'
        )
        self.utente = Utente.objects.create(
            user=self.user,
            nome='Test',
            cognome='User',
            documento='TESTDOC001',
            patente_verificata=True
        )
        self.client.force_authenticate(user=self.user)
        
        self.mezzo_bici = Mezzo.objects.create(
            tipo='BICI',
            stato='DISPONIBILE',
            batteria=80,
            latitudine=41.1151,
            longitudine=16.8644
        )
        self.mezzo_auto = Mezzo.objects.create(
            tipo='AUTO',
            stato='DISPONIBILE',
            batteria=60,
            latitudine=41.1200,
            longitudine=16.8700
        )

    def test_avvia_corsa(self):
        """Test POST /api/corse/avvia/ - Avvio corsa."""
        data = {
            'mezzo_id': self.mezzo_bici.id,
            'latitudine': 41.1151,
            'longitudine': 16.8644
        }
        response = self.client.post('/api/corse/avvia/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('corsa', response.data)
        self.mezzo_bici.refresh_from_db()
        self.assertEqual(self.mezzo_bici.stato, 'IN_USO')

    def test_costo_corrente_bici(self):
        """Test GET /api/corse/{id}/costo_corrente/ - Costo real-time."""
        corsa = Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now() - timedelta(minutes=5),
            metodo_pagamento_utilizzato='CARTA'
        )
        response = self.client.get(f'/api/corse/{corsa.id}/costo_corrente/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(float(response.data['costo_stimato_corrente']), 0.75, places=1)

    def test_termina_corsa(self):
        """Test POST /api/corse/{id}/termina/ - Termine corsa."""
        corsa = Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now() - timedelta(minutes=10),
            metodo_pagamento_utilizzato='CARTA'
        )
        
        data = {
            'latitudine': 41.1160,
            'longitudine': 16.8650
        }
        response = self.client.post(f'/api/corse/{corsa.id}/termina/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        corsa.refresh_from_db()
        self.assertIsNotNone(corsa.fine)
        self.assertEqual(corsa.mezzo.stato, 'DISPONIBILE')
        self.assertGreater(float(corsa.costo_totale), 0)

    def test_sblocca_mezzo_success(self):
        """Test POST /api/corse/{id}/sblocca/ - Sblocco mezzo con GPS valido."""
        corsa = Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now(),
            metodo_pagamento_utilizzato='CARTA'
        )
        
        data = {
            'latitudine': 41.1151,
            'longitudine': 16.8644
        }
        response = self.client.post(f'/api/corse/{corsa.id}/sblocca/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        corsa.refresh_from_db()
        self.assertTrue(corsa.sbloccato)

    def test_sblocca_mezzo_distanza_invalida(self):
        """Test sblocco mezzo da lontano (>100m)."""
        corsa = Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now(),
            metodo_pagamento_utilizzato='CARTA'
        )
        
        data = {
            'latitudine': 41.1300,
            'longitudine': 16.8800
        }
        response = self.client.post(f'/api/corse/{corsa.id}/sblocca/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_corsa_attiva(self):
        """Test GET /api/corse/corsa_attiva/ - Corsa attiva."""
        corsa = Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now(),
            metodo_pagamento_utilizzato='CARTA'
        )
        
        response = self.client.get('/api/corse/corsa_attiva/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['corsa_attiva'])
        self.assertEqual(response.data['corsa']['id'], corsa.id)

    def test_mie_corse(self):
        """Test GET /api/corse/mie_corse/ - Storico corse."""
        Corsa.objects.create(
            utente=self.utente,
            mezzo=self.mezzo_bici,
            inizio=timezone.now() - timedelta(days=1),
            fine=timezone.now() - timedelta(hours=23, minutes=50),
            costo_totale=1.50,
            metodo_pagamento_utilizzato='CARTA'
        )
        
        response = self.client.get('/api/corse/mie_corse/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class AreaUrbanaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area_parcheggio = Area_Urbana.objects.create(
            nome_zona='Piazza Libertà',
            tipologia='PARCHEGGIO',
            latitudine_centro=41.1151,
            longitudine_centro=16.8644,
            raggio_m=200
        )
        self.area_vietata = Area_Urbana.objects.create(
            nome_zona='ZTL Centro',
            tipologia='VIETATA',
            latitudine_centro=41.1100,
            longitudine_centro=16.8600,
            raggio_m=300
        )

    def test_valida_punto_in_area(self):
        """Test validazione punto dentro area."""
        data = {
            'latitudine': 41.1151,
            'longitudine': 16.8644
        }
        response = self.client.post('/api/aree-urbane/valida_punto/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['in_zona_consentita'])

    def test_valida_punto_in_zona_vietata(self):
        """Test validazione punto in zona vietata."""
        data = {
            'latitudine': 41.1100,
            'longitudine': 16.8600
        }
        response = self.client.post('/api/aree-urbane/valida_punto/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['in_zona_vietata'])


class ValidazioniTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@test.com'
        )
        self.utente = Utente.objects.create(
            user=self.user,
            nome='Test',
            cognome='User',
            documento='TESTDOC001',
            patente_verificata=False
        )
        self.client.force_authenticate(user=self.user)

    def test_non_avvia_corsa_senza_patente_auto(self):
        """Test non avvia corsa auto senza patente."""
        mezzo_auto = Mezzo.objects.create(
            tipo='AUTO',
            stato='DISPONIBILE',
            batteria=80,
            latitudine=41.1151,
            longitudine=16.8644
        )
        
        data = {
            'mezzo_id': mezzo_auto.id,
            'latitudine': 41.1151,
            'longitudine': 16.8644
        }
        response = self.client.post('/api/corse/avvia/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_avvia_corsa_batteria_bassa(self):
        """Test non avvia corsa con batteria < 10%."""
        mezzo_scarica = Mezzo.objects.create(
            tipo='BICI',
            stato='DISPONIBILE',
            batteria=5,
            latitudine=41.1151,
            longitudine=16.8644
        )
        
        data = {
            'mezzo_id': mezzo_scarica.id,
            'latitudine': 41.1151,
            'longitudine': 16.8644
        }
        response = self.client.post('/api/corse/avvia/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

