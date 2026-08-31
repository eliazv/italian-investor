#!/usr/bin/env python3
"""Analisi di portafoglio e confronto di strategie di ribilanciamento tax-aware.

Calcoli deterministici, nessuna dipendenza esterna, nessuna raccomandazione:
lo script produce numeri, l'interpretazione resta all'analisi.

    python scripts/portfolio.py analizza portafoglio.csv
    python scripts/portfolio.py ribilancia portafoglio.csv \
        --target azionario=70,obbligazionario=25,liquidita=5 \
        --zainetto-csv zainetto.csv --anno-fiscale 2026

Per vendite parziali lot-aware:

    python scripts/portfolio.py ribilancia portafoglio.csv \
        --target azionario=70,obbligazionario=25,liquidita=5 \
        --lotti-posizioni-csv lotti-portafoglio.csv \
        --zainetto-csv zainetto.csv --anno-fiscale 2026 --regime dichiarativo

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
from lot_sale import TIPI_LOT_AWARE, simula_vendita_lotti
from portfolio_lots import (
    carica_lotti_portafoglio,
    copia_indice as copia_lotti_posizioni,
    indicizza as indicizza_lotti_posizioni,
    riepilogo as riepilogo_lotti_posizioni,
    sostituisci_lotti,
    valida_copertura as valida_copertura_lotti,
)
from portfolio_validator import valida_portafoglio
from tax_engine import simula_vendita
from zainetto import aggiungi as aggiungi_minus
from zainetto import carica_csv as carica_zainetto
from zainetto import consuma as consuma_minus
from zainetto import disponibile as minus_disponibile
from zainetto import riepilogo as riepilogo_zainetto

RICHIESTE = ["isin", "nome", "tipo", "quantita", "pmc", "prezzo", "asset_class"]
OPZIONALI = [
    "valuta_esposizione", "valuta_quotazione", "area", "settore", "broker",
    "quota_stato",
]


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
                "isin": riga["isin"].strip().upper(),
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
    return {
        k: {"valore": round(v, 2), "peso": round(v / totale, 4)}
        for k, v in sorted(agg.items(), key=lambda kv: -kv[1])
    }


def concentrazione_per_isin(posizioni, totale):
    """Concentrazione economica aggregata per ISIN, indipendente dal broker."""
    valori = defaultdict(float)
    nomi = {}
    for p in posizioni:
        valori[p["isin"]] += p["valore"]
        nomi.setdefault(p["isin"], p["nome"])

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
    imposta_min = imposta_max = 0.0
    non_calcolabili, quote_ignote = [], []

    # Liquidazione integrale: il totale del costo dei lotti coincide con la base
    # complessiva, ma qui il PMC resta un input dichiarato. La stima non usa lo
    # zainetto per evitare un ordine arbitrario fra broker.
    for p in posizioni:
        i_min, i_max, _ = imposta_vendita(p, p["valore"], 0.0)
        if i_min is None:
            res = simula_vendita(p["tipo"], p["pmc"], p["prezzo"], p["quantita"])
            non_calcolabili.append(
                "%s (%s): %s" % (p["nome"], p["tipo"], res.get("errore", "non calcolabile"))
            )
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
        "imposta_se_liquidato_tutto": (
            round(imposta_max, 2)
            if round(imposta_min, 2) == round(imposta_max, 2) else None
        ),
        "imposta_se_liquidato_tutto_intervallo": [
            round(imposta_min, 2), round(imposta_max, 2)
        ],
        "posizioni_con_quota_agevolata_ignota": quote_ignote,
        "posizioni_non_calcolabili": non_calcolabili,
        "dati_mancanti": lacune,
        "verificare": [
            "La concentrazione HHI/top-5 e' aggregata per ISIN; la ripartizione per broker resta separata per non perdere il contesto fiscale.",
            "La valuta di esposizione va letta sui sottostanti, non sulla valuta di quotazione: confermare il dato per ogni fondo.",
            "L'imposta di liquidazione integrale non applica lo zainetto: e' una soglia indicativa, non una simulazione di vendita ordinata.",
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
        k, sep, v = pezzo.partition("=")
        if not sep or not k.strip():
            raise SystemExit("Target non valido: %s" % pezzo)
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
    """Modalita' legacy: un unico saldo minus numerico e PMC del portfolio."""
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, minus_disponibili
    quota = min(1.0, importo / p["valore"])
    res = simula_vendita(
        p["tipo"], p["pmc"], p["prezzo"], p["quantita"] * quota,
        minus_disponibili=minus_disponibili,
        quota_stato=p.get("quota_stato"),
    )
    return _risultato_imposta(res, minus_disponibili)


