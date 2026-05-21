# 🧪 Sprint 1 Testing Guide - Complete Feature Validation

## 📋 Indice
1. Setup iniziale
2. Test automatici (unit tests)
3. Test manuali con Postman
4. Test del Frontend
5. Test Real-time Features
6. Test Geofencing
7. Test Integration End-to-End
8. Troubleshooting

---

## 🚀 PARTE 1: Setup Iniziale

### Step 1 - Installa dipendenze
```bash
cd smart_mobility
python -m venv venv
venv\Scripts\activate.bat  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### Step 2 - Applica migrazioni
```bash
python manage.py migrate
```

### Step 3 - Popola database con dati di test
```bash
python manage.py seed_data
```

Output atteso:
```
=== Inizio popolazione database ===
✓ Creato utente: mario.rossi
✓ Creato utente: anna.bianchi
✓ Creato utente: luca.verdi
✓ Creato mezzo: Bicicletta Elettrica #1
... (6 mezzi totali)
✓ Creata area: Piazza Libertà (Area di Parcheggio Consentita)
✓ Creata area: ZTL Centro Storico (Zona a Traffico Limitato / Divieto)
=== Database popolato con successo ===
```

### Step 4 - Avvia il server
```bash
python manage.py runserver
```

Output:
```
Django version 5.2.14, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
```

---

## ✅ PARTE 2: Test Automatici (Unit Tests)

### Esegui TUTTI i test
```bash
python manage.py test
```

Risultato atteso:
```
Ran 17 tests in 2.345s
OK
```

### Esegui test specifici per feature

**IF-U01 + IF-U11 (Display Available Vehicles + Battery Status)**
```bash
python manage.py test mobility.tests.MezzoTestCase.test_lista_mezzi_disponibili
```

**IF-U02 (Reserve Vehicles)**
```bash
python manage.py test mobility.tests.MezzoTestCase.test_prenota_mezzo
```

**IF-U03 (Estimate Ride Cost)**
```bash
python manage.py test mobility.tests.CorsaTestCase.test_avvia_corsa
```

**IF-U04 (Real-time Cost Display)**
```bash
python manage.py test mobility.tests.CorsaTestCase.test_costo_corrente_bici
```

**IF-U05 (End Ride & Final Cost)**
```bash
python manage.py test mobility.tests.CorsaTestCase.test_termina_corsa
```

**IF-U12 (Unlock Vehicle via App)**
```bash
python manage.py test mobility.tests.CorsaTestCase.test_sblocca_mezzo_success
python manage.py test mobility.tests.CorsaTestCase.test_sblocca_mezzo_distanza_invalida
```

**IF-U13 (Save Payment Method)**
```bash
python manage.py test mobility.tests.MezzoTestCase  # Implicit in all tests
```

**IF-O02 (Fleet Distribution Monitoring)**
```bash
python manage.py test mobility.tests.MezzoTestCase.test_mappa_flotta
```

**IF-O04 (Detect Position at Ride End)**
```bash
python manage.py test mobility.tests.AreaUrbanaTestCase.test_valida_punto_in_zona_vietata
```

### Esegui con verbose output
```bash
python manage.py test --verbosity=2
```

### Esegui con coverage report
```bash
pip install coverage
coverage run --source='mobility' manage.py test
coverage report
coverage html  # Genera HTML report in htmlcov/
```

---

## 🔧 PARTE 3: Test Manuali con CURL

### 1️⃣ IF-U01 + IF-U11: Display Available Vehicles + Battery

```bash
# Ottenere lista mezzi disponibili
curl http://localhost:8000/api/mezzi/

# Output: Lista di 6 mezzi con batteria
```

**Verifica:**
- ✅ 6 mezzi nel response
- ✅ Campi: tipo, batteria, latitudine, longitudine, stato
- ✅ Tutti hanno stato="DISPONIBILE"
- ✅ Batteria varia tra 20-100%

### 2️⃣ IF-U02: Reserve Vehicle

**Step 1: Ottieni token di login**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"mario.rossi","password":"Test1234!"}'
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {"id": 1, "username": "mario.rossi"}
}
```

Salva il token `access` in una variabile:
```bash
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
```

**Step 2: Prenota mezzo #1**
```bash
curl -X POST http://localhost:8000/api/mezzi/1/prenota/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "status": "Mezzo prenotato con successo per 15 minuti.",
    "mezzo": {
        "id": 1,
        "stato": "PRENOTATO",
        "batteria": 85
    }
}
```

