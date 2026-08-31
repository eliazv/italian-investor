#!/usr/bin/env python3
"""Resolver prudente ISIN -> natura giuridica/tipo fiscale dichiarato.

Non prova a dedurre la natura di uno strumento dal prefisso ISIN o dal nome.
Fa quattro cose utili e deterministiche:

1. valida formalmente l'ISIN con il check digit ISO 6166/Luhn;
2. legge un registry locale verificato su KID/prospetto;
3. confronta `tipo` dichiarato nel portfolio con il tipo verificato;
4. opzionalmente blocca voci troppo vecchie rispetto a una data di riferimento.

Formato registry CSV:
    isin,tipo,fonte,verificato_il

`verificato_il` deve essere ISO `YYYY-MM-DD`. Una voce senza fonte/data valida
non rende il tipo fiscalmente azionabile. Un tipo può essere riconosciuto dal
resolver e restare comunque non calcolabile dal motore fiscale: è intenzionale,
per distinguere "so che prodotto è" da "conosco la regola fiscale applicabile".
"""

import argparse
import csv
import json
import re
import sys
from datetime import date

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
TIPI_NOTI = {
    "etf", "oicr", "etf_non_armonizzato",
    "azione", "obbligazione", "titolo_stato",
    "etc_etn", "certificate", "liquidita",
    "cripto", "fondo_pensione", "pir",
}


def normalizza_isin(isin):
    return str(isin or "").strip().upper()


def valida_isin(isin):
    """Valida struttura e check digit ISIN secondo espansione alfanumerica + Luhn."""
    isin = normalizza_isin(isin)
    if not ISIN_RE.match(isin):
        return False
    cifre = ""
    for ch in isin:
        if ch.isdigit():
            cifre += ch
        else:
            cifre += str(ord(ch) - 55)
    totale = 0
    parity = len(cifre) % 2
    for i, ch in enumerate(cifre):
        n = int(ch)
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return totale % 10 == 0


def parse_data_iso(value, campo="data"):
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("%s non valida, atteso YYYY-MM-DD: %s" % (campo, raw or "<vuota>")) from exc


def carica_registry(percorso):
    if not percorso:
        return {}
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    if not righe:
        return {}
    richieste = {"isin", "tipo", "fonte", "verificato_il"}
    mancanti = richieste - set(righe[0])
    if mancanti:
        raise ValueError("colonne mancanti nel registry strumenti: %s"
                         % ", ".join(sorted(mancanti)))
    out = {}
    for numero, riga in enumerate(righe, start=2):
        isin = normalizza_isin(riga["isin"])
        tipo = str(riga["tipo"]).strip().lower()
        fonte = str(riga.get("fonte") or "").strip()
        verificato_il = str(riga.get("verificato_il") or "").strip()
        if not valida_isin(isin):
            raise ValueError("ISIN non valido nel registry: %s" % isin)
        if tipo not in TIPI_NOTI:
            raise ValueError("tipo non riconosciuto nel registry per %s: %s" % (isin, tipo))
        if not fonte:
            raise ValueError("fonte mancante nel registry per %s (riga %d)" % (isin, numero))
        parse_data_iso(verificato_il, "verificato_il per %s" % isin)
        if isin in out:
            raise ValueError("ISIN duplicato nel registry: %s" % isin)
        out[isin] = {
            "isin": isin,
            "tipo": tipo,
            "fonte": fonte,
            "verificato_il": verificato_il,
        }
    return out


def _freschezza(voce, data_riferimento=None, max_age_giorni=None):
    """Restituisce metadati di freschezza senza inventare una soglia di default."""
    try:
        verificata = parse_data_iso(voce.get("verificato_il"), "verificato_il")
    except ValueError as exc:
        return {
            "data_valida": False,
            "scaduta": None,
            "eta_giorni": None,
            "motivo": str(exc),
        }

    if max_age_giorni is None:
        return {
            "data_valida": True,
            "scaduta": None,
            "eta_giorni": None,
            "motivo": None,
        }

    try:
        max_age_giorni = int(max_age_giorni)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_age_giorni deve essere un intero >= 0") from exc
    if max_age_giorni < 0:
        raise ValueError("max_age_giorni deve essere >= 0")

    riferimento = (parse_data_iso(data_riferimento, "data_riferimento")
                    if data_riferimento else date.today())
    eta = (riferimento - verificata).days
    # Una verifica nel futuro rispetto alla data di riferimento è un dato incoerente,
    # non una voce 'molto fresca'.
    if eta < 0:
        return {
            "data_valida": True,
            "scaduta": True,
            "eta_giorni": eta,
            "motivo": "verificato_il è successiva alla data di riferimento",
        }
    return {
        "data_valida": True,
        "scaduta": eta > max_age_giorni,
        "eta_giorni": eta,
        "motivo": ("verifica più vecchia di %d giorni" % max_age_giorni
                   if eta > max_age_giorni else None),
    }


