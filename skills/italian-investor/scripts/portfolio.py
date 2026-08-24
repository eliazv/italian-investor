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
                p[c] = float(v) if v else None
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
    imposta_min = imposta_max = 0.0
    non_calcolabili, quote_ignote = [], []
    for p in posizioni:
        i_min, i_max, _ = imposta_vendita(p, p["valore"], 0.0)
        if i_min is None:
            res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"])
            non_calcolabili.append("%s (%s): %s" % (p["nome"], p["tipo"], res["errore"]))
            continue
        imposta_min += i_min
        imposta_max += i_max
        if round(i_min, 2) != round(i_max, 2):
            quote_ignote.append(p["nome"])

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
        "imposta_se_liquidato_tutto": (round(imposta_max, 2)
                                       if round(imposta_min, 2) == round(imposta_max, 2)
                                       else None),
        "imposta_se_liquidato_tutto_intervallo": [round(imposta_min, 2),
                                                  round(imposta_max, 2)],
        "posizioni_con_quota_agevolata_ignota": quote_ignote,
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
    """Imposta stimata vendendo `importo` euro della posizione p.

    Ritorna (min, max, residuo zainetto). Gli estremi differiscono quando la
    quota agevolata di un OICR non e' nota; valgono None se lo strumento non e'
    calcolabile.
    """
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, minus_disponibili
    quota = min(1.0, importo / p["valore"])
    res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"] * quota,
                         minus_disponibili=minus_disponibili,
                         quota_stato=p.get("quota_stato"))
    if res.get("errore"):
        return None, None, minus_disponibili
    if res["risultato_lordo"] > 0:
        residuo = res.get("zainetto_residuo", minus_disponibili)
    else:
        residuo = res.get("zainetto_dopo", minus_disponibili)
    if res.get("imposta_stimata") is None:
        sc = res["imposta_scenario"]
        return sc["quota_agevolata_100"], sc["quota_agevolata_0"], residuo
    return res["imposta_stimata"], res["imposta_stimata"], residuo


def esegui_vendite(posizioni, eccessi, minus, ordine=None, frazione=1.0):
    """Vende dalle asset class in eccesso.

    Ritorna (imposta_min, imposta_max, venduto_per_classe, residuo minus,
    posizioni non calcolabili).
    """
    candidate = [p for p in posizioni if eccessi.get(p["asset_class"], 0) > 0]
    if ordine:
        candidate.sort(key=ordine)
    da_vendere = {ac: v * frazione for ac, v in eccessi.items() if v > 0}
    imposta_min = imposta_max = 0.0
    venduto = defaultdict(float)
    incalcolabili = []
    for p in candidate:
        residuo_ac = da_vendere.get(p["asset_class"], 0.0)
        if residuo_ac <= 0:
            continue
        importo = min(residuo_ac, p["valore"])
        i_min, i_max, minus = imposta_vendita(p, importo, minus)
        if i_min is None:
            incalcolabili.append(p["nome"])
            continue
        imposta_min += i_min
        imposta_max += i_max
        venduto[p["asset_class"]] += importo
        da_vendere[p["asset_class"]] = residuo_ac - importo
    return imposta_min, imposta_max, dict(venduto), minus, incalcolabili


def drift_post_tax(correnti, target, classi, totale, venduto, imposta):
    """Drift residuo dopo aver pagato l'imposta e reinvestito solo il netto.

    L'imposta esce dal portafoglio: si reinveste meno di quanto si e' venduto,
    quindi il target non viene raggiunto esattamente.
    """
    nuovo_totale = totale - imposta
    if nuovo_totale <= 0:
        return None, 0.0
    valori = {ac: correnti.get(ac, 0.0) - venduto.get(ac, 0.0) for ac in classi}
    reinvestibile = sum(venduto.values()) - imposta
    mancanze = {ac: max(0.0, target.get(ac, 0.0) * nuovo_totale - valori[ac])
                for ac in classi}
    totale_mancanze = sum(mancanze.values())
    if totale_mancanze > 0 and reinvestibile > 0:
        for ac in classi:
            valori[ac] += reinvestibile * mancanze[ac] / totale_mancanze
    drift = sum(abs(valori[ac] / nuovo_totale - target.get(ac, 0.0))
                for ac in classi) / 2
    return round(drift, 4), round(nuovo_totale, 2)


