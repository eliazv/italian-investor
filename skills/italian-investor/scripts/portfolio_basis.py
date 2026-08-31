#!/usr/bin/env python3
"""Riconcilia il PMC del portfolio con il costo fiscale ricostruito dai lotti.

Il modulo NON decide quale base usare per uno specifico evento. Per una
liquidazione integrale dei tipi coperti, tuttavia, la somma del costo dei lotti
fornisce un controllo deterministico molto utile sul `pmc` dichiarato.

Input:
- posizioni già normalizzate da portfolio.py;
- indice lotti per `ISIN + broker` prodotto da portfolio_lots.py.

Non modifica le posizioni e non corregge automaticamente il portfolio.
"""

import argparse
import json
import sys

from lot_sale import TIPI_LOT_AWARE
from portfolio_lots import carica_lotti_portafoglio, indicizza
from portfolio_validator import valida_portafoglio

EPS_EUR = 0.01


def riconcilia_posizione(posizione, lotti):
    tipo = str(posizione.get("tipo") or "").strip().lower()
    if tipo not in TIPI_LOT_AWARE:
        return {
            "isin": posizione.get("isin"),
            "broker": posizione.get("broker"),
            "nome": posizione.get("nome"),
            "tipo": tipo,
            "coperta": False,
            "motivo": "tipo fuori dal lot engine automatico",
        }

    if not lotti:
        return {
            "isin": posizione.get("isin"),
            "broker": posizione.get("broker"),
            "nome": posizione.get("nome"),
            "tipo": tipo,
            "coperta": True,
            "riconciliabile": False,
            "motivo": "lotti fiscali mancanti",
        }

    quantita_lotti = sum(float(x["quantita"]) for x in lotti)
    costo_lotti = sum(float(x["costo_totale_eur"]) for x in lotti)
    quantita_port = float(posizione.get("quantita") or 0.0)
    costo_pmc = quantita_port * float(posizione.get("pmc") or 0.0)
    differenza = costo_lotti - costo_pmc
    pmc_lotti = costo_lotti / quantita_lotti if quantita_lotti else None
    tolleranza_q = max(1e-7, abs(quantita_port) * 1e-8)
    quantita_coerente = abs(quantita_lotti - quantita_port) <= tolleranza_q

    return {
        "isin": posizione.get("isin"),
        "broker": posizione.get("broker"),
        "nome": posizione.get("nome"),
        "tipo": tipo,
        "coperta": True,
        "riconciliabile": quantita_coerente,
        "quantita_portfolio": round(quantita_port, 8),
        "quantita_lotti": round(quantita_lotti, 8),
        "quantita_coerente": quantita_coerente,
        "pmc_csv": round(float(posizione.get("pmc") or 0.0), 8),
        "costo_da_pmc_eur": round(costo_pmc, 2),
        "pmc_fiscale_lotti_eur": round(pmc_lotti, 8) if pmc_lotti is not None else None,
        "costo_fiscale_lotti_eur": round(costo_lotti, 2),
        "differenza_costo_eur": round(differenza, 2),
        "coincide_al_centesimo": quantita_coerente and abs(differenza) <= EPS_EUR,
        "azione": (
            "nessuna" if quantita_coerente and abs(differenza) <= EPS_EUR
            else "verificare_pmc_e_base_fiscale"
        ),
    }


def riconcilia_portafoglio(posizioni, indice_lotti):
    righe = []
    costo_pmc_coperto = 0.0
    costo_lotti_coperto = 0.0
    differenze = []
    mancanti = []

    for p in posizioni:
        key = (str(p.get("isin") or "").strip().upper(), str(p.get("broker") or "").strip())
        esito = riconcilia_posizione(p, indice_lotti.get(key))
        righe.append(esito)
        if not esito.get("coperta"):
            continue
        if not esito.get("riconciliabile"):
            mancanti.append("%s / %s" % key)
            continue
        costo_pmc_coperto += float(esito["costo_da_pmc_eur"])
        costo_lotti_coperto += float(esito["costo_fiscale_lotti_eur"])
        if not esito["coincide_al_centesimo"]:
            differenze.append("%s / %s" % key)

    return {
        "posizioni": righe,
        "riepilogo": {
            "costo_pmc_posizioni_coperte_eur": round(costo_pmc_coperto, 2),
            "costo_fiscale_lotti_posizioni_coperte_eur": round(costo_lotti_coperto, 2),
            "differenza_eur": round(costo_lotti_coperto - costo_pmc_coperto, 2),
            "posizioni_con_differenza": differenze,
            "posizioni_coperte_non_riconciliabili": mancanti,
            "tutto_coerente": not differenze and not mancanti,
        },
        "avvertenze": [
            "La riconciliazione non sostituisce automaticamente il PMC del portfolio.",
            "Per ETF/OICR e tipi fuori dal lot engine la base fiscale resta da verificare con la disciplina specifica.",
            "Una differenza puo' dipendere da commissioni, trasferimenti, corporate action, valuta o dati del broker: va spiegata prima di correggere il portfolio.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("portfolio")
    p.add_argument("lotti")
    args = p.parse_args(argv)
    try:
        qualita = valida_portafoglio(args.portfolio)
        if not qualita.get("azionabile"):
            raise ValueError("portfolio non valido: %s" % "; ".join(qualita.get("errori", [])))
        # Import locale per evitare un ciclo a import-time: portfolio importa questo
        # helper solo nel flusso applicativo.
        from portfolio import leggi
        posizioni, _ = leggi(args.portfolio)
        indice = indicizza(carica_lotti_portafoglio(args.lotti))
        out = riconcilia_portafoglio(posizioni, indice)
    except (OSError, ValueError) as exc:
        out = {"errore": str(exc)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
