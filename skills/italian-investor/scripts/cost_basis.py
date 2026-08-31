#!/usr/bin/env python3
"""Calcolo deterministico della base di costo da lotti gia' convertiti in EUR.

Questo modulo NON decide quale metodo fiscale sia applicabile. Il chiamante deve
prima verificare regime, strumento ed evento su fonti primarie.

Oltre a calcolare la base di una vendita puo' produrre lo stato residuo dei
lotti, utile per simulare in sequenza piu' operazioni senza riusare quantita'
gia' cedute.

Esempi:

    python scripts/cost_basis.py calcola lotti.csv --metodo cmp --quantita 40
    python scripts/cost_basis.py calcola lotti.csv --metodo lifo --quantita 40
    python scripts/cost_basis.py consuma lotti.csv --metodo lifo --quantita 40

CSV minimo:

    data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur

`costi_acquisto_eur` e' opzionale e rappresenta i costi totali attribuibili al
lotto di acquisto. Gli eventuali costi della vendita vanno trattati separatamente
nel motore fiscale.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date

EPS = 1e-12


def r(x):
    return round(float(x) + 0.0, 8)


def normalizza_lotto(row, indice=0):
    try:
        giorno = date.fromisoformat(str(row["data_acquisto"]).strip())
        quantita = float(row["quantita"])
        costo_unitario = float(row["costo_unitario_eur"])
        costi = float(row.get("costi_acquisto_eur") or 0.0)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("lotto %s non valido: %s" % (indice + 1, exc)) from exc

    if quantita <= 0:
        raise ValueError("lotto %s: quantita deve essere > 0" % (indice + 1))
    if costo_unitario < 0 or costi < 0:
        raise ValueError("lotto %s: costi e prezzo non possono essere negativi" % (indice + 1))

    costo_totale = quantita * costo_unitario + costi
    return {
        "indice": indice,
        "data_acquisto": giorno.isoformat(),
        "quantita": quantita,
        "costo_unitario_eur": costo_unitario,
        "costi_acquisto_eur": costi,
        "costo_totale_eur": costo_totale,
        "costo_unitario_fiscale_eur": costo_totale / quantita,
    }


def _ricostruisci_lotto(lotto, quantita, costi=None):
    """Ricrea un lotto normalizzato preservando prezzo e data originali."""
    q = float(quantita)
    if q <= EPS:
        return None
    if costi is None:
        rapporto = q / float(lotto["quantita"])
        costi = float(lotto.get("costi_acquisto_eur") or 0.0) * rapporto
    return normalizza_lotto({
        "data_acquisto": lotto["data_acquisto"],
        "quantita": q,
        "costo_unitario_eur": lotto["costo_unitario_eur"],
        "costi_acquisto_eur": float(costi),
    }, lotto.get("indice", 0))


def carica_lotti(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [normalizza_lotto(row, i) for i, row in enumerate(reader)]


def _valida_quantita(lotti, quantita_venduta):
    q = float(quantita_venduta)
    if q <= 0:
        raise ValueError("quantita venduta deve essere > 0")
    disponibile = sum(x["quantita"] for x in lotti)
    if q > disponibile + EPS:
        raise ValueError(
            "quantita venduta %.8g superiore alla quantita disponibile %.8g"
            % (q, disponibile)
        )
    return q, disponibile


def base_cmp(lotti, quantita_venduta):
    """Costo medio ponderato dei lotti correnti, senza scegliere la regola fiscale."""
    q, disponibile = _valida_quantita(lotti, quantita_venduta)
    costo_totale = sum(x["costo_totale_eur"] for x in lotti)
    cmp_unitario = costo_totale / disponibile
    base = cmp_unitario * q
    return {
        "metodo": "cmp",
        "quantita_disponibile": r(disponibile),
        "quantita_venduta": r(q),
        "costo_totale_posizione_eur": r(costo_totale),
        "costo_medio_ponderato_unitario_eur": r(cmp_unitario),
        "base_costo_vendita_eur": r(base),
        "quantita_residua": r(disponibile - q),
        "regola_fiscale_verificata": False,
        "avvertenza": (
            "Il calcolo e' solo aritmetico. Verificare che il CMP sia il criterio "
            "applicabile a regime, strumento ed evento."
        ),
    }


def base_lifo(lotti, quantita_venduta):
    """Consuma prima le date piu' recenti; hard-stop su parziale ambiguo stessa data."""
    q, disponibile = _valida_quantita(lotti, quantita_venduta)
    per_data = defaultdict(list)
    for lotto in lotti:
        per_data[lotto["data_acquisto"]].append(lotto)

    residuo = q
    base = 0.0
    utilizzi = []

    for giorno in sorted(per_data.keys(), reverse=True):
        gruppo = per_data[giorno]
        q_gruppo = sum(x["quantita"] for x in gruppo)
        costo_gruppo = sum(x["costo_totale_eur"] for x in gruppo)

        if residuo <= EPS:
            break

        if residuo >= q_gruppo - EPS:
            usata = min(residuo, q_gruppo)
            base += costo_gruppo
            utilizzi.append({
                "data_acquisto": giorno,
                "quantita_utilizzata": r(usata),
                "base_costo_eur": r(costo_gruppo),
                "lotti_nella_data": len(gruppo),
            })
            residuo -= usata
            continue

        if len(gruppo) > 1:
            return {
                "metodo": "lifo",
                "errore": "AMBIGUITA_STESSA_DATA",
                "imposta_stimata": None,
                "base_costo_vendita_eur": None,
                "dato_mancante": "ordine_intraday_o_base_fiscale_certificata",
                "data_ambigua": giorno,
                "quantita_da_prelevare_nella_data": r(residuo),
                "quantita_totale_nella_data": r(q_gruppo),
                "avvertenza": (
                    "Esistono piu' lotti nella stessa data e la vendita ne consuma solo "
                    "una parte. Non viene inventato un ordine intraday."
                ),
            }

        lotto = gruppo[0]
        costo_unit = lotto["costo_unitario_fiscale_eur"]
        costo_usato = residuo * costo_unit
        base += costo_usato
        utilizzi.append({
            "data_acquisto": giorno,
            "quantita_utilizzata": r(residuo),
            "base_costo_eur": r(costo_usato),
            "lotti_nella_data": 1,
        })
        residuo = 0.0

    return {
        "metodo": "lifo",
        "quantita_disponibile": r(disponibile),
        "quantita_venduta": r(q),
        "base_costo_vendita_eur": r(base),
        "quantita_residua": r(disponibile - q),
        "lotti_utilizzati": utilizzi,
        "regola_fiscale_verificata": False,
        "avvertenza": (
            "Il calcolo e' solo aritmetico. Verificare che il LIFO sia il criterio "
            "applicabile alla fattispecie prima di usare il risultato."
        ),
    }


