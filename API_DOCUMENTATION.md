# Smart Mobility - API Documentation Sprint 1

## Base URL
```
http://localhost:8000/api
```

## Authentication
Tutti gli endpoint (tranne auth e mezzi pubblici) richiedono:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 🔐 Auth Endpoints

### POST /api/auth/registrazione/
**Registrazione nuovo utente**

Request:
```json
{
    "username": "mario.rossi",
    "email": "mario@test.it",
    "password": "SecurePass123",
    "nome": "Mario",
    "cognome": "Rossi",
    "documento": "RSSMRA80A01H501Y"
}
```

Response:
```json
{
    "id": 1,
    "username": "mario.rossi",
    "email": "mario@test.it",
    "profilo": {
        "id": 1,
        "nome": "Mario",
        "cognome": "Rossi",
        "documento": "RSSMRA80A01H501Y",
        "patente_verificata": false,
        "sospensione": false,
        "metodo_pagamento": "CARTA"
    }
}
```

### POST /api/auth/login/
**Login e ottenimento JWT token**

Request:
```json
{
    "username": "mario.rossi",
    "password": "SecurePass123"
}
```

Response:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "id": 1,
        "username": "mario.rossi",
        "email": "mario@test.it"
    }
}
```

---

## 🚗 Mezzi Endpoints (IF-U01, IF-U11, IF-O02)

### GET /api/mezzi/
**Lista mezzi disponibili** (IF-U01, IF-U11)

Query Parameters:
- `mostra_tutti=true` - Mostra tutti i mezzi (default: solo DISPONIBILI)
- `tipo=BICI` - Filtro per tipo (BICI, SCOOTER, AUTO)
- `filtro_batteria=LOW` - Batteria < 20%
- `filtro_batteria=CRITICAL` - Batteria < 10%

Response:
```json
[
    {
        "id": 1,
        "tipo": "BICI",
        "tipo_display": "Bicicletta Elettrica",
        "stato": "DISPONIBILE",
        "stato_display": "Disponibile",
        "latitudine": 41.1151,
        "longitudine": 16.8644,
        "batteria": 85,
        "stato_critico": false,
        "targa": "BRI1000",
        "sbloccato": false,
        "distanza_km": null
    }
]
```

### GET /api/mezzi/mappa_flotta/
**Mappa distribuzione flotta** (IF-O02)

Response:
```json
{
    "totale_mezzi": 6,
    "disponibili": 4,
    "in_uso": 1,
    "prenotati": 1,
    "manutenzione": 0,
    "mezzi": [...]
}
```

### GET /api/mezzi/statistiche/
**Statistiche flotta**

Response:
```json
{
    "totale_mezzi": 6,
    "disponibili": 4,
    "percentuale_disponibilita": 66.67,
    "per_tipo": {
        "BICI": 2,
        "SCOOTER": 2,
        "AUTO": 2
    }
}
```

### POST /api/mezzi/{id}/prenota/
**Prenotazione mezzo** (IF-U02)

Request: (empty body)

Response:
```json
{
    "status": "Mezzo prenotato con successo per 15 minuti.",
    "mezzo": {...}
}
```

---

## 🏁 Corse Endpoints (IF-U03 a IF-U05, IF-U12, IF-O04)

### POST /api/corse/avvia/
**Avvia nuova corsa** (IF-U03)

Request:
```json
{
    "mezzo_id": 1,
    "latitudine": 41.1151,
    "longitudine": 16.8644
}
```

Response:
```json
{
    "corsa": {
        "id": 5,
        "utente": 1,
        "mezzo": 1,
        "inizio": "21/05/2026 16:42:14",
        "fine": null,
        "costo_totale": null,
        "costo_corrente": 0.0,
        "latitudine_inizio": 41.1151,
        "longitudine_inizio": 16.8644,
        "latitudine_fine": null,
        "longitudine_fine": null,
        "metodo_pagamento_utilizzato": "CARTA",
        "sbloccato": false,
        "mezzo_dettagli": {...}
    },
    "stima_costo_al_minuto": 0.15
}
```

Errori:
- 400: Mezzo non disponibile
- 400: Batteria < 10%
- 400: Auto senza patente verificata
- 400: Utente sospeso

### GET /api/corse/{id}/costo_corrente/
**Costo in tempo reale** (IF-U04)

Response:
```json
{
    "corsa_id": 5,
    "minuti_trascorsi": 5,
    "secondi_trascorsi": 312,
    "costo_stimato_corrente": 0.75,
    "stato": "in_corso"
}
```

### POST /api/corse/{id}/sblocca/
**Sblocca mezzo via GPS** (IF-U12)

Request:
```json
{
    "latitudine": 41.1151,
    "longitudine": 16.8644
}
```

Response:
```json
{
    "status": "Mezzo sbloccato con successo!",
    "corsa": {...}
}
```

Validazioni:
- Distanza <= 100m dal mezzo
- Mezzo non già sbloccato

### POST /api/corse/{id}/termina/
**Termina corsa** (IF-U05, IF-O04)

Request:
```json
{
    "latitudine": 41.1160,
    "longitudine": 16.8650
}
```

Response:
```json
{
    "status": "Corsa terminata con successo!",
    "corsa": {
        "id": 5,
        "fine": "21/05/2026 16:47:14",
        "costo_totale": 1.50,
        "latitudine_fine": 41.1160,
        "longitudine_fine": 16.8650
    }
}
```

Validazioni:
- Posizione non in zona vietata (ZTL)
- Calcolo automatico costo basato su durata

### GET /api/corse/corsa_attiva/
**Corsa attiva utente loggato**

Response:
```json
{
    "corsa_attiva": true,
    "corsa": {...}
}
```

### GET /api/corse/mie_corse/
**Storico corse utente**

Query Parameters:
- `page=1` - Paginazione (20 per pagina)

Response:
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/corse/mie_corse/?page=2",
    "previous": null,
    "results": [...]
}
```

