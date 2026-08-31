#!/usr/bin/env python3
"""Analisi di portafoglio e confronto di strategie di ribilanciamento tax-aware.

Calcoli deterministici, nessuna dipendenza esterna, nessuna raccomandazione:
lo script produce numeri, l'interpretazione resta all'analisi.

    python scripts/portfolio.py analizza portafoglio.csv
    python scripts/portfolio.py ribilancia portafoglio.csv \
        --target azionario=70,obbligazionario=25,liquidita=5 \
        --zainetto-csv zainetto.csv --anno-fiscale 2026

Colonne CSV richieste: isin, nome, tipo, quantita, pmc, prezzo, asset_class.
Colonne opzionali: valuta_esposizione, valuta_quotazione, area, settore, broker,
quota_stato.
"""

import argparse
import copy
import csv
import json
import sys
from collections import defaultdict

from instrument_resolver import carica_registry, verifica_portafoglio
from portfolio_validator import valida_portafoglio
from tax_engine import simula_vendita
from zainetto import aggiungi as aggiungi_minus
from zainetto import carica_csv as carica_zainetto
from zainetto import consuma as consuma_minus
from zainetto import disponibile as minus_disponibile
from zainetto import riepilogo as riepilogo_zainetto

RICHIESTE = ["isin", "nome", "tipo", "quantita", "pmc", "prezzo", "asset_class"]
OPZIONALI = ["valuta_esposizione", "valuta_quotazione", "area", "settore", "broker", "quota_stato"]


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


def concentrazione_per_isin(posizioni, totale):
    """Concentrazione economica aggregata per ISIN, indipendente dal broker.

    Lo stesso strumento detenuto su due broker deve restare fiscalmente distinto,
    ma per HHI/top-5 rappresenta una sola esposizione economica.
    """
    valori = defaultdict(float)
    nomi = {}
    for p in posizioni:
        isin = p["isin"]
        valori[isin] += p["valore"]
        nomi.setdefault(isin, p["nome"])

    ordinate = sorted(valori.items(), key=lambda kv: -kv[1])
    pesi = [(isin, valore / totale) for isin, valore in ordinate]
    hhi = sum(peso ** 2 for _, peso in pesi)
    dettaglio = [
        {
            "isin": isin,
            "nome": nomi.get(isin),
            "valore": round(valori[isin], 2),
            "peso": round(peso, 4),
        }
        for isin, peso in pesi
    ]
    return {
        "hhi": round(hhi, 4),
        "posizioni_equivalenti": round(1 / hhi, 1) if hhi else 0.0,
        "prima_posizione": round(pesi[0][1], 4) if pesi else 0.0,
        "prime_cinque": round(sum(p for _, p in pesi[:5]), 4),
        "strumenti_unici": len(pesi),
        "aggregata_per": "isin",
        "dettaglio_top": dettaglio[:10],
    }


def analizza(posizioni, lacune, minus=0.0, zainetto_lotti=None, anno_fiscale=None):
    totale = sum(p["valore"] for p in posizioni)
    if totale <= 0:
        raise SystemExit("Controvalore totale nullo.")

    for p in posizioni:
        p["peso"] = p["valore"] / totale

    ordinate = sorted(posizioni, key=lambda p: -p["valore"])
    concentrazione = concentrazione_per_isin(posizioni, totale)

    # Soglia fiscale indicativa: non usa lo zainetto per non simulare un ordine
    # arbitrario di liquidazione tra broker diversi.
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

    out = {
        "totale": round(totale, 2),
        "costo_totale": round(sum(p["costo"] for p in posizioni), 2),
        "plusvalenza_latente_netta": round(sum(p["plus_minus"] for p in posizioni), 2),
        "righe_portafoglio": len(posizioni),
        "strumenti_unici": concentrazione["strumenti_unici"],
        "concentrazione": concentrazione,
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
            "La concentrazione HHI/top-5 e' aggregata per ISIN; la ripartizione per broker resta separata per non perdere il contesto fiscale.",
            "La valuta di esposizione va letta sui sottostanti, non sulla valuta di quotazione: confermare il dato per ogni fondo.",
            "L'imposta di liquidazione integrale non applica lo zainetto: e' una soglia superiore indicativa, non una simulazione di vendita ordinata.",
            "Il PMC del CSV resta un input dichiarato: verificare che rappresenti la base fiscale applicabile prima di rendere azionabile il calcolo.",
        ],
    }
    if zainetto_lotti is not None and anno_fiscale is not None:
        out["zainetto"] = riepilogo_zainetto(zainetto_lotti, anno_fiscale)
    elif minus:
        out["minusvalenze_legacy"] = round(minus, 2)
    return out