def _simula_posizione(p, importo, minus, regime, lotti_posizioni=None):
    """Simula una vendita e, se disponibile, consuma i lotti della posizione."""
    if importo <= 0 or p["valore"] <= 0:
        return {
            "vendita": None,
            "lotti_posizioni": copia_lotti_posizioni(lotti_posizioni or {}),
            "meta": {"modalita_base": "nessuna_vendita"},
        }

    quota = min(1.0, importo / p["valore"])
    q_venduta = p["quantita"] * quota
    stato_lotti = copia_lotti_posizioni(lotti_posizioni or {})

    if lotti_posizioni is not None and p["tipo"] in TIPI_LOT_AWARE:
        key = (p["isin"], p.get("broker"))
        lotti = stato_lotti.get(key)
        if not lotti:
            return {
                "errore": "Lotti fiscali mancanti per %s / %s" % key,
                "vendita": None,
                "lotti_posizioni": stato_lotti,
                "meta": {"modalita_base": "lotti_mancanti"},
            }
        lot_res = simula_vendita_lotti(
            p["tipo"], regime, lotti, p["prezzo"], q_venduta,
            minus_disponibili=minus,
            quota_stato=p.get("quota_stato"),
        )
        if lot_res.get("errore"):
            return {
                "errore": lot_res["errore"],
                "vendita": None,
                "lotti_posizioni": stato_lotti,
                "meta": {
                    "modalita_base": "lot_aware",
                    "metodo_base": lot_res.get("metodo_base"),
                },
            }
        stato_lotti = sostituisci_lotti(
            stato_lotti, p["isin"], p.get("broker"), lot_res.get("lotti_residui")
        )
        return {
            "vendita": lot_res["vendita"],
            "lotti_posizioni": stato_lotti,
            "meta": {
                "modalita_base": "lot_aware",
                "metodo_base": lot_res["metodo_base"],
                "pmc_fiscale_derivato": lot_res["pmc_fiscale_derivato"],
                "base_costo_vendita_eur": lot_res["base_fiscale"].get("base_costo_vendita_eur"),
                "quantita_venduta": round(q_venduta, 8),
            },
        }

    vendita = simula_vendita(
        p["tipo"], p["pmc"], p["prezzo"], q_venduta,
        minus_disponibili=minus,
        quota_stato=p.get("quota_stato"),
    )
    return {
        "vendita": vendita,
        "lotti_posizioni": stato_lotti,
        "meta": {
            "modalita_base": "pmc_csv",
            "quantita_venduta": round(q_venduta, 8),
            "nota": (
                "Strumento non coperto dal lot engine oppure CSV lotti non fornito; "
                "la base deriva dal PMC dichiarato nel portfolio."
            ),
        },
    }


def _aggiorna_wallet(work, vendita, broker, anno_fiscale, regime):
    if work is None or vendita is None:
        return work
    if vendita.get("risultato_lordo", 0) > 0:
        usate = float(vendita.get("minusvalenze_utilizzate", 0.0) or 0.0)
        if usate > 0:
            return consuma_minus(work, usate, broker, anno_fiscale, regime)["lotti"]
    else:
        generata = vendita.get("minusvalenza_generata")
        if generata is not None and float(generata) > 0:
            return aggiungi_minus(work, broker, regime, anno_fiscale, float(generata))
    return work


