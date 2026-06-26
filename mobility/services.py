"""
Servizi di dominio per lo Sprint 3 (Blocco 3).

Implementazioni DETERMINISTICHE/SIMULATE, senza chiamate a servizi esterni:
non richiedono chiavi API e non possono fallire durante una demo.
Sono strutturate come adapter sostituibili: domani il corpo dei metodi può
chiamare OSRM/Google (routing), OpenWeatherMap (meteo) o Stripe (pagamenti)
mantenendo identica la firma usata dalle viste.
"""
import math
import hashlib


def _distanza_km(p1, p2):
    """Distanza approssimata (equirettangolare) in km tra due punti [lat, lng]."""
    dy = (p1[0] - p2[0]) * 111.0
    dx = (p1[1] - p2[1]) * 80.0
    return math.sqrt(dx ** 2 + dy ** 2)


class RoutingService:
    """IF-U06: calcolo del percorso più breve evitando le zone vietate.

    Genera una polilinea tra origine e destinazione; se un punto intermedio
    cade dentro un'area vietata/cantiere, lo sposta all'esterno (detour).
    """

    VELOCITA_KMH = {'BICI': 12.0, 'SCOOTER': 15.0, 'AUTO': 25.0}

    def calcola_percorso(self, origine, destinazione, tipo_mezzo='SCOOTER', aree_vietate=None):
        aree_vietate = aree_vietate or []
        n_punti = 20
        punti = []
        for i in range(n_punti + 1):
            t = i / n_punti
            lat = origine[0] + (destinazione[0] - origine[0]) * t
            lng = origine[1] + (destinazione[1] - origine[1]) * t
            lat, lng = self._evita_zone([lat, lng], aree_vietate)
            punti.append([round(lat, 6), round(lng, 6)])

        distanza = 0.0
        for i in range(1, len(punti)):
            distanza += _distanza_km(punti[i - 1], punti[i])

        velocita = self.VELOCITA_KMH.get(tipo_mezzo, 15.0)
        durata_min = round((distanza / velocita) * 60.0, 1)

        return {
            'punti': punti,
            'distanza_km': round(distanza, 3),
            'durata_minuti': durata_min,
            'tipo_mezzo': tipo_mezzo,
        }

    @staticmethod
    def _evita_zone(punto, aree_vietate):
        """Se il punto è dentro un'area vietata, lo spinge appena fuori dal raggio."""
        for area in aree_vietate:
            centro = [area.latitudine, area.longitudine]
            dist_m = _distanza_km(punto, centro) * 1000.0
            if dist_m <= area.raggio_metri:
                # vettore dal centro al punto; se coincidono, spingo verso nord
                dlat = punto[0] - area.latitudine
                dlng = punto[1] - area.longitudine
                norm = math.sqrt(dlat ** 2 + dlng ** 2) or 1e-9
                margine = (area.raggio_metri + 30) / 111000.0  # gradi ~
                punto = [area.latitudine + (dlat / norm) * margine,
                         area.longitudine + (dlng / norm) * margine]
        return punto


class MeteoService:
    """IF-U07: meteo simulato deterministico + suggerimento del mezzo.

    La condizione dipende dal giorno dell'anno (deterministica) ma può essere
    forzata via parametro per i test/demo.
    """

    CONDIZIONI = ['SOLE', 'NUVOLOSO', 'PIOGGIA', 'VENTO']

    SUGGERIMENTO = {
        'SOLE':     ('BICI',    'Giornata serena: la bici è la scelta più ecologica e piacevole.'),
        'NUVOLOSO': ('SCOOTER', 'Cielo coperto ma asciutto: lo scooter è comodo e veloce.'),
        'PIOGGIA':  ('AUTO',    'Pioggia in corso: meglio un mezzo coperto come l\'auto.'),
        'VENTO':    ('AUTO',    'Vento forte: sconsigliate due ruote, preferibile l\'auto.'),
    }

    def get_meteo(self, giorno_anno, condizione=None, distanza_km=None):
        if condizione and condizione.upper() in self.CONDIZIONI:
            cond = condizione.upper()
        else:
            cond = self.CONDIZIONI[giorno_anno % len(self.CONDIZIONI)]
        temperatura = 10 + (giorno_anno % 18)  # 10–27 °C, deterministica

        # Suggerimento basato su meteo E distanza (IF-U07)
        if cond in ('PIOGGIA', 'VENTO'):
            mezzo, motivazione = self.SUGGERIMENTO[cond]
        elif distanza_km is not None:
            if distanza_km <= 2:
                mezzo, motivazione = 'BICI', 'Tragitto breve con bel tempo: la bici è ideale.'
            elif distanza_km <= 5:
                mezzo, motivazione = 'SCOOTER', 'Distanza media: lo scooter è il giusto compromesso.'
            else:
                mezzo, motivazione = 'AUTO', 'Tragitto lungo: meglio l\'auto per comodità.'
        else:
            mezzo, motivazione = self.SUGGERIMENTO[cond]

        return {
            'condizione': cond,
            'temperatura_c': temperatura,
            'distanza_km': distanza_km,
            'mezzo_consigliato': mezzo,
            'motivazione': motivazione,
        }


class GatewayPagamento:
    """IF-U13: gateway di pagamento simulato.

    Riceve i dati carta, NON li memorizza: restituisce solo un token e le
    ultime 4 cifre (come farebbe un vero gateway PCI-DSS compliant tipo Stripe).
    """

    CIRCUITI = {'4': 'VISA', '5': 'Mastercard', '3': 'American Express'}

    def tokenizza_carta(self, numero, scadenza):
        numero = (numero or '').replace(' ', '')
        if not numero.isdigit() or not (13 <= len(numero) <= 19):
            raise ValueError("Numero carta non valido.")
        ultime4 = numero[-4:]
        circuito = self.CIRCUITI.get(numero[0], 'Carta')
        seed = f"{numero}|{scadenza}".encode()
        token = 'tok_' + hashlib.sha256(seed).hexdigest()[:24]
        return {'token': token, 'ultime4': ultime4, 'circuito': circuito}