def risolvi(isin, tipo_dichiarato=None, registry=None,
            data_riferimento=None, max_age_giorni=None):
    isin = normalizza_isin(isin)
    tipo_dichiarato = (str(tipo_dichiarato).strip().lower()
                       if tipo_dichiarato is not None else None)

    if isin.startswith("CASH-"):
        coerente = tipo_dichiarato in (None, "liquidita")
        return {
            "isin": isin,
            "isin_valido": True,
            "sintetico": True,
            "tipo_dichiarato": tipo_dichiarato,
            "tipo_verificato": "liquidita",
            "coerente": coerente,
            "calcolo_fiscale_azionabile": coerente,
            "fonte": "convenzione interna CASH-*",
            "verificato_il": "n/a",
            "freschezza": {"non_applicabile": True},
        }

    if not valida_isin(isin):
        return {
            "isin": isin,
            "isin_valido": False,
            "tipo_dichiarato": tipo_dichiarato,
            "tipo_verificato": None,
            "coerente": False,
            "calcolo_fiscale_azionabile": False,
            "motivo": "ISIN formalmente non valido: correggere il dato prima dell'analisi.",
        }

    voce = (registry or {}).get(isin)
    if not voce:
        return {
            "isin": isin,
            "isin_valido": True,
            "tipo_dichiarato": tipo_dichiarato,
            "tipo_verificato": None,
            "coerente": None,
            "calcolo_fiscale_azionabile": False,
            "motivo": "ISIN non presente nel registry verificato: recuperare KID/prospetto e classificare la natura giuridica.",
        }

    try:
        freschezza = _freschezza(voce, data_riferimento, max_age_giorni)
    except ValueError as exc:
        return {
            "isin": isin,
            "isin_valido": True,
            "tipo_dichiarato": tipo_dichiarato,
            "tipo_verificato": voce.get("tipo"),
            "coerente": None,
            "calcolo_fiscale_azionabile": False,
            "fonte": voce.get("fonte"),
            "verificato_il": voce.get("verificato_il"),
            "motivo": str(exc),
        }

    metadati_ok = bool(voce.get("fonte") and freschezza.get("data_valida"))
    coerente = tipo_dichiarato is None or tipo_dichiarato == voce["tipo"]
    fresca_ok = freschezza.get("scaduta") is not True
    azionabile = bool(metadati_ok and coerente and fresca_ok)

    if azionabile:
        motivo = None
    elif not coerente:
        motivo = "Tipo incoerente con il registry."
    elif not metadati_ok:
        motivo = freschezza.get("motivo") or "Voce registry priva di fonte o data valida."
    else:
        motivo = "Voce registry non abbastanza recente: %s." % (freschezza.get("motivo") or "verifica scaduta")

    return {
        "isin": isin,
        "isin_valido": True,
        "tipo_dichiarato": tipo_dichiarato,
        "tipo_verificato": voce["tipo"],
        "coerente": coerente,
        "calcolo_fiscale_azionabile": azionabile,
        "fonte": voce.get("fonte"),
        "verificato_il": voce.get("verificato_il"),
        "freschezza": freschezza,
        "motivo": motivo,
    }


def verifica_portafoglio(posizioni, registry=None,
                         data_riferimento=None, max_age_giorni=None):
    esiti = []
    for p in posizioni:
        esito = risolvi(
            p.get("isin"), p.get("tipo"), registry,
            data_riferimento=data_riferimento,
            max_age_giorni=max_age_giorni,
        )
        esito["nome"] = p.get("nome")
        esiti.append(esito)
    return {
        "tutti_azionabili": all(e["calcolo_fiscale_azionabile"] for e in esiti),
        "non_verificati": [e for e in esiti if not e["calcolo_fiscale_azionabile"]],
        "strumenti": esiti,
        "policy_freschezza": {
            "max_age_giorni": max_age_giorni,
            "data_riferimento": data_riferimento,
        },
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve", help="valida e risolve un ISIN")
    r.add_argument("--isin", required=True)
    r.add_argument("--tipo")
    r.add_argument("--registry")
    r.add_argument("--max-age-giorni", type=int,
                   help="blocca voci più vecchie della soglia; nessun default implicito")
    r.add_argument("--data-riferimento",
                   help="YYYY-MM-DD; utile per test/riproducibilità, altrimenti oggi")
    a = p.parse_args(argv)
    try:
        reg = carica_registry(a.registry)
        out = risolvi(
            a.isin, a.tipo, reg,
            data_riferimento=a.data_riferimento,
            max_age_giorni=a.max_age_giorni,
        )
    except ValueError as e:
        out = {"errore": str(e)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