def imposta_vendita_strutturata(p, importo, lotti, anno_fiscale,
                                 regime="amministrato", lotti_posizioni=None):
    """Vendita con zainetto strutturato e, opzionalmente, base fiscale a lotti."""
    if importo <= 0 or p["valore"] <= 0:
        return 0.0, 0.0, copy.deepcopy(lotti), copia_lotti_posizioni(lotti_posizioni or {}), None
    broker = p.get("broker")
    if not broker or broker == "non indicato":
        return None, None, copy.deepcopy(lotti), copia_lotti_posizioni(lotti_posizioni or {}), None
    try:
        minus = minus_disponibile(lotti, broker, anno_fiscale, regime)
    except ValueError:
        return None, None, copy.deepcopy(lotti), copia_lotti_posizioni(lotti_posizioni or {}), None

    calc = _simula_posizione(p, importo, minus, regime, lotti_posizioni)
    if calc.get("errore") or not calc.get("vendita"):
        return None, None, copy.deepcopy(lotti), calc.get("lotti_posizioni"), calc

    vendita = calc["vendita"]
    work = _aggiorna_wallet(copy.deepcopy(lotti), vendita, broker, anno_fiscale, regime)
    i_min, i_max, _ = _risultato_imposta(vendita, minus)
    return i_min, i_max, work, calc["lotti_posizioni"], calc


def esegui_vendite(posizioni, eccessi, minus=0.0, ordine=None, frazione=1.0,
                    zainetto_lotti=None, anno_fiscale=None,
                    regime="amministrato", lotti_posizioni=None):
    """Vende dalle asset class in eccesso mantenendo zainetto e lotti residui."""
    candidate = [p for p in posizioni if eccessi.get(p["asset_class"], 0) > 0]
    if ordine:
        candidate.sort(key=ordine)
    da_vendere = {ac: v * frazione for ac, v in eccessi.items() if v > 0}
    imposta_min = imposta_max = 0.0
    venduto = defaultdict(float)
    incalcolabili = []
    dettagli = []
    minus_legacy = minus
    wallet = copy.deepcopy(zainetto_lotti) if zainetto_lotti is not None else None
    stato_lotti = copia_lotti_posizioni(lotti_posizioni or {}) if lotti_posizioni is not None else None

    for p in candidate:
        residuo_ac = da_vendere.get(p["asset_class"], 0.0)
        if residuo_ac <= 0:
            continue
        importo = min(residuo_ac, p["valore"])

        if wallet is not None:
            i_min, i_max, wallet_nuovo, lotti_nuovi, calc = imposta_vendita_strutturata(
                p, importo, wallet, anno_fiscale, regime, stato_lotti
            )
            if i_min is not None:
                wallet = wallet_nuovo
                stato_lotti = lotti_nuovi
        else:
            calc = _simula_posizione(p, importo, minus_legacy, regime, stato_lotti)
            if calc.get("errore") or not calc.get("vendita"):
                i_min = i_max = None
            else:
                vendita = calc["vendita"]
                i_min, i_max, minus_legacy = _risultato_imposta(vendita, minus_legacy)
                stato_lotti = calc["lotti_posizioni"]

        if i_min is None:
            motivo = (calc or {}).get("errore") or "base fiscale/non calcolabile"
            incalcolabili.append("%s: %s" % (p["nome"], motivo))
            continue

        imposta_min += i_min
        imposta_max += i_max
        venduto[p["asset_class"]] += importo
        da_vendere[p["asset_class"]] = residuo_ac - importo
        dettagli.append({
            "isin": p["isin"],
            "nome": p["nome"],
            "broker": p.get("broker"),
            "importo_venduto": round(importo, 2),
            "imposta_min": round(i_min, 2),
            "imposta_max": round(i_max, 2),
            **((calc or {}).get("meta") or {}),
        })

    return (
        imposta_min, imposta_max, dict(venduto), minus_legacy, wallet,
        stato_lotti, incalcolabili, dettagli,
    )


