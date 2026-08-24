#!/usr/bin/env python3
"""Gestione deterministica dello zainetto fiscale per anno, broker e regime.

Il file CSV usa le colonne:
    broker,regime,anno_realizzo,importo

- `regime`: amministrato oppure dichiarativo.
- la scadenza e' calcolata come anno_realizzo + 4;
- in amministrato sono disponibili solo i lotti dello stesso broker;
- in dichiarativo si aggregano i lotti marcati dichiarativo anche se originati
  da intermediari diversi;
- la simulazione consuma prima i lotti con scadenza piu' vicina. E' una scelta
  prudenziale/ottimizzante del simulatore, non una regola sull'ordine contabile
  applicato dal singolo intermediario.
"""

import argparse
import copy
import csv
import json
import sys

REGIMI = {"amministrato", "dichiarativo"}


def r(x):
    return round(float(x), 2)


def anno_scadenza(anno_realizzo):
    return int(anno_realizzo) + 4


def normalizza_lotto(lotto):
    broker = str(lotto.get("broker", "")).strip()
    regime = str(lotto.get("regime", "amministrato")).strip().lower()
    if not broker:
        raise ValueError("broker mancante nello zainetto")
    if regime not in REGIMI:
        raise ValueError("regime non supportato nello zainetto: %s" % regime)
    anno = int(lotto["anno_realizzo"])
    importo = float(lotto["importo"])
    if importo < 0:
        raise ValueError("importo minusvalenza negativo per %s" % broker)
    return {
        "broker": broker,
        "regime": regime,
        "anno_realizzo": anno,
        "anno_scadenza": anno_scadenza(anno),
        "importo": importo,
    }


def carica_csv(percorso):
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    richieste = {"broker", "regime", "anno_realizzo", "importo"}
    if not righe:
        return []
    mancanti = richieste - set(righe[0])
    if mancanti:
        raise ValueError("colonne mancanti nello zainetto: %s" % ", ".join(sorted(mancanti)))
    return [normalizza_lotto(riga) for riga in righe]


def lotto_utilizzabile(lotto, anno_fiscale, broker, regime):
    if lotto["importo"] <= 0:
        return False
    if int(anno_fiscale) < lotto["anno_realizzo"]:
        return False
    if int(anno_fiscale) > lotto["anno_scadenza"]:
        return False
    if lotto["regime"] != regime:
        return False
    if regime == "amministrato" and lotto["broker"] != broker:
        return False
    return True


def disponibile(lotti, broker, anno_fiscale, regime="amministrato"):
    regime = regime.lower()
    if regime not in REGIMI:
        raise ValueError("regime non supportato: %s" % regime)
    if regime == "amministrato" and not broker:
        raise ValueError("broker richiesto in regime amministrato")
    return r(sum(l["importo"] for l in lotti
                 if lotto_utilizzabile(l, anno_fiscale, broker, regime)))


def scadute(lotti, anno_fiscale, broker=None, regime=None):
    out = []
    for l in lotti:
        if regime and l["regime"] != regime:
            continue
        if broker and l["broker"] != broker:
            continue
        if int(anno_fiscale) > l["anno_scadenza"] and l["importo"] > 0:
            out.append(dict(l))
    return out


def consuma(lotti, importo, broker, anno_fiscale, regime="amministrato"):
    """Simula la compensazione e restituisce lotti aggiornati e dettaglio uso."""
    regime = regime.lower()
    if importo < 0:
        raise ValueError("importo da compensare negativo")
    work = copy.deepcopy(lotti)
    candidati = [
        (idx, l) for idx, l in enumerate(work)
        if lotto_utilizzabile(l, anno_fiscale, broker, regime)
    ]
    candidati.sort(key=lambda x: (x[1]["anno_scadenza"], x[1]["anno_realizzo"], x[0]))

    residuo = float(importo)
    usi = []
    for idx, lotto in candidati:
        if residuo <= 0:
            break
        usato = min(lotto["importo"], residuo)
        if usato <= 0:
            continue
        lotto["importo"] -= usato
        residuo -= usato
        usi.append({
            "broker": lotto["broker"],
            "regime": lotto["regime"],
            "anno_realizzo": lotto["anno_realizzo"],
            "anno_scadenza": lotto["anno_scadenza"],
            "utilizzato": r(usato),
        })

    for lotto in work:
        lotto["importo"] = r(lotto["importo"])
    return {
        "richiesto": r(importo),
        "utilizzato": r(importo - residuo),
        "non_compensato": r(residuo),
        "ordine_simulazione": "scadenza_piu_vicina_prima",
        "utilizzi": usi,
        "lotti": work,
    }


def aggiungi(lotti, broker, regime, anno_realizzo, importo):
    work = copy.deepcopy(lotti)
    importo = float(importo)
    if importo <= 0:
        return work
    work.append(normalizza_lotto({
        "broker": broker,
        "regime": regime,
        "anno_realizzo": anno_realizzo,
        "importo": importo,
    }))
    return work


def riepilogo(lotti, anno_fiscale):
    gruppi = {}
    for l in lotti:
        key = "%s|%s" % (l["regime"], l["broker"])
        g = gruppi.setdefault(key, {
            "regime": l["regime"],
            "broker": l["broker"],
            "disponibile": 0.0,
            "scaduto": 0.0,
            "lotti": [],
        })
        voce = dict(l)
        if int(anno_fiscale) > l["anno_scadenza"]:
            stato = "scaduto"
            g["scaduto"] += l["importo"]
        elif int(anno_fiscale) < l["anno_realizzo"]:
            stato = "futuro"
        else:
            stato = "utilizzabile"
            g["disponibile"] += l["importo"]
        voce["stato"] = stato
        g["lotti"].append(voce)
    for g in gruppi.values():
        g["disponibile"] = r(g["disponibile"])
        g["scaduto"] = r(g["scaduto"])
    return {"anno_fiscale": int(anno_fiscale), "gruppi": list(gruppi.values())}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stato", help="riepilogo lotti e scadenze")
    s.add_argument("csv")
    s.add_argument("--anno-fiscale", type=int, required=True)

    c = sub.add_parser("compensa", help="simula utilizzo dello zainetto")
    c.add_argument("csv")
    c.add_argument("--importo", type=float, required=True)
    c.add_argument("--anno-fiscale", type=int, required=True)
    c.add_argument("--broker", required=True)
    c.add_argument("--regime", choices=sorted(REGIMI), default="amministrato")

    a = p.parse_args(argv)
    try:
        lotti = carica_csv(a.csv)
        if a.cmd == "stato":
            out = riepilogo(lotti, a.anno_fiscale)
        else:
            out = consuma(lotti, a.importo, a.broker, a.anno_fiscale, a.regime)
    except (ValueError, KeyError) as e:
        print(json.dumps({"errore": str(e)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
