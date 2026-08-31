#!/usr/bin/env python3
"""Calcolo deterministico della base di costo da lotti gia' convertiti in EUR.

Questo modulo NON decide quale metodo fiscale sia applicabile. Il chiamante deve
prima verificare regime, strumento ed evento su fonti primarie.

Esempi:

    python scripts/cost_basis.py calcola lotti.csv --metodo cmp --quantita 40
    python scripts/cost_basis.py calcola lotti.csv --metodo lifo --quantita 40

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


def carica_lotti(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [normalizza_lotto(row, i) for i, row in enumerate(reader)]


def _valida_quantita(lotti, quantita_venduta):
    q = float(quantita_venduta)
    if q <= 0:
        raise ValueError("quantita venduta deve essere > 0")
    disponibile = sum(x["quantita"] for x in lotti)
    if q > disponibile + 1e-12:
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

        if residuo <= 1e-12:
            break

        if residuo >= q_gruppo - 1e-12:
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


def calcola(lotti, metodo, quantita_venduta):
    metodo = str(metodo).strip().lower()
    if not lotti:
        raise ValueError("nessun lotto disponibile")
    if metodo == "cmp":
        return base_cmp(lotti, quantita_venduta)
    if metodo == "lifo":
        return base_lifo(lotti, quantita_venduta)
    raise ValueError("metodo non supportato: %s (usa cmp o lifo)" % metodo)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("calcola", help="calcola la base di costo della quantita venduta")
    p.add_argument("csv", help="CSV dei lotti con costi gia' espressi in EUR")
    p.add_argument("--metodo", choices=("cmp", "lifo"), required=True)
    p.add_argument("--quantita", type=float, required=True, help="quantita da vendere")

    args = parser.parse_args(argv)
    try:
        lotti = carica_lotti(args.csv)
        out = calcola(lotti, args.metodo, args.quantita)
    except (OSError, ValueError) as exc:
        out = {"errore": str(exc), "base_costo_vendita_eur": None}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if "errore" not in out else 2


if __name__ == "__main__":
    sys.exit(main())