def drift_post_tax(correnti, target, classi, totale, venduto, imposta):
    nuovo_totale = totale - imposta
    if nuovo_totale <= 0:
        return None, 0.0
    valori = {ac: correnti.get(ac, 0.0) - venduto.get(ac, 0.0) for ac in classi}
    reinvestibile = sum(venduto.values()) - imposta
    mancanze = {
        ac: max(0.0, target.get(ac, 0.0) * nuovo_totale - valori[ac])
        for ac in classi
    }
    totale_mancanze = sum(mancanze.values())
    if totale_mancanze > 0 and reinvestibile > 0:
        for ac in classi:
            valori[ac] += reinvestibile * mancanze[ac] / totale_mancanze
    drift = sum(
        abs(valori[ac] / nuovo_totale - target.get(ac, 0.0)) for ac in classi
    ) / 2
    return round(drift, 4), round(nuovo_totale, 2)


def voce_strategia(nome, imposta_min, imposta_max, venduto, drift, tempo,
                   incalcolabili, nota=None, wallet=None, anno_fiscale=None,
                   lotti_posizioni=None, dettagli_vendite=None):
    v = {
        "strategia": nome,
        "imposta_stimata": round(imposta_max, 2),
        "venduto": round(sum(venduto.values()), 2),
        "drift_residuo": drift,
        "tempo": tempo,
        "non_calcolabili": incalcolabili,
        "dettagli_vendite": dettagli_vendite or [],
    }
    if round(imposta_min, 2) != round(imposta_max, 2):
        v["imposta_intervallo"] = [round(imposta_min, 2), round(imposta_max, 2)]
        v["nota_imposta"] = (
            "Quota agevolata ignota su almeno un OICR: la simulazione usa "
            "l'estremo prudenziale (imposta massima)."
        )
    if wallet is not None and anno_fiscale is not None:
        v["zainetto_dopo"] = riepilogo_zainetto(wallet, anno_fiscale)
    if lotti_posizioni is not None:
        v["lotti_posizioni_dopo"] = riepilogo_lotti_posizioni(lotti_posizioni)
    if nota:
        v["nota"] = nota
    return v