def consuma_cmp(lotti, quantita_venduta):
    """Riduce pro-quota tutti i lotti mantenendo invariato il CMP del residuo.

    Nel regime a costo medio non esiste un lotto specifico da scegliere per la
    vendita. Per mantenere uno stato numericamente coerente nelle simulazioni,
    il pool residuo conserva le proporzioni dei lotti originari. Non usare questo
    stato sintetico per inferire un successivo ordine LIFO dopo un cambio regime.
    """
    base = base_cmp(lotti, quantita_venduta)
    disponibile = float(base["quantita_disponibile"])
    residua = float(base["quantita_residua"])
    if residua <= EPS:
        return {**base, "lotti_residui": [], "stato_residuo": "vuoto"}

    fattore = residua / disponibile
    residui = []
    for lotto in lotti:
        nuovo = _ricostruisci_lotto(
            lotto,
            float(lotto["quantita"]) * fattore,
            float(lotto.get("costi_acquisto_eur") or 0.0) * fattore,
        )
        if nuovo:
            residui.append(nuovo)
    return {
        **base,
        "lotti_residui": residui,
        "stato_residuo": "pool_cmp_proporzionale",
    }


def consuma_lifo(lotti, quantita_venduta):
    """Restituisce i lotti residui dopo consumo LIFO senza inventare ordini intraday."""
    base = base_lifo(lotti, quantita_venduta)
    if base.get("errore"):
        return {**base, "lotti_residui": None}

    da_consumare = float(quantita_venduta)
    per_data = defaultdict(list)
    for lotto in lotti:
        per_data[lotto["data_acquisto"]].append(lotto)

    residui = []
    consumati = set()
    parziale = None

    for giorno in sorted(per_data.keys(), reverse=True):
        gruppo = per_data[giorno]
        q_gruppo = sum(float(x["quantita"]) for x in gruppo)
        if da_consumare <= EPS:
            break
        if da_consumare >= q_gruppo - EPS:
            for lotto in gruppo:
                consumati.add(id(lotto))
            da_consumare -= q_gruppo
            continue
        # base_lifo ha gia' bloccato il caso con piu' lotti nella stessa data.
        lotto = gruppo[0]
        nuova_q = float(lotto["quantita"]) - da_consumare
        parziale = (lotto, nuova_q)
        consumati.add(id(lotto))
        da_consumare = 0.0
        break

    for lotto in lotti:
        if parziale and lotto is parziale[0]:
            nuovo = _ricostruisci_lotto(lotto, parziale[1])
            if nuovo:
                residui.append(nuovo)
        elif id(lotto) not in consumati:
            residui.append(_ricostruisci_lotto(
                lotto,
                lotto["quantita"],
                lotto.get("costi_acquisto_eur", 0.0),
            ))

    return {
        **base,
        "lotti_residui": residui,
        "stato_residuo": "lotti_lifo_effettivi",
    }