def parse_target(s):
    target = {}
    for pezzo in s.split(","):
        k, _, v = pezzo.partition("=")
        target[k.strip().lower()] = float(v) / 100.0
    somma = sum(target.values())
    if abs(somma - 1.0) > 0.005:
        raise SystemExit("I target sommano a %.1f%%, non a 100%%." % (somma * 100))
    return target


def _risultato_imposta(res, minus_disponibili):
    if res.get("errore"):
        return None, None, minus_disponibili
    if res["risultato_lordo"] > 0:
        residuo = res.get("zainetto_residuo", minus_disponibili)
    else:
        residuo = res.get("zainetto_dopo", minus_disponibili)
    if res.get("imposta_stimata") is None:
        sc = res.get("imposta_scenario")
        if not sc:
            return 0.0, 0.0, residuo
        return sc["quota_agevolata_100"], sc["quota_agevolata_0"], residuo
    return res["imposta_stimata"], res["imposta_stimata"], residuo


def imposta_vendita(p, importo, minus_disponibili):
    """Modalita' legacy: un unico saldo minus numerico."""
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, minus_disponibili
    quota = min(1.0, importo / p["valore"])
    res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"] * quota,
                         minus_disponibili=minus_disponibili,
                         quota_stato=p.get("quota_stato"))
    return _risultato_imposta(res, minus_disponibili)


def imposta_vendita_strutturata(p, importo, lotti, anno_fiscale,
                                 regime="amministrato"):
    """Simula una vendita usando solo le minus compatibili con broker/regime/anno."""
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, copy.deepcopy(lotti)
    broker = p.get("broker")
    if not broker or broker == "non indicato":
        return None, None, copy.deepcopy(lotti)
    try:
        minus = minus_disponibile(lotti, broker, anno_fiscale, regime)
    except ValueError:
        return None, None, copy.deepcopy(lotti)

    quota = min(1.0, importo / p["valore"])
    res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"] * quota,
                         minus_disponibili=minus,
                         quota_stato=p.get("quota_stato"))
    if res.get("errore"):
        return None, None, copy.deepcopy(lotti)

    work = copy.deepcopy(lotti)
    if res["risultato_lordo"] > 0:
        usate = float(res.get("minusvalenze_utilizzate", 0.0) or 0.0)
        if usate > 0:
            work = consuma_minus(work, usate, broker, anno_fiscale, regime)["lotti"]
    else:
        generata = res.get("minusvalenza_generata")
        if generata is not None and float(generata) > 0:
            work = aggiungi_minus(work, broker, regime, anno_fiscale, float(generata))

    i_min, i_max, _ = _risultato_imposta(res, minus)
    return i_min, i_max, work


def esegui_vendite(posizioni, eccessi, minus=0.0, ordine=None, frazione=1.0,
                    zainetto_lotti=None, anno_fiscale=None,
                    regime="amministrato"):
    """Vende dalle asset class in eccesso mantenendo lo stato fiscale."""
    candidate = [p for p in posizioni if eccessi.get(p["asset_class"], 0) > 0]
    if ordine:
        candidate.sort(key=ordine)
    da_vendere = {ac: v * frazione for ac, v in eccessi.items() if v > 0}
    imposta_min = imposta_max = 0.0
    venduto = defaultdict(float)
    incalcolabili = []
    minus_legacy = minus
    wallet = copy.deepcopy(zainetto_lotti) if zainetto_lotti is not None else None

    for p in candidate:
        residuo_ac = da_vendere.get(p["asset_class"], 0.0)
        if residuo_ac <= 0:
            continue
        importo = min(residuo_ac, p["valore"])
        if wallet is not None:
            i_min, i_max, wallet_nuovo = imposta_vendita_strutturata(
                p, importo, wallet, anno_fiscale, regime)
            if i_min is not None:
                wallet = wallet_nuovo
        else:
            i_min, i_max, minus_legacy = imposta_vendita(p, importo, minus_legacy)
        if i_min is None:
            incalcolabili.append(p["nome"])
            continue
        imposta_min += i_min
        imposta_max += i_max
        venduto[p["asset_class"]] += importo
        da_vendere[p["asset_class"]] = residuo_ac - importo
    return imposta_min, imposta_max, dict(venduto), minus_legacy, wallet, incalcolabili


def drift_post_tax(correnti, target, classi, totale, venduto, imposta):
    """Drift residuo dopo aver pagato l'imposta e reinvestito solo il netto."""
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
                   incalcolabili, nota=None, wallet=None, anno_fiscale=None):
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
        v["nota_imposta"] = ("Quota agevolata ignota su almeno un OICR: la simulazione usa l'estremo prudenziale (imposta massima).")
    if wallet is not None and anno_fiscale is not None:
        v["zainetto_dopo"] = riepilogo_zainetto(wallet, anno_fiscale)
    if nota:
        v["nota"] = nota
    return v