def ribilancia(posizioni, target, minus=0.0, versamento_mensile=0.0,
                zainetto_lotti=None, anno_fiscale=None,
                regime="amministrato", lotti_posizioni=None):
    totale = sum(p["valore"] for p in posizioni)
    correnti = defaultdict(float)
    for p in posizioni:
        correnti[p["asset_class"]] += p["valore"]

    classi = set(list(correnti) + list(target))
    drift = {ac: correnti.get(ac, 0.0) / totale - target.get(ac, 0.0) for ac in classi}
    eccessi = {ac: d * totale for ac, d in drift.items() if d > 0}
    drift_iniziale = sum(abs(d) for d in drift.values()) / 2
    strategie = []

    def esegui(**kwargs):
        return esegui_vendite(
            posizioni, eccessi, minus,
            zainetto_lotti=zainetto_lotti,
            anno_fiscale=anno_fiscale,
            regime=regime,
            lotti_posizioni=lotti_posizioni,
            **kwargs
        )

    i_min, i_max, venduto, _, wallet, lp, inc, det = esegui()
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "A - ribilanciamento immediato", i_min, i_max, venduto, d_res,
        "immediato", inc,
        nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post,
        wallet=wallet, anno_fiscale=anno_fiscale,
        lotti_posizioni=lp, dettagli_vendite=det,
    ))

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
    nota_b = (
        "Nessuna vendita, nessuna imposta: serve capitale nuovo pari a %.0f EUR "
        "perche' le classi in eccesso rientrino nel target per diluizione."
        % fabbisogno
    )
    if impossibile:
        nota_b += (
            " Le classi %s hanno target 0%%: senza vendite non si azzerano mai."
            % ", ".join(sorted(impossibile))
        )
    if versamento_mensile > 0 and not impossibile:
        tempo_b = "circa %d mesi" % round(fabbisogno / versamento_mensile)
    elif versamento_mensile > 0:
        tempo_b = "non raggiungibile senza vendite"
    else:
        tempo_b = "non calcolabile: passare --versamento-mensile"
    strategie.append(voce_strategia(
        "B - solo nuovi versamenti", 0.0, 0.0, {},
        round(drift_iniziale, 4) if impossibile else 0.0,
        tempo_b, [], nota=nota_b,
        wallet=copy.deepcopy(zainetto_lotti) if zainetto_lotti is not None else None,
        anno_fiscale=anno_fiscale,
        lotti_posizioni=(copia_lotti_posizioni(lotti_posizioni)
                         if lotti_posizioni is not None else None),
    ))

    i_min, i_max, venduto, _, wallet, lp, inc, det = esegui(frazione=0.5)
    d_res, _ = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "C - ribilanciamento parziale (50%)", i_min, i_max, venduto, d_res,
        "immediato", inc, wallet=wallet, anno_fiscale=anno_fiscale,
        lotti_posizioni=lp, dettagli_vendite=det,
    ))

    def costo_fiscale_unitario(p):
        campione = p["valore"] * 0.01
        if zainetto_lotti is not None:
            i_min_c, i_max_c, _, _, _ = imposta_vendita_strutturata(
                p, campione, zainetto_lotti, anno_fiscale, regime, lotti_posizioni
            )
        else:
            calc = _simula_posizione(p, campione, minus, regime, lotti_posizioni)
            if calc.get("errore") or not calc.get("vendita"):
                return float("inf")
            i_min_c, i_max_c, _ = _risultato_imposta(calc["vendita"], minus)
        if i_max_c is None:
            return float("inf")
        return i_max_c / campione if campione else 0.0

    i_min, i_max, venduto, _, wallet, lp, inc, det = esegui(
        ordine=costo_fiscale_unitario
    )
    d_res, tot_post = drift_post_tax(correnti, target, classi, totale, venduto, i_max)
    strategie.append(voce_strategia(
        "D - tax-aware (vende prima cio che costa meno in imposta)",
        i_min, i_max, venduto, d_res, "immediato", inc,
        nota="Portafoglio dopo le imposte: %.2f EUR." % tot_post,
        wallet=wallet, anno_fiscale=anno_fiscale,
        lotti_posizioni=lp, dettagli_vendite=det,
    ))

    out = {
        "totale": round(totale, 2),
        "allocazione_corrente": {
            ac: round(correnti.get(ac, 0.0) / totale, 4) for ac in sorted(classi)
        },
        "target": {ac: round(target.get(ac, 0.0), 4) for ac in sorted(classi)},
        "drift_per_classe": {ac: round(drift[ac], 4) for ac in sorted(classi)},
        "drift_totale": round(drift_iniziale, 4),
        "strategie": strategie,
        "base_fiscale_modalita": (
            "lotti_per_isin_broker" if lotti_posizioni is not None else "pmc_csv"
        ),
        "verificare": [
            "ETF/OICR e strumenti fuori dal lot engine continuano a usare il PMC dichiarato: la disciplina della loro base/provento va verificata separatamente.",
            "Non sono inclusi spread e bollo; le commissioni di vendita vanno passate al motore quando note.",
            "Lo zainetto strutturato distingue broker, regime e anno di scadenza; l'ordine 'scadenza piu' vicina prima' e' una scelta del simulatore, non una regola contabile del broker.",
            "Nessuna strategia va scelta solo per il risultato fiscale.",
            "Il drift residuo e' al netto delle imposte: l'imposta esce dal portafoglio, quindi si reinveste meno di quanto si e' venduto.",
        ],
    }
    if regime == "dichiarativo" and lotti_posizioni is None:
        out["verificare"].insert(0,
            "ATTENZIONE: senza --lotti-posizioni-csv le vendite parziali dichiarative usano il PMC del portfolio e non sono fiscalmente definitive.")
    elif lotti_posizioni is not None:
        out["verificare"].insert(0,
            "Per i tipi coperti dal lot engine ogni strategia riparte dagli stessi lotti iniziali e consuma CMP/LIFO operazione per operazione; le strategie restano scenari indipendenti.")

    if zainetto_lotti is not None:
        out["zainetto_modalita"] = "strutturato"
        out["anno_fiscale"] = anno_fiscale
        out["regime"] = regime
    else:
        out["zainetto_modalita"] = "legacy_saldo_unico"
        out["minusvalenze_disponibili"] = minus
    if lotti_posizioni is not None:
        out["lotti_posizioni_iniziali"] = riepilogo_lotti_posizioni(lotti_posizioni)
    return out