**Verifica:**
- ✅ Status 200 OK
- ✅ Stato cambio a "PRENOTATO"

### 3️⃣ IF-U03: Estimate Ride Cost

**Step 1: Avvia corsa (mezzo #2 - SCOOTER)**
```bash
curl -X POST http://localhost:8000/api/corse/avvia/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mezzo_id": 2,
    "latitudine": 41.1151,
    "longitudine": 16.8644
  }'
```

**Response:**
```json
{
    "corsa": {
        "id": 1,
        "mezzo": 2,
        "inizio": "21/05/2026 16:55:00",
        "fine": null,
        "costo_totale": null,
        "costo_corrente": 0.0
    },
    "stima_costo_al_minuto": 0.20
}
```

Salva corsa ID:
```bash
CORSA_ID=1
```

**Verifica:**
- ✅ stima_costo_al_minuto = 0.20 per SCOOTER
- ✅ Mezzo cambio stato a "IN_USO"
- ✅ fine è null (corsa attiva)

### 4️⃣ IF-U04: Real-time Cost Display

**Aspetta 5 secondi, poi chiama:**
```bash
curl http://localhost:8000/api/corse/$CORSA_ID/costo_corrente/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response (dopo ~5 sec):**
```json
{
    "corsa_id": 1,
    "minuti_trascorsi": 0,
    "secondi_trascorsi": 5,
    "costo_stimato_corrente": 0.20,
    "stato": "in_corso"
}
```

**Ripeti dopo 1 minuto:**
```bash
# Attendi 60 secondi...
curl http://localhost:8000/api/corse/$CORSA_ID/costo_corrente/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response (dopo ~60 sec):**
```json
{
    "corsa_id": 1,
    "minuti_trascorsi": 1,
    "secondi_trascorsi": 60,
    "costo_stimato_corrente": 0.20,
    "stato": "in_corso"
}
```

**Verifica:**
- ✅ minuti_trascorsi incrementa
- ✅ costo_stimato_corrente = minuti * 0.20

### 5️⃣ IF-U12: Unlock Vehicle via App

```bash
curl -X POST http://localhost:8000/api/corse/$CORSA_ID/sblocca/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 41.1151,
    "longitudine": 16.8644
  }'
```

**Response:**
```json
{
    "status": "Mezzo sbloccato con successo!",
    "corsa": {
        "id": 1,
        "sbloccato": true
    }
}
```

**Test: Sblocco da lontano (>100m)**
```bash
curl -X POST http://localhost:8000/api/corse/$CORSA_ID/sblocca/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 41.2000,
    "longitudine": 16.9000
  }'
```

**Response (errore):**
```json
{
    "error": "Sei troppo lontano dal mezzo (4892m). Deve essere entro 100m.",
    "distanza_m": 4892.34
}
```

**Verifica:**
- ✅ Sblocco con GPS vicino: Status 200 OK
- ✅ Sblocco da lontano: Status 400 BAD_REQUEST

### 6️⃣ IF-U05: End Ride & Final Cost

```bash
# Aspetta 2 minuti, poi termina corsa
curl -X POST http://localhost:8000/api/corse/$CORSA_ID/termina/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 41.1160,
    "longitudine": 16.8650
  }'
```

**Response:**
```json
{
    "status": "Corsa terminata con successo!",
    "corsa": {
        "id": 1,
        "fine": "21/05/2026 16:57:00",
        "costo_totale": 0.40,
        "latitudine_fine": 41.1160,
        "longitudine_fine": 16.8650
    }
}
```

**Verifica:**
- ✅ fine non è null
- ✅ costo_totale = 2 minuti * €0.20 = €0.40
- ✅ Mezzo torna a "DISPONIBILE"
- ✅ Coordinate di fine registrate

### 7️⃣ IF-U13: Save Payment Method

```bash
# Ottieni profilo attuale
curl http://localhost:8000/api/utenti/profilo/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
    "id": 1,
    "nome": "Mario",
    "cognome": "Rossi",
    "metodo_pagamento": "CARTA",
    "metodo_pagamento_display": "Carta di Credito/Debito"
}
```

**Cambia metodo di pagamento a PAYPAL:**
```bash
curl -X PUT http://localhost:8000/api/utenti/aggiorna_profilo/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metodo_pagamento": "PAYPAL"}'
```

**Response:**
```json
{
    "metodo_pagamento": "PAYPAL",
    "metodo_pagamento_display": "PayPal"
}
```

**Verifica:**
- ✅ Metodo cambiato a PAYPAL
- ✅ Salvo persistente

### 8️⃣ IF-O02: Fleet Distribution Monitoring

```bash
curl http://localhost:8000/api/mezzi/mappa_flotta/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
    "totale_mezzi": 6,
    "disponibili": 4,
    "in_uso": 1,
    "prenotati": 1,
    "manutenzione": 0,
    "mezzi": [
        {
            "id": 1,
            "tipo": "BICI",
            "stato": "DISPONIBILE",
            "latitudine": 41.1151,
            "longitudine": 16.8644,
            "batteria": 85
        },
        ...
    ]
}
```

**Verifica:**
- ✅ Conteggio totale = 6
- ✅ Distribuzione per stato corretta
- ✅ Tutti i mezzi hanno lat/lng

### 9️⃣ IF-O04: Detect Position at Ride End

```bash
# Testa zona VIETATA
curl -X POST http://localhost:8000/api/aree-urbane/valida_punto/ \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 41.1100,
    "longitudine": 16.8600
  }'
```

**Response (zona vietata):**
```json
{
    "in_zona_vietata": true,
    "zone_vietate": [
        {
            "id": 1,
            "nome_zona": "ZTL Centro Storico",
            "tipologia": "VIETATA"
        }
    ],
    "in_zona_consentita": false,
    "zone_consentite": []
}
```

**Test: Termina corsa in zona vietata**
```bash
# Avvia nuova corsa (mezzo #3)
CORSA_ID2=$(curl -s -X POST http://localhost:8000/api/corse/avvia/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mezzo_id": 3, "latitudine": 41.1151, "longitudine": 16.8644}' \
  | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

# Prova a terminare in zona vietata
curl -X POST http://localhost:8000/api/corse/$CORSA_ID2/termina/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 41.1100,
    "longitudine": 16.8600
  }'
```

**Response (errore - zona vietata):**
```json
{
    "error": "Non è consentito parcheggiare in 'ZTL Centro Storico'"
}
```

**Verifica:**
- ✅ Riconosce zona vietata
- ✅ Blocca termine corsa in zone vietate

---

## 🎨 PARTE 4: Test del Frontend

### Accedi al Dashboard
```
http://localhost:8000/frontend_app/dashboard.html
```

### Test Scenario 1: Login

1. Carica la pagina
2. Vedi form di login
3. Inserisci:
   - Username: `mario.rossi`
   - Password: `Test1234!`
4. Clicca "Accedi"

**Verifica:**
- ✅ Form scompare
- ✅ Dashboard appare
- ✅ Nome utente visibile in alto a destra
- ✅ 6 mezzi visibili nella grid

### Test Scenario 2: Visualizza Veicoli (IF-U01, IF-U11)

1. Mira sulla pagina principale
2. Vedi una griglia di 6 card

**Verifica per ogni mezzo:**
- ✅ Icona mezzo (🚴, 🛴, 🚗)
- ✅ ID mezzo
- ✅ Batteria % con color bar
- ✅ Battery bar color: verde (>20%), arancio (10-20%), rosso (<10%)
- ✅ Stato DISPONIBILE

### Test Scenario 3: Avvia Corsa (IF-U03)

1. Clicca su un mezzo (es: bici #1)
2. Si apre modale con dettagli
3. Clicca "🏁 Avvia Corsa"
4. Permetti geolocalizzazione quando chiesto

**Verifica:**
- ✅ Modale si chiude
- ✅ Messaggio success: "Corsa avviata!"
- ✅ Right panel mostra "Corsa Attiva"
- ✅ Mezzo, batteria, costo visualizzati

### Test Scenario 4: Real-time Cost Display (IF-U04)

1. Dopo aver avviato corsa, guarda il pannello a destra
2. Il costo dovrebbe aggiornare ogni 2 secondi
3. Aspetta 60 secondi

**Verifica:**
- ✅ Costo aumenta ogni 2 sec
- ✅ Tempo trascorso incrementa
- ✅ Calcolo corretto (minuti * €0.15 per bici)
- ✅ Updates fluidi senza refresh pagina

### Test Scenario 5: Sblocca Mezzo (IF-U12)

1. Nel pannello corsa attiva, clicca "🔓 Sblocca"
2. Si apre modale
3. Inserisci coordinate (puoi usare le stesse di avvio):
   - Latitudine: 41.1151
   - Longitudine: 16.8644
4. Clicca "Sblocca"

**Verifica:**
- ✅ Messaggio success: "Mezzo sbloccato!"
- ✅ Bottone "Sblocca" diventa "Sbloccato" (disabled)
- ✅ Modale chiude

**Test errore (distanza >100m):**
1. Riapri modale
2. Inserisci coordinate diverse (es. 41.2000, 16.9000)
3. Clicca "Sblocca"

**Verifica:**
- ✅ Errore: "Sei troppo lontano dal mezzo"
- ✅ Mostra distanza effettiva

### Test Scenario 6: Termina Corsa (IF-U05)

1. Nel pannello corsa, clicca "🏁 Termina"
2. Si apre modale
3. Inserisci coordinate di fine:
   - Latitudine: 41.1160
   - Longitudine: 16.8650
4. Clicca "Termina Corsa"

**Verifica:**
- ✅ Messaggio success con costo finale (es: "€0.75")
- ✅ Pannello torna a "Nessuna corsa attiva"
- ✅ Statistiche aggiornate (corse, speso, tempo)

### Test Scenario 7: Cambia Metodo Pagamento (IF-U13)

1. Apri browser console (F12)
2. Nel pannello profilo (non ancora implementato nel frontend di base)
3. Oppure usa curl command dal terminal

**Verifica:**
- ✅ Metodo persistente

### Test Scenario 8: Visualizza Statistiche

1. Guarda il panel destro "📊 Le Tue Statistiche"

**Verifica:**
- ✅ Totale Corse: incrementa dopo ogni corsa
- ✅ Speso: somma costi
- ✅ Tempo: somma durate

### Test Scenario 9: Storico Corse

1. Scorri nel panel "📜 Storico Corse"

**Verifica:**
- ✅ Mostra corse completate
- ✅ Ordine cronologico inverso (più recenti in alto)

### Test Scenario 10: Logout

1. Clicca bottone "Logout" in alto a destra
2. Pagina ricarica

**Verifica:**
- ✅ Torna a form login
- ✅ Token rimosso da localStorage

---

## ⚡ PARTE 5: Test Real-time Features

### Test: Real-time Cost Polling (2-sec)

**Metodo 1: Browser DevTools**
1. Apri DevTools (F12) → Network
2. Avvia corsa
3. Guarda le richieste GET a `/api/corse/{id}/costo_corrente/`
4. Vedrai una richiesta ogni 2 secondi

**Metodo 2: Network Monitor**
```bash
# In altro terminal, monitora il traffico
tcpdump -i lo -n "port 8000" | grep costo_corrente
```

### Test: Real-time Fleet Status (5-sec)

1. In un browser: Avvia corsa (diventa IN_USO)
2. In altro browser: Aggiorna lista mezzi
3. Vedrai il mezzo cambio stato

---

## 🗺️ PARTE 6: Test Geofencing

### Test Zone Configuration

```bash
# Vedi tutte le zone
curl http://localhost:8000/api/aree-urbane/

# Response mostra 3 zone:
# 1. Piazza Libertà (PARCHEGGIO) - lat 41.1151, lng 16.8644, radius 200m
# 2. Via Manzoni (PARCHEGGIO) - lat 41.1200, lng 16.8700, radius 150m
# 3. ZTL Centro Storico (VIETATA) - lat 41.1100, lng 16.8600, radius 300m
```

### Test: Punti dentro/fuori zone

```bash
# Punto dentro PARCHEGGIO
curl -X POST http://localhost:8000/api/aree-urbane/valida_punto/ \
  -d '{"latitudine": 41.1151, "longitudine": 16.8644}'
# Response: in_zona_consentita: true

# Punto dentro ZTL
curl -X POST http://localhost:8000/api/aree-urbane/valida_punto/ \
  -d '{"latitudine": 41.1100, "longitudine": 16.8600}'
# Response: in_zona_vietata: true

# Punto fuori tutte le zone
curl -X POST http://localhost:8000/api/aree-urbane/valida_punto/ \
  -d '{"latitudine": 41.0000, "longitudine": 16.0000}'
# Response: in_zona_vietata: false, in_zona_consentita: false
```

---

## 🔄 PARTE 7: Test Integration End-to-End

### Scenario Completo: Utente A avvia e termina corsa

```bash
#!/bin/bash

# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"mario.rossi","password":"Test1234!"}' \
  | grep -o '"access":"[^"]*' | cut -d'"' -f4)

echo "✓ Logged in with token: ${TOKEN:0:20}..."

# 2. Get available vehicles
echo "✓ Available vehicles:"
curl -s http://localhost:8000/api/mezzi/ | python -m json.tool | grep -E "id|tipo|batteria"

# 3. Start ride on vehicle #2 (SCOOTER)
CORSA=$(curl -s -X POST http://localhost:8000/api/corse/avvia/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mezzo_id":2,"latitudine":41.1151,"longitudine":16.8644}')

CORSA_ID=$(echo $CORSA | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo "✓ Ride started: $CORSA_ID"

# 4. Check real-time cost
sleep 2
echo "✓ Cost after 2 seconds:"
curl -s http://localhost:8000/api/corse/$CORSA_ID/costo_corrente/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 5. Unlock vehicle
echo "✓ Unlocking vehicle..."
curl -s -X POST http://localhost:8000/api/corse/$CORSA_ID/sblocca/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"latitudine":41.1151,"longitudine":16.8644}' | python -m json.tool

# 6. Wait 60 seconds
echo "⏱️  Waiting 60 seconds for ride cost to accumulate..."
sleep 60

# 7. Check cost again
echo "✓ Cost after 60 seconds:"
curl -s http://localhost:8000/api/corse/$CORSA_ID/costo_corrente/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 8. End ride
echo "✓ Ending ride..."
curl -s -X POST http://localhost:8000/api/corse/$CORSA_ID/termina/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"latitudine":41.1160,"longitudine":16.8650}' | python -m json.tool

# 9. Check user statistics
echo "✓ User statistics:"
curl -s http://localhost:8000/api/corse/statistiche_utente/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 10. Check ride history
echo "✓ Ride history:"
curl -s http://localhost:8000/api/corse/mie_corse/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool | head -30
```

Salva come `test_e2e.sh` e esegui:
```bash
bash test_e2e.sh
```

---

## 🛠️ PARTE 8: Troubleshooting

### Errore: "Token is invalid or expired"
**Soluzione:**
```bash
# Fai login di nuovo
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"mario.rossi","password":"Test1234!"}'
```

### Errore: "Mezzo non disponibile"
**Soluzione:**
```bash
# Controlla stato mezzi
curl http://localhost:8000/api/mezzi/?mostra_tutti=true
# Cerca un mezzo con stato="DISPONIBILE"
```

### Errore: "Batteria troppo bassa"
**Soluzione:**
```bash
# Prova con un mezzo che ha batteria > 10%
# Usa Admin panel per cambiare batteria:
python manage.py shell
>>> from mobility.models import Mezzo
>>> m = Mezzo.objects.get(id=5)
>>> m.batteria = 50
>>> m.save()
```

### Errore: "database is locked"
**Soluzione:**
```bash
# Chiudi tutti i processi Django
# Elimina db.sqlite3
# Re-migra
python manage.py migrate
python manage.py seed_data
```

### Frontend non carica
**Soluzione:**
```bash
# Controlla CORS in settings.py
# Deve avere: CORS_ALLOW_ALL_ORIGINS = True
# Se necessario, aggiungi il tuo domain a ALLOWED_HOSTS
```

---

## 📊 Checklist di Test Finale

### Backend ✅
- [ ] Esegui `python manage.py test` (17/17 passing)
- [ ] Test manuali con curl per tutti gli endpoint
- [ ] Verifica database popoli

### Frontend ✅
- [ ] Login funziona
- [ ] Vehicle grid mostra 6 mezzi
- [ ] Avvia corsa (mezzo cambia stato)
- [ ] Cost display aggiorna ogni 2 sec
- [ ] Unlock vehicle (GPS validation)
- [ ] End ride (calcolo finale)
- [ ] Statistiche aggiornate
- [ ] Logout funziona

### Real-time ✅
- [ ] Cost updates ogni 2 secondi
- [ ] Fleet status aggiorna
- [ ] No console errors

### Geofencing ✅
- [ ] Validazione zona consentita
- [ ] Validazione zona vietata
- [ ] End ride blocca in zone vietate

### Integration ✅
- [ ] Scenario E2E completo
- [ ] Più utenti simultanei
- [ ] Multiple rides overlap

---

## 🎯 Risultato Atteso

**Tutti i test devono passare con ✅**

```
UNIT TESTS:           17/17 ✅
API ENDPOINTS:        20/20 ✅
FRONTEND:             10/10 ✅
REAL-TIME:            3/3 ✅
GEOFENCING:           3/3 ✅
INTEGRATION E2E:      1/1 ✅
TOTAL:                54/54 ✅
```

---

**Enjoy testing! 🧪**
