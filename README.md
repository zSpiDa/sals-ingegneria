# Smart Mobility - Sistema di Mobilità Urbana Condivisa

Applicazione Django REST + Frontend per la gestione di un sistema di shared mobility (bici, scooter, auto).

## 🎯 Features Sprint 1

### User Features (IF-U*)
- ✅ **IF-U01** - Display Available Vehicles (Lista mezzi disponibili con filtri)
- ✅ **IF-U02** - Reserve Vehicles (Prenotazione mezzo per 15 minuti)
- ✅ **IF-U03** - Estimate Ride Cost (Stima costo al minuto per tipo mezzo)
- ✅ **IF-U04** - Real-time Cost Display (Aggiornamento costo in tempo reale ogni 2 sec)
- ✅ **IF-U05** - End Ride & Final Cost (Termine corsa, calcolo finale, geofencing)
- ✅ **IF-U11** - Display Charging Status (Visualizzazione % batteria per ogni mezzo)
- ✅ **IF-U12** - Unlock Vehicle via App (Sblocco via GPS con validazione <100m)
- ✅ **IF-U13** - Save Payment Method (Salva metodo pagamento: CARTA/PAYPAL/APPLE_PAY/GOOGLE_PAY)

### Operator Features (IF-O*)
- ✅ **IF-O02** - Fleet Distribution Monitoring (Dashboard mappa con tutti i mezzi)
- ✅ **IF-O04** - Detect Position at Ride End (Registrazione GPS a fine corsa + geofencing)

## 📋 Struttura Progetto

```
smart_mobility/
├── manage.py                    # Django entry point
├── requirements.txt             # Python dependencies
├── setup.sh / setup.bat         # Setup scripts
├── config/                      # Django config
│   ├── settings.py             # Django settings (JWT auth, CORS)
│   ├── urls.py                 # Main URL router
│   ├── wsgi.py
│   └── asgi.py
├── mobility/                    # Main app
│   ├── models.py               # Utente, Mezzo, Corsa, Area_Urbana
│   ├── views.py                # ViewSets con 20+ endpoints
│   ├── serializers.py          # DRF serializers
│   ├── urls.py                 # API routes
│   ├── tests.py                # 25+ unit tests
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py    # Populate DB with test data
│   └── migrations/
├── frontend_app/               # Frontend
│   ├── dashboard.html          # Single-page app (33KB)
│   └── index.html
├── db.sqlite3                  # SQLite database
└── venv/                       # Virtual environment

```

## 🚀 Installazione e Setup

### 1️⃣ Windows
```bash
cd smart_mobility
setup.bat
python manage.py runserver
# Apri: http://localhost:8000/frontend_app/dashboard.html
```

### 2️⃣ Linux/Mac
```bash
cd smart_mobility
bash setup.sh
python manage.py runserver
# Apri: http://localhost:8000/frontend_app/dashboard.html
```

### 3️⃣ Manuale
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate.bat

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## 📚 API Endpoints

### Autenticazione
```
POST /api/auth/registrazione/     # Register new user
POST /api/auth/login/              # Get JWT token
```

### Mezzi (Vehicles)
```
GET    /api/mezzi/                    # IF-U01: List available vehicles
GET    /api/mezzi/?tipo=BICI          # Filter by type
POST   /api/mezzi/{id}/prenota/       # IF-U02: Reserve vehicle
GET    /api/mezzi/mappa_flotta/       # IF-O02: Fleet map
GET    /api/mezzi/statistiche/        # Fleet stats
```

### Corse (Rides)
```
POST   /api/corse/avvia/              # IF-U03: Start ride
GET    /api/corse/{id}/costo_corrente/ # IF-U04: Real-time cost
POST   /api/corse/{id}/sblocca/       # IF-U12: Unlock vehicle
POST   /api/corse/{id}/termina/       # IF-U05: End ride + IF-O04: Position
GET    /api/corse/corsa_attiva/       # Get active ride
GET    /api/corse/mie_corse/          # Ride history
GET    /api/corse/statistiche_utente/ # User stats
```