def prepara_verifica_strumenti(posizioni, registry_path=None,
                                data_riferimento=None, max_age_giorni=None):
    if not registry_path:
        return None
    registry = carica_registry(registry_path)
    return verifica_portafoglio(
        posizioni, registry,
        data_riferimento=data_riferimento,
        max_age_giorni=max_age_giorni,
    )


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
    parser.add_argument("--max-age-giorni", type=int,
                        help="con --registry, rende non azionabili verifiche piu vecchie")
    parser.add_argument("--data-riferimento",
                        help="YYYY-MM-DD per policy di freschezza riproducibile")
    parser.add_argument("--lotti-posizioni-csv",
                        help="CSV isin,broker,data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur")


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
    if (args.max_age_giorni is not None or args.data_riferimento) and not args.registry:
        raise SystemExit("--max-age-giorni/--data-riferimento richiedono --registry.")

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
        verifica = prepara_verifica_strumenti(
            posizioni, args.registry, args.data_riferimento, args.max_age_giorni
        )
        if args.strict_instruments and not verifica["tutti_azionabili"]:
            print(json.dumps({
                "errore": "Verifica strumenti fallita: almeno un ISIN/tipo non e' azionabile.",
                "verifica_strumenti": verifica,
                "validazione_portafoglio": qualita,
            }, indent=2, ensure_ascii=False))
            return 1

        wallet = carica_zainetto(args.zainetto_csv) if args.zainetto_csv else None
        indice_lotti = None
        copertura_lotti = None
        if args.lotti_posizioni_csv:
            records = carica_lotti_portafoglio(args.lotti_posizioni_csv)
            indice_lotti = indicizza_lotti_posizioni(records)
            copertura_lotti = valida_copertura_lotti(
                posizioni, indice_lotti, TIPI_LOT_AWARE
            )
            if not copertura_lotti["azionabile"]:
                print(json.dumps({
                    "errore": "Validazione lotti fiscali fallita: correggere il dataset prima della simulazione.",
                    "validazione_lotti": copertura_lotti,
                }, indent=2, ensure_ascii=False))
                return 1
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({"errore": str(e)}, indent=2, ensure_ascii=False))
        return 1

    if args.cmd == "analizza":
        res = analizza(posizioni, lacune, args.minus, wallet, args.anno_fiscale)
    else:
        res = ribilancia(
            posizioni, parse_target(args.target), args.minus,
            args.versamento_mensile, wallet, args.anno_fiscale,
            args.regime, indice_lotti,
        )

    res["validazione_portafoglio"] = qualita
    if copertura_lotti is not None:
        res["validazione_lotti"] = copertura_lotti
    if verifica is not None:
        res["verifica_strumenti"] = verifica
    else:
        res.setdefault("verificare", []).append(
            "Nessun registry ISIN fornito: i campi tipo del CSV restano dichiarazioni non verificate. Usare --registry e --strict-instruments per un'analisi fiscale azionabile."
        )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