### GET /api/corse/statistiche_utente/
**Statistiche personali utente**

Response:
```json
{
    "totale_corse": 25,
    "corse_completate": 24,
    "costo_totale_speso": 45.50,
    "durata_totale_minuti": 240,
    "costo_medio_corsa": 1.90,
    "mezzo_preferito": {
        "mezzo__tipo": "BICI",
        "id__count": 12
    }
}
```

---

## 👤 Utenti Endpoints (IF-U13)

### GET /api/utenti/profilo/
**Profilo utente loggato**

Response:
```json
{
    "id": 1,
    "user": {
        "id": 1,
        "username": "mario.rossi",
        "email": "mario@test.it",
        "first_name": "Mario",
        "last_name": "Rossi"
    },
    "nome": "Mario",
    "cognome": "Rossi",
    "documento": "RSSMRA80A01H501Y",
    "patente_verificata": false,
    "sospensione": false,
    "metodo_pagamento": "CARTA",
    "metodo_pagamento_display": "Carta di Credito/Debito",
    "data_creazione": "2026-05-21T14:30:00Z",
    "ultimo_accesso": "2026-05-21T16:42:00Z"
}
```

### PUT /api/utenti/aggiorna_profilo/
**Aggiorna profilo utente loggato** (IF-U13)

Request:
```json
{
    "metodo_pagamento": "PAYPAL",
    "patente_verificata": true
}
```

Response: (same as GET profilo)

### PUT /api/utenti/{id}/cambia_metodo_pagamento/
**Cambia metodo pagamento** (IF-U13)

Request:
```json
{
    "metodo_pagamento": "APPLE_PAY"
}
```

Valori accettati:
- `CARTA` - Carta di Credito/Debito
- `PAYPAL` - PayPal
- `APPLE_PAY` - Apple Pay
- `GOOGLE_PAY` - Google Pay

---

## 🗺️ Aree Urbane Endpoints (IF-O04)

### GET /api/aree-urbane/
**Lista aree urbane (geofences)**

Response:
```json
[
    {
        "id": 1,
        "nome_zona": "Piazza Libertà",
        "tipologia": "PARCHEGGIO",
        "tipologia_display": "Area di Parcheggio Consentita",
        "latitudine_centro": 41.1151,
        "longitudine_centro": 16.8644,
        "raggio_m": 200
    }
]
```

### POST /api/aree-urbane/valida_punto/
**Valida punto GPS** (IF-O04)

Request:
```json
{
    "latitudine": 41.1151,
    "longitudine": 16.8644
}
```

Response:
```json
{
    "in_zona_vietata": false,
    "zone_vietate": [],
    "in_zona_consentita": true,
    "zone_consentite": [
        {
            "id": 1,
            "nome_zona": "Piazza Libertà",
            "tipologia": "PARCHEGGIO"
        }
    ]
}
```

---

## ⚠️ Codici di Errore

| Code | Message | Soluzione |
|------|---------|-----------|
| 400 | Bad Request | Verifica parametri richiesta |
| 401 | Unauthorized | Effettua login, token scaduto |
| 403 | Forbidden | Permessi insufficienti |
| 404 | Not Found | Risorsa non esiste |
| 500 | Internal Server Error | Errore server |

---

## 🧪 Curl Examples

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"mario.rossi","password":"Test1234!"}'
```

### Lista Mezzi
```bash
curl http://localhost:8000/api/mezzi/
```

### Avvia Corsa
```bash
curl -X POST http://localhost:8000/api/corse/avvia/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"mezzo_id":1,"latitudine":41.1151,"longitudine":16.8644}'
```

### Costo Real-time
```bash
curl http://localhost:8000/api/corse/5/costo_corrente/ \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 📊 Tariffe

| Mezzo | Prezzo/minuto |
|-------|---------------|
| 🚴 BICI | €0.15 |
| 🛴 SCOOTER | €0.20 |
| 🚗 AUTO | €0.35 |

**Tempo minimo**: 1 minuto (arrotondato per eccesso)

---

## 🔒 JWT Token

Formato: `Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...`

Durata:
- **Access Token**: 60 minuti
- **Refresh Token**: 7 giorni

Per rinnovare access token (da implementare in Sprint 2):
```
POST /api/token/refresh/
```

---

Ultima aggiornamento: Sprint 1 - 21/05/2026