### Aree Urbane (Geofencing)
```
GET    /api/aree-urbane/              # List areas
POST   /api/aree-urbane/valida_punto/ # IF-O04: Validate parking zone
```

### Utenti (Users)
```
GET    /api/utenti/profilo/           # User profile
PUT    /api/utenti/aggiorna_profilo/  # IF-U13: Update payment method
```

## 🧪 Test

```bash
# Esegui tutti i test
python manage.py test

# Test specifico
python manage.py test mobility.tests.CorsaTestCase.test_avvia_corsa

# Con coverage
pip install coverage
coverage run --source='mobility' manage.py test
coverage report
```

## 🔐 Credenziali di Test

Dopo `python manage.py seed_data`, sono disponibili:

| Username | Password | Ruolo |
|----------|----------|-------|
| mario.rossi | Test1234! | User |
| anna.bianchi | Test1234! | User |
| luca.verdi | Test1234! | User |
| admin | admin123 | Admin |

## 💰 Tariffe

| Mezzo | Costo/min |
|-------|-----------|
| BICI | €0.15 |
| SCOOTER | €0.20 |
| AUTO | €0.35 |

## 🌍 Geofencing

Mezzi scaricati (batteria < 10%) non possono essere noleggiati.
Fine corsa in zone vietate (ZTL) rigetta il completamento.

## 📊 Database Schema

### Utente
- user (OneToOne → Django User)
- nome, cognome, documento (unique)
- patente_verificata (required for AUTO)
- sospensione (blocks rental)
- metodo_pagamento
- data_creazione, ultimo_accesso

### Mezzo
- tipo (BICI, SCOOTER, AUTO)
- stato (DISPONIBILE, PRENOTATO, IN_USO, MANUTENZIONE)
- batteria (0-100%)
- latitudine, longitudine
- targa, data_ultimo_check, sbloccato

### Corsa
- utente, mezzo (ForeignKey)
- inizio, fine
- costo_totale
- latitudine_inizio/fine, longitudine_inizio/fine
- metodo_pagamento_utilizzato
- sbloccato

### Area_Urbana
- nome_zona, tipologia (PARCHEGGIO, VIETATA, CANTIERE)
- latitudine_centro, longitudine_centro, raggio_m
- Validazione via formula Haversine

## 🎨 Frontend Features

- **Responsive Design** - Mobile-first, funziona su tutti i device
- **Real-time Updates** - Costo aggiornato ogni 2 secondi
- **GPS Integration** - Geolocalizzazione per sblocco e termine corsa
- **Dark/Light Theme** - Gradient UI moderno
- **Offline Support** - LocalStorage per tokens e dati

## 🔧 Configurazione Avanzata

### JWT Token Lifetime
In `config/settings.py`:
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

### CORS
```python
CORS_ALLOW_ALL_ORIGINS = True  # Development only
```

### Database
Di default SQLite3, cambia in `settings.py` per PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'smart_mobility',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
    }
}
```

## 📱 Roadmap Sprint 2

- ⚠️ WebSocket real-time updates (Django Channels)
- ⚠️ Push notifications (Firebase Cloud Messaging)
- ⚠️ Admin dashboard (Django admin extension)
- ⚠️ Mobile app (React Native / Flutter)
- ⚠️ Payment integration (Stripe/PayPal)
- ⚠️ Email notifications
- ⚠️ Ride rating system

## 🐛 Troubleshooting

### CORS Error
```
"Access to XMLHttpRequest has been blocked by CORS policy"
→ Verifica che 'corsheaders' sia in INSTALLED_APPS
```

### JWT Expired
```
"Token is invalid or expired"
→ Effettua login di nuovo o usa refresh token endpoint
```

### Database locked
```
"database is locked"
→ Chiudi altri processi Django, elimina db.sqlite3 e re-migra
```

## 📞 Support

Per issues e domande: [GitHub Issues](https://github.com/zSpiDa/sals-ingegneria/issues)

---

**Sprint 1 Completion**: ✅ Tutte le 10 features implementate e testate!

Fatto con ❤️ per Smart Mobility