def ribilancia(posizioni, target, minus=0.0, versamento_mensile=0.0,
                zainetto_lotti=None, anno_fiscale=None,
                regime="amministrato"):
    totale = sum(p["valore"] for p in posizioni)
    correnti = defaultdict(float)
    for p in posizioni:
        correnti[p["asset_class"]] += p["valore"]

    classi = set(list(correnti) + list(target))
    drift = {ac: correnti.get(ac, 0.0) / totale - target.get(ac, 0.0) for ac in classi}
    eccessi = {ac: d * totale for ac, d in drift.items() if d > 0}
    drift_iniziale = sum(abs(d) for d in drift.values()) / 2
    strategie = []

    i_min, i_max, venduto, _, wallet, inc = esegui_vendite(
        posizioni, eccessi, minus, zainetto_lotti=zainetto_lotti,
        anno_fiscale=anno_fiscale, regime=regime)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "A - ribilanciamento immediato", i_min, i_max, venduto, d_res,
        "immediato", inc, nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post,
        wallet=wallet, anno_fiscale=anno_fiscale))

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
    nota_b = ("Nessuna vendita, nessuna imposta: serve capitale nuovo pari a %.0f EUR perche' le classi in eccesso rientrino nel target per diluizione." % fabbisogno)
    if impossibile:
        nota_b += (" Le classi %s hanno target 0%%: senza vendite non si azzerano mai." % ", ".join(sorted(impossibile)))
    if versamento_mensile > 0 and not impossibile:
        tempo_b = "circa %d mesi" % round(fabbisogno / versamento_mensile)
    elif versamento_mensile > 0:
        tempo_b = "non raggiungibile senza vendite"
    else:
        tempo_b = "non calcolabile: passare --versamento-mensile"
    strategie.append(voce_strategia(
        "B - solo nuovi versamenti", 0.0, 0.0, {},
        round(drift_iniziale, 4) if impossibile else 0.0, tempo_b, [], nota=nota_b,
        wallet=copy.deepcopy(zainetto_lotti) if zainetto_lotti is not None else None,
        anno_fiscale=anno_fiscale))

    i_min, i_max, venduto, _, wallet, inc = esegui_vendite(
        posizioni, eccessi, minus, frazione=0.5,
        zainetto_lotti=zainetto_lotti, anno_fiscale=anno_fiscale, regime=regime)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "C - ribilanciamento parziale (50%)", i_min, i_max, venduto, d_res,
        "immediato", inc, wallet=wallet, anno_fiscale=anno_fiscale))

    def costo_fiscale_unitario(p):
        campione = p["valore"] * 0.01
        if zainetto_lotti is not None:
            _, i_max_c, _ = imposta_vendita_strutturata(
                p, campione, zainetto_lotti, anno_fiscale, regime)
        else:
            _, i_max_c, _ = imposta_vendita(p, campione, minus)
        if i_max_c is None:
            return float("inf")
        return i_max_c / campione if campione else 0.0

    i_min, i_max, venduto, _, wallet, inc = esegui_vendite(
        posizioni, eccessi, minus, ordine=costo_fiscale_unitario,
        zainetto_lotti=zainetto_lotti, anno_fiscale=anno_fiscale, regime=regime)
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "D - tax-aware (vende prima cio che costa meno in imposta)", i_min, i_max,
        venduto, d_res, "immediato", inc,
        nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post,
        wallet=wallet, anno_fiscale=anno_fiscale))

    out = {
        "totale": round(totale, 2),
        "allocazione_corrente": {ac: round(correnti.get(ac, 0.0) / totale, 4)
                                 for ac in sorted(classi)},
        "target": {ac: round(target.get(ac, 0.0), 4) for ac in sorted(classi)},
        "drift_per_classe": {ac: round(drift[ac], 4) for ac in sorted(classi)},
        "drift_totale": round(drift_iniziale, 4),
        "strategie": strategie,
        "verificare": [
            "Le vendite sono simulate pro-quota sulla posizione: il risultato reale dipende dai lotti effettivi e dal criterio applicato dall'intermediario. Per vendite lot-aware usare scripts/lot_sale.py nei casi coperti.",
            "Non sono inclusi spread e bollo; le commissioni vanno passate al motore di vendita quando note.",
            "Lo zainetto strutturato distingue broker, regime e anno di scadenza; l'ordine 'scadenza piu' vicina prima' e' una scelta del simulatore, non una regola contabile del broker.",
            "Nessuna strategia va scelta solo per il risultato fiscale.",
            "Il drift residuo e' al netto delle imposte: l'imposta esce dal portafoglio, quindi si reinveste meno di quanto si e' venduto.",
        ],
    }
    if regime == "dichiarativo":
        out["verificare"].insert(0,
            "ATTENZIONE: il ribilanciamento dichiarativo usa ancora il PMC del portfolio per le vendite parziali. Rendere azionabile ogni vendita con scripts/lot_sale.py e i lotti reali; non usare la stima aggregata come imposta definitiva.")
    if zainetto_lotti is not None:
        out["zainetto_modalita"] = "strutturato"
        out["anno_fiscale"] = anno_fiscale
        out["regime"] = regime
    else:
        out["zainetto_modalita"] = "legacy_saldo_unico"
        out["minusvalenze_disponibili"] = minus
    return out