def voce_strategia(nome, imposta_min, imposta_max, venduto, drift, tempo,
                   incalcolabili, nota=None):
    v = {
        "strategia": nome,
        "imposta_stimata": round(imposta_max, 2),
        "venduto": round(sum(venduto.values()), 2),
        "drift_residuo": drift,
        "tempo": tempo,
        "non_calcolabili": incalcolabili,
    }
    if round(imposta_min, 2) != round(imposta_max, 2):
        v["imposta_intervallo"] = [round(imposta_min, 2), round(imposta_max, 2)]
        v["nota_imposta"] = ("Quota agevolata ignota su almeno un OICR: la simulazione "
                             "usa l'estremo prudenziale (imposta massima).")
    if nota:
        v["nota"] = nota
    return v


def ribilancia(posizioni, target, minus=0.0, versamento_mensile=0.0):
    totale = sum(p["valore"] for p in posizioni)
    correnti = defaultdict(float)
    for p in posizioni:
        correnti[p["asset_class"]] += p["valore"]

    classi = set(list(correnti) + list(target))
    drift = {ac: correnti.get(ac, 0.0) / totale - target.get(ac, 0.0) for ac in classi}
    eccessi = {ac: d * totale for ac, d in drift.items() if d > 0}
    drift_iniziale = sum(abs(d) for d in drift.values()) / 2

    strategie = []

    i_min, i_max, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "A - ribilanciamento immediato", i_min, i_max, venduto, d_res,
        "immediato", inc,
        nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post))

    # Solo versamenti: senza vendite le classi in eccesso rientrano nel target solo
    # per diluizione. Serve C tale che corrente[ac] <= target[ac] * (totale + C).
    fabbisogno = 0.0
    impossibile = []
    for ac in classi:
        t = target.get(ac, 0.0)
        if correnti.get(ac, 0.0) <= t * totale:
            continue
        if t <= 0:
            impossibile.append(ac)
            continue
        fabbisogno = max(fabbisogno, correnti[ac] / t - totale)
    nota_b = ("Nessuna vendita, nessuna imposta: serve capitale nuovo pari a %.0f EUR "
              "perche' le classi in eccesso rientrino nel target per diluizione."
              % fabbisogno)
    if impossibile:
        nota_b += (" Le classi %s hanno target 0%%: senza vendite non si azzerano mai."
                   % ", ".join(sorted(impossibile)))
    if versamento_mensile > 0 and not impossibile:
        tempo_b = "circa %d mesi" % round(fabbisogno / versamento_mensile)
    elif versamento_mensile > 0:
        tempo_b = "non raggiungibile senza vendite"
    else:
        tempo_b = "non calcolabile: passare --versamento-mensile"
    strategie.append(voce_strategia(
        "B - solo nuovi versamenti", 0.0, 0.0, {},
        round(drift_iniziale, 4) if impossibile else 0.0, tempo_b, [], nota=nota_b))

    i_min, i_max, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus,
                                                   frazione=0.5)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "C - ribilanciamento parziale (50%)", i_min, i_max, venduto, d_res,
        "immediato", inc))

    # Tax-aware: prima le posizioni con minore imposta stimata per euro venduto.
    def costo_fiscale_unitario(p):
        campione = p["valore"] * 0.01
        _, i_max_c, _ = imposta_vendita(p, campione, minus)
        if i_max_c is None:
            return float("inf")  # non calcolabile: vendere per ultimo
        return i_max_c / campione if campione else 0.0

    i_min, i_max, venduto, _, inc = esegui_vendite(posizioni, eccessi, minus,
                                                   ordine=costo_fiscale_unitario)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "D - tax-aware (vende prima cio che costa meno in imposta)", i_min, i_max,
        venduto, d_res, "immediato", inc,
        nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post))

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
            "Il drift residuo e' al netto delle imposte: l'imposta esce dal portafoglio, "
            "quindi si reinveste meno di quanto si e' venduto.",
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
