#!/usr/bin/env python3
"""Analisi di portafoglio e confronto di strategie di ribilanciamento tax-aware.

Calcoli deterministici, nessuna dipendenza esterna, nessuna raccomandazione:
lo script produce numeri, l'interpretazione resta all'analisi.

    python scripts/portfolio.py analizza portafoglio.csv
    python scripts/portfolio.py ribilancia portafoglio.csv \
        --target azionario=70,obbligazionario=25,liquidita=5 \
        --versamento-mensile 1000

Colonne CSV richieste: isin, nome, tipo, quantita, pmc, prezzo, asset_class.
Colonne opzionali: valuta_esposizione, area, settore, broker, quota_stato.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

from tax_engine import simula_vendita

RICHIESTE = ["isin", "nome", "tipo", "quantita", "pmc", "prezzo", "asset_class"]
OPZIONALI = ["valuta_esposizione", "area", "settore", "broker", "quota_stato"]


def leggi(percorso):
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    if not righe:
        raise SystemExit("CSV vuoto: %s" % percorso)
    mancanti = [c for c in RICHIESTE if c not in righe[0]]
    if mancanti:
        raise SystemExit("Colonne mancanti nel CSV: %s" % ", ".join(mancanti))

    posizioni, lacune = [], []
    for i, riga in enumerate(righe, start=2):
        try:
            p = {
                "isin": riga["isin"].strip(),
                "nome": riga["nome"].strip(),
                "tipo": riga["tipo"].strip().lower(),
                "quantita": float(riga["quantita"]),
                "pmc": float(riga["pmc"]),
                "prezzo": float(riga["prezzo"]),
                "asset_class": riga["asset_class"].strip().lower(),
            }
        except (ValueError, AttributeError) as e:
            raise SystemExit("Riga %d non valida: %s" % (i, e))
        for c in OPZIONALI:
            v = (riga.get(c) or "").strip()
            if c == "quota_stato":
                p[c] = float(v) if v else 0.0
                if not v and p["tipo"] in ("etf", "oicr"):
                    lacune.append("%s: quota titoli di Stato non indicata" % p["nome"])
            else:
                p[c] = v or "non indicato"
                if not v:
                    lacune.append("%s: %s non indicato" % (p["nome"], c))
        p["valore"] = p["quantita"] * p["prezzo"]
        p["costo"] = p["quantita"] * p["pmc"]
        p["plus_minus"] = p["valore"] - p["costo"]
        posizioni.append(p)
    return posizioni, lacune


def ripartizione(posizioni, chiave, totale):
    agg = defaultdict(float)
    for p in posizioni:
        agg[p.get(chiave, "non indicato")] += p["valore"]
    return {k: {"valore": round(v, 2), "peso": round(v / totale, 4)}
            for k, v in sorted(agg.items(), key=lambda kv: -kv[1])}


def analizza(posizioni, lacune, minus=0.0):
    totale = sum(p["valore"] for p in posizioni)
    if totale <= 0:
        raise SystemExit("Controvalore totale nullo.")

    for p in posizioni:
        p["peso"] = p["valore"] / totale

    hhi = sum(p["peso"] ** 2 for p in posizioni)
    ordinate = sorted(posizioni, key=lambda p: -p["valore"])

    # Imposta stimata in caso di liquidazione integrale, posizione per posizione.
    imposta_totale, non_calcolabili = 0.0, []
    for p in posizioni:
        res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"],
                             minus_disponibili=0.0, quota_stato=p.get("quota_stato", 0.0))
        if res.get("imposta_stimata") is None:
            non_calcolabili.append("%s (%s): %s" % (p["nome"], p["tipo"], res["errore"]))
        else:
            imposta_totale += res["imposta_stimata"]

    return {
        "totale": round(totale, 2),
        "costo_totale": round(sum(p["costo"] for p in posizioni), 2),
        "plusvalenza_latente_netta": round(sum(p["plus_minus"] for p in posizioni), 2),
        "posizioni": len(posizioni),
        "concentrazione": {
            "hhi": round(hhi, 4),
            "posizioni_equivalenti": round(1 / hhi, 1),
            "prima_posizione": round(ordinate[0]["peso"], 4),
            "prime_cinque": round(sum(p["peso"] for p in ordinate[:5]), 4),
        },
        "ripartizioni": {
            "asset_class": ripartizione(posizioni, "asset_class", totale),
            "valuta_esposizione": ripartizione(posizioni, "valuta_esposizione", totale),
            "area": ripartizione(posizioni, "area", totale),
            "settore": ripartizione(posizioni, "settore", totale),
            "broker": ripartizione(posizioni, "broker", totale),
        },
        "dettaglio": [
            {k: (round(v, 4) if isinstance(v, float) else v)
             for k, v in p.items() if k in
             ("isin", "nome", "tipo", "valore", "plus_minus", "peso")}
            for p in ordinate
        ],
        "imposta_se_liquidato_tutto": round(imposta_totale, 2),
        "posizioni_non_calcolabili": non_calcolabili,
        "dati_mancanti": lacune,
        "verificare": [
            "La valuta di esposizione va letta sui sottostanti, non sulla valuta di "
            "quotazione: confermare il dato per ogni fondo.",
            "L'imposta di liquidazione integrale ignora lo zainetto e i costi: e' una "
            "soglia superiore indicativa.",
        ],
    }


def parse_target(s):
    target = {}
    for pezzo in s.split(","):
        k, _, v = pezzo.partition("=")
        target[k.strip().lower()] = float(v) / 100.0
    somma = sum(target.values())
    if abs(somma - 1.0) > 0.005:
        raise SystemExit("I target sommano a %.1f%%, non a 100%%." % (somma * 100))
    return target


def imposta_vendita(p, importo, minus_disponibili):
    """Imposta stimata vendendo `importo` euro di controvalore della posizione p."""
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, minus_disponibili
    quota = min(1.0, importo / p["valore"])
    res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"] * quota,
                         minus_disponibili=minus_disponibili,
                         quota_stato=p.get("quota_stato", 0.0))
    if res.get("imposta_stimata") is None:
        return None, 0.0, minus_disponibili
    imposta = res["imposta_stimata"]
    if res["risultato_lordo"] > 0:
        residuo = res.get("zainetto_residuo", minus_disponibili)
    else:
        residuo = res.get("zainetto_dopo", minus_disponibili)
    return imposta, res["risultato_lordo"], residuo


def esegui_vendite(posizioni, eccessi, minus, ordine=None, frazione=1.0):
    """Vende dalle asset class in eccesso; ritorna (imposta, venduto, residuo minus)."""
    candidate = [p for p in posizioni if eccessi.get(p["asset_class"], 0) > 0]
    if ordine:
        candidate.sort(key=ordine)
    da_vendere = {ac: v * frazione for ac, v in eccessi.items() if v > 0}
    imposta_tot, venduto_tot, incalcolabili = 0.0, 0.0, []
    for p in candidate:
        residuo_ac = da_vendere.get(p["asset_class"], 0.0)
        if residuo_ac <= 0:
            continue
        importo = min(residuo_ac, p["valore"])
        imposta, _, minus = imposta_vendita(p, importo, minus)
        if imposta is None:
            incalcolabili.append(p["nome"])
            continue
        imposta_tot += imposta
        venduto_tot += importo
        da_vendere[p["asset_class"]] = residuo_ac - importo
    return imposta_tot, venduto_tot, minus, incalcolabili


def ribilancia(posizioni, target, minus=0.0, versamento_mensile=0.0):
    totale = sum(p["valore"] for p in posizioni)
    correnti = defaultdict(float)
    for p in posizioni:
        correnti[p["asset_class"]] += p["valore"]

    classi = set(list(correnti) + list(target))
    drift = {ac: correnti.get(ac, 0.0) / totale - target.get(ac, 0.0) for ac in classi}
    eccessi = {ac: d * totale for ac, d in drift.items() if d > 0}
    scoperto = sum(-d * totale for d in drift.values() if d < 0)
    drift_iniziale = sum(abs(d) for d in drift.values()) / 2

    strategie = []

    imposta, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus)
    strategie.append({
        "strategia": "A - ribilanciamento immediato",
        "imposta_stimata": round(imposta, 2),
        "venduto": round(venduto, 2),
        "drift_residuo": 0.0,
        "tempo": "immediato",
        "non_calcolabili": inc,
    })

    if versamento_mensile > 0:
        mesi = scoperto / versamento_mensile
        strategie.append({
            "strategia": "B - solo nuovi versamenti",
            "imposta_stimata": 0.0,
            "venduto": 0.0,
            "drift_residuo": round(drift_iniziale, 4),
            "tempo": "circa %d mesi (%.0f EUR da versare)" % (round(mesi), scoperto),
            "nota": "Il drift si riduce progressivamente; il target si raggiunge senza "
                    "realizzare plusvalenze ma con esposizione fuori target nel frattempo.",
        })
    else:
        strategie.append({
            "strategia": "B - solo nuovi versamenti",
            "imposta_stimata": 0.0,
            "venduto": 0.0,
            "drift_residuo": round(drift_iniziale, 4),
            "tempo": "non calcolabile",
            "nota": "Passare --versamento-mensile per stimare il tempo.",
        })

    imposta, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus, frazione=0.5)
    strategie.append({
        "strategia": "C - ribilanciamento parziale (50%)",
        "imposta_stimata": round(imposta, 2),
        "venduto": round(venduto, 2),
        "drift_residuo": round(drift_iniziale / 2, 4),
        "tempo": "immediato",
        "non_calcolabili": inc,
    })

    # Tax-aware: prima le posizioni con minore imposta stimata per euro venduto.
    def costo_fiscale_unitario(p):
        campione = p["valore"] * 0.01
        imposta_c, _, _ = imposta_vendita(p, campione, minus)
        if imposta_c is None:
            return float("inf")  # non calcolabile: vendere per ultimo
        return imposta_c / campione if campione else 0.0

    imposta, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus,
                                              ordine=costo_fiscale_unitario)
    strategie.append({
        "strategia": "D - tax-aware (vende prima cio che costa meno in imposta)",
        "imposta_stimata": round(imposta, 2),
        "venduto": round(venduto, 2),
        "drift_residuo": 0.0,
        "tempo": "immediato",
        "non_calcolabili": inc,
    })

    return {
        "totale": round(totale, 2),
        "allocazione_corrente": {ac: round(correnti.get(ac, 0.0) / totale, 4)
                                 for ac in sorted(classi)},
        "target": {ac: round(target.get(ac, 0.0), 4) for ac in sorted(classi)},
        "drift_per_classe": {ac: round(drift[ac], 4) for ac in sorted(classi)},
        "drift_totale": round(drift_iniziale, 4),
        "minusvalenze_disponibili": minus,
        "strategie": strategie,
        "verificare": [
            "Le vendite sono simulate pro-quota sulla posizione: il risultato reale "
            "dipende dai lotti effettivi e dal criterio applicato dall'intermediario.",
            "Non sono inclusi commissioni, spread e bollo.",
            "Lo zainetto e' per intermediario: verificare che le minus siano presso lo "
            "stesso broker delle plusvalenze realizzate.",
            "Nessuna strategia va scelta solo per il risultato fiscale.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analizza", help="metriche, esposizioni, plus/minus latenti")
    a.add_argument("csv")
    a.add_argument("--minus", type=float, default=0.0)

    rb = sub.add_parser("ribilancia", help="confronto di strategie di ribilanciamento")
    rb.add_argument("csv")
    rb.add_argument("--target", required=True,
                    help="es. azionario=70,obbligazionario=25,liquidita=5")
    rb.add_argument("--minus", type=float, default=0.0)
    rb.add_argument("--versamento-mensile", type=float, default=0.0)

    args = p.parse_args(argv)
    posizioni, lacune = leggi(args.csv)
    if args.cmd == "analizza":
        res = analizza(posizioni, lacune, args.minus)
    else:
        res = ribilancia(posizioni, parse_target(args.target),
                         args.minus, args.versamento_mensile)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
