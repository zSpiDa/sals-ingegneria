# 🧪 Quick Testing Reference

## 🚀 Quick Start (1 minuto)

### Terminal 1 - Avvia server
```bash
cd smart_mobility
python manage.py runserver
```

### Terminal 2 - Esegui test automatici
```bash
cd smart_mobility
python run_tests.py
```

**Risultato atteso**: ✅ ALL TESTS PASSED!

---

## 🔨 Unit Tests

### Esegui TUTTI i test
```bash
python manage.py test
```

### Esegui test per feature

| Feature | Comando |
|---------|---------|
| **IF-U01** (Vehicle List) | `python manage.py test mobility.tests.MezzoTestCase.test_lista_mezzi_disponibili` |
| **IF-U02** (Reservation) | `python manage.py test mobility.tests.MezzoTestCase.test_prenota_mezzo` |
| **IF-U03** (Cost Estimate) | `python manage.py test mobility.tests.CorsaTestCase.test_avvia_corsa` |
| **IF-U04** (Real-time Cost) | `python manage.py test mobility.tests.CorsaTestCase.test_costo_corrente_bici` |
| **IF-U05** (End Ride) | `python manage.py test mobility.tests.CorsaTestCase.test_termina_corsa` |
| **IF-U11** (Battery) | `python manage.py test mobility.tests.MezzoTestCase.test_lista_mezzi_disponibili` |
| **IF-U12** (Unlock) | `python manage.py test mobility.tests.CorsaTestCase.test_sblocca_mezzo_success` |
| **IF-U13** (Payment) | `python manage.py test mobility.tests` |
| **IF-O02** (Fleet Monitor) | `python manage.py test mobility.tests.MezzoTestCase.test_mappa_flotta` |
| **IF-O04** (Geofencing) | `python manage.py test mobility.tests.AreaUrbanaTestCase.test_valida_punto_in_zona_vietata` |

---

## 🖥️ API Tests (CURL)

### 1. Login
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"mario.rossi","password":"Test1234!"}' | jq -r '.access')

echo "Token: $TOKEN"
```

### 2. List Vehicles (IF-U01, IF-U11)
```bash
curl http://localhost:8000/api/mezzi/ | jq
```

### 3. Reserve Vehicle (IF-U02)
```bash
curl -X POST http://localhost:8000/api/mezzi/1/prenota/ \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Start Ride (IF-U03)
```bash
RIDE=$(curl -s -X POST http://localhost:8000/api/corse/avvia/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mezzo_id":2,"latitudine":41.1151,"longitudine":16.8644}' | jq -r '.corsa.id')

echo "Ride ID: $RIDE"
```

### 5. Check Real-time Cost (IF-U04)
```bash
curl http://localhost:8000/api/corse/$RIDE/costo_corrente/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 6. Unlock Vehicle (IF-U12)
```bash
curl -X POST http://localhost:8000/api/corse/$RIDE/sblocca/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"latitudine":41.1151,"longitudine":16.8644}'
```

### 7. End Ride (IF-U05)
```bash
curl -X POST http://localhost:8000/api/corse/$RIDE/termina/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"latitudine":41.1160,"longitudine":16.8650}' | jq
```

### 8. Change Payment Method (IF-U13)
```bash
curl -X PUT http://localhost:8000/api/utenti/aggiorna_profilo/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metodo_pagamento":"PAYPAL"}' | jq
```

### 9. Fleet Monitoring (IF-O02)
```bash
curl http://localhost:8000/api/mezzi/mappa_flotta/ | jq
```

### 10. Geofencing Validation (IF-O04)
```bash
curl -X POST http://localhost:8000/api/aree-urbane/valida_punto/ \
  -H "Content-Type: application/json" \
  -d '{"latitudine":41.1151,"longitudine":16.8644}' | jq
```

---

## 🌐 Frontend Test

### Accedi al Dashboard
```
http://localhost:8000/frontend_app/dashboard.html
```

### Test Scenario
1. **Login**: mario.rossi / Test1234! ✅
2. **Select Vehicle**: Click on a bike card ✅
3. **Start Ride**: Click "🏁 Avvia Corsa" ✅
4. **Watch Cost**: Observe cost update every 2 sec ✅
5. **Unlock**: Click "🔓 Sblocca" button ✅
6. **Wait 60 sec**: Let cost accumulate ✅
7. **End Ride**: Click "🏁 Termina" ✅
8. **Verify Stats**: Check updated statistics ✅

---

## 📊 Test Coverage

```
UNIT TESTS:           ✅ 17 tests
API ENDPOINTS:        ✅ 20+ endpoints  
FRONTEND:             ✅ Single-page app
REAL-TIME:            ✅ 2-sec polling
GEOFENCING:           ✅ Haversine validation
INTEGRATION:          ✅ Full E2E scenario
```

---

## 🔍 Debugging

### Check Active Ride
```bash
curl http://localhost:8000/api/corse/corsa_attiva/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Check User Stats
```bash
curl http://localhost:8000/api/corse/statistiche_utente/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### View All Rides
```bash
curl http://localhost:8000/api/corse/mie_corse/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Check Database
```bash
python manage.py dbshell
sqlite> SELECT COUNT(*) FROM mobility_corsa;
sqlite> SELECT * FROM mobility_mezzo WHERE id=1;
```

---

## ✅ Final Checklist

- [ ] Run `python manage.py test` → All 17 passing
- [ ] Run `python run_tests.py` → All tests passing
- [ ] Access frontend → http://localhost:8000/frontend_app/dashboard.html
- [ ] Complete login flow
- [ ] Start a ride and verify cost updates
- [ ] End ride and verify calculation
- [ ] Check statistics updated

---

## 🎯 Expected Results

**After all tests:**
- ✅ 17 Unit tests passing
- ✅ 10 Features working
- ✅ Frontend responsive
- ✅ Real-time updates working
- ✅ All validations in place
- ✅ Production-ready code

---

**Duration**: ~5-10 minutes for full test suite

**Status**: Ready for production deployment! 🚀