def calcola(lotti, metodo, quantita_venduta):
    metodo = str(metodo).strip().lower()
    if not lotti:
        raise ValueError("nessun lotto disponibile")
    if metodo == "cmp":
        return base_cmp(lotti, quantita_venduta)
    if metodo == "lifo":
        return base_lifo(lotti, quantita_venduta)
    raise ValueError("metodo non supportato: %s (usa cmp o lifo)" % metodo)


def calcola_e_consuma(lotti, metodo, quantita_venduta):
    metodo = str(metodo).strip().lower()
    if not lotti:
        raise ValueError("nessun lotto disponibile")
    if metodo == "cmp":
        return consuma_cmp(lotti, quantita_venduta)
    if metodo == "lifo":
        return consuma_lifo(lotti, quantita_venduta)
    raise ValueError("metodo non supportato: %s (usa cmp o lifo)" % metodo)


def _serializza_lotti(lotti):
    if lotti is None:
        return None
    return [
        {
            "data_acquisto": x["data_acquisto"],
            "quantita": r(x["quantita"]),
            "costo_unitario_eur": r(x["costo_unitario_eur"]),
            "costi_acquisto_eur": r(x.get("costi_acquisto_eur", 0.0)),
            "costo_totale_eur": r(x["costo_totale_eur"]),
        }
        for x in lotti
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("calcola", help="calcola la base di costo della quantita venduta")
    p.add_argument("csv", help="CSV dei lotti con costi gia' espressi in EUR")
    p.add_argument("--metodo", choices=("cmp", "lifo"), required=True)
    p.add_argument("--quantita", type=float, required=True, help="quantita da vendere")

    c = sub.add_parser("consuma", help="calcola la base e restituisce i lotti residui")
    c.add_argument("csv", help="CSV dei lotti con costi gia' espressi in EUR")
    c.add_argument("--metodo", choices=("cmp", "lifo"), required=True)
    c.add_argument("--quantita", type=float, required=True, help="quantita da vendere")

    args = parser.parse_args(argv)
    try:
        lotti = carica_lotti(args.csv)
        if args.comando == "calcola":
            out = calcola(lotti, args.metodo, args.quantita)
        else:
            out = calcola_e_consuma(lotti, args.metodo, args.quantita)
            out["lotti_residui"] = _serializza_lotti(out.get("lotti_residui"))
    except (OSError, ValueError) as exc:
        out = {"errore": str(exc), "base_costo_vendita_eur": None}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if "errore" not in out else 2


if __name__ == "__main__":
    sys.exit(main())
