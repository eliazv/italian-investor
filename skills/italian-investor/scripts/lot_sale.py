#!/usr/bin/env python3
"""Simula una vendita partendo dai lotti reali invece che da un PMC generico.

Questo helper collega `cost_basis.py` e `tax_engine.py`. Determina il metodo di
base fiscale solo nei casi espressamente coperti dalla regola operativa della
skill:

- amministrato -> CMP per strumenti che generano redditi diversi da cessione;
- dichiarativo -> LIFO per le fattispecie coperte dall'art. 67 c.1-bis TUIR.

ETF/OICR vengono bloccati in automatico: la determinazione del provento OICR
segue regole proprie e non va assimilata meccanicamente al LIFO dei redditi
diversi.

CSV lotti minimo:
    data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur

Esempio:
    python scripts/lot_sale.py vendita --tipo azione --regime dichiarativo \
      --lotti examples/lotti-esempio.csv --prezzo 140 --quantita 15
"""

import argparse
import json
import sys

from cost_basis import carica_lotti, calcola
from tax_engine import simula_vendita

TIPI_LOT_AWARE = {"azione", "obbligazione", "titolo_stato", "certificate"}


def metodo_da_regime(tipo, regime):
    tipo = str(tipo).strip().lower()
    regime = str(regime).strip().lower()
    if tipo not in TIPI_LOT_AWARE:
        return None, (
            "LOT_METHOD_NOT_AUTOMATIC: il metodo base fiscale non viene dedotto per %s. "
            "Per ETF/OICR la disciplina del provento e' distinta; per altri strumenti "
            "serve una qualificazione specifica." % tipo
        )
    if regime == "amministrato":
        return "cmp", None
    if regime == "dichiarativo":
        return "lifo", None
    return None, "Regime non supportato: %s" % regime


def simula_vendita_lotti(tipo, regime, lotti, prezzo, quantita,
                         minus_disponibili=0.0, quota_stato=None,
                         costi_vendita=0.0, metodo=None):
    tipo = str(tipo).strip().lower()
    regime = str(regime).strip().lower()

    if metodo is None:
        metodo, errore = metodo_da_regime(tipo, regime)
        if errore:
            return {
                "errore": errore,
                "imposta_stimata": None,
                "base_fiscale": None,
            }
    else:
        metodo = str(metodo).strip().lower()
        if metodo not in ("cmp", "lifo"):
            return {"errore": "metodo deve essere cmp o lifo", "imposta_stimata": None}

    try:
        base = calcola(lotti, metodo, quantita)
    except ValueError as exc:
        return {"errore": str(exc), "imposta_stimata": None, "base_fiscale": None}

    if base.get("errore"):
        return {
            "errore": base["errore"],
            "imposta_stimata": None,
            "base_fiscale": base,
        }

    q = float(quantita)
    base_totale = float(base["base_costo_vendita_eur"])
    pmc_fiscale = base_totale / q

    vendita = simula_vendita(
        tipo,
        pmc_fiscale,
        float(prezzo),
        q,
        minus_disponibili=float(minus_disponibili or 0.0),
        quota_stato=quota_stato,
        costi=float(costi_vendita or 0.0),
    )

    return {
        "tipo": tipo,
        "regime": regime,
        "metodo_base": metodo,
        "base_fiscale": base,
        "pmc_fiscale_derivato": round(pmc_fiscale, 8),
        "vendita": vendita,
        "imposta_stimata": vendita.get("imposta_stimata"),
        "verificare": [
            "Il metodo e' stato scelto in base al regime solo per una fattispecie coperta; verificare sempre che lo strumento e l'evento rientrino davvero nella regola.",
            "I lotti devono essere gia' convertiti correttamente in EUR con cambi fiscalmente rilevanti e costi inerenti documentabili.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("vendita", help="simula vendita da lotti")
    v.add_argument("--tipo", required=True)
    v.add_argument("--regime", choices=("amministrato", "dichiarativo"), required=True)
    v.add_argument("--lotti", required=True)
    v.add_argument("--prezzo", type=float, required=True)
    v.add_argument("--quantita", type=float, required=True)
    v.add_argument("--minus", type=float, default=0.0)
    v.add_argument("--quota-stato", type=float)
    v.add_argument("--costi-vendita", type=float, default=0.0)
    v.add_argument("--metodo", choices=("cmp", "lifo"),
                   help="override esplicito; usare solo se gia' verificato")

    args = p.parse_args(argv)
    try:
        lotti = carica_lotti(args.lotti)
        out = simula_vendita_lotti(
            args.tipo, args.regime, lotti, args.prezzo, args.quantita,
            args.minus, args.quota_stato, args.costi_vendita, args.metodo,
        )
    except (OSError, ValueError) as exc:
        out = {"errore": str(exc), "imposta_stimata": None}

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