def prepara_verifica_strumenti(posizioni, registry_path=None):
    if not registry_path:
        return None
    registry = carica_registry(registry_path)
    return verifica_portafoglio(posizioni, registry)


def aggiungi_argomenti_comuni(parser):
    parser.add_argument("--minus", type=float, default=0.0,
                        help="legacy: saldo minus unico; preferire --zainetto-csv")
    parser.add_argument("--zainetto-csv",
                        help="CSV broker,regime,anno_realizzo,importo")
    parser.add_argument("--anno-fiscale", type=int,
                        help="obbligatorio con --zainetto-csv")
    parser.add_argument("--regime", choices=["amministrato", "dichiarativo"],
                        default="amministrato")
    parser.add_argument("--registry",
                        help="registry ISIN verificato: isin,tipo,fonte,verificato_il")
    parser.add_argument("--strict-instruments", action="store_true",
                        help="blocca l'analisi se anche uno strumento non e' verificato")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analizza", help="metriche, esposizioni, plus/minus latenti")
    a.add_argument("csv")
    aggiungi_argomenti_comuni(a)

    rb = sub.add_parser("ribilancia", help="confronto di strategie di ribilanciamento")
    rb.add_argument("csv")
    rb.add_argument("--target", required=True,
                    help="es. azionario=70,obbligazionario=25,liquidita=5")
    rb.add_argument("--versamento-mensile", type=float, default=0.0)
    aggiungi_argomenti_comuni(rb)

    args = p.parse_args(argv)
    if args.zainetto_csv and args.minus:
        raise SystemExit("Usare --zainetto-csv oppure --minus, non entrambi.")
    if args.zainetto_csv and args.anno_fiscale is None:
        raise SystemExit("--anno-fiscale e' obbligatorio con --zainetto-csv.")
    if args.strict_instruments and not args.registry:
        raise SystemExit("--strict-instruments richiede --registry.")

    try:
        qualita = valida_portafoglio(args.csv)
    except OSError as e:
        print(json.dumps({"errore": str(e)}, indent=2, ensure_ascii=False))
        return 1
    if not qualita.get("azionabile"):
        print(json.dumps({
            "errore": "Validazione portfolio fallita: correggere i dati prima dell'analisi.",
            "validazione_portafoglio": qualita,
        }, indent=2, ensure_ascii=False))
        return 1

    posizioni, lacune = leggi(args.csv)
    try:
        verifica = prepara_verifica_strumenti(posizioni, args.registry)
        if args.strict_instruments and not verifica["tutti_azionabili"]:
            print(json.dumps({
                "errore": "Verifica strumenti fallita: almeno un ISIN/tipo non e' azionabile.",
                "verifica_strumenti": verifica,
                "validazione_portafoglio": qualita,
            }, indent=2, ensure_ascii=False))
            return 1
        wallet = carica_zainetto(args.zainetto_csv) if args.zainetto_csv else None
    except (ValueError, KeyError) as e:
        print(json.dumps({"errore": str(e)}, indent=2, ensure_ascii=False))
        return 1

    if args.cmd == "analizza":
        res = analizza(posizioni, lacune, args.minus, wallet, args.anno_fiscale)
    else:
        res = ribilancia(posizioni, parse_target(args.target), args.minus,
                         args.versamento_mensile, wallet, args.anno_fiscale,
                         args.regime)
    res["validazione_portafoglio"] = qualita
    if verifica is not None:
        res["verifica_strumenti"] = verifica
    else:
        res.setdefault("verificare", []).append(
            "Nessun registry ISIN fornito: i campi tipo del CSV restano dichiarazioni non verificate. Usare --registry e --strict-instruments per un'analisi fiscale azionabile.")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
