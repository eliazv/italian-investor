#!/usr/bin/env python3
"""Resolver prudente ISIN -> natura giuridica/tipo fiscale dichiarato.

Non prova a dedurre la natura di uno strumento dal prefisso ISIN o dal nome.
Fa tre cose utili e deterministiche:

1. valida formalmente l'ISIN con il check digit ISO 6166/Luhn;
2. legge un registry locale verificato su KID/prospetto;
3. confronta `tipo` dichiarato nel portfolio con il tipo verificato.

Formato registry CSV:
    isin,tipo,fonte,verificato_il

Una voce senza fonte o data non rende il tipo fiscalmente azionabile. Un tipo
puo' essere riconosciuto dal resolver e restare comunque non calcolabile dal
motore fiscale: e' intenzionale, per distinguere "so che prodotto e'" da
"conosco la regola fiscale applicabile".
"""

import argparse
import csv
import json
import re
import sys

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
    for riga in righe:
        isin = normalizza_isin(riga["isin"])
        tipo = str(riga["tipo"]).strip().lower()
        if not valida_isin(isin):
            raise ValueError("ISIN non valido nel registry: %s" % isin)
        if tipo not in TIPI_NOTI:
            raise ValueError("tipo non riconosciuto nel registry per %s: %s" % (isin, tipo))
        out[isin] = {
            "isin": isin,
            "tipo": tipo,
            "fonte": str(riga.get("fonte") or "").strip(),
            "verificato_il": str(riga.get("verificato_il") or "").strip(),
        }
    return out


def risolvi(isin, tipo_dichiarato=None, registry=None):
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

    metadati_ok = bool(voce.get("fonte") and voce.get("verificato_il"))
    coerente = tipo_dichiarato is None or tipo_dichiarato == voce["tipo"]
    return {
        "isin": isin,
        "isin_valido": True,
        "tipo_dichiarato": tipo_dichiarato,
        "tipo_verificato": voce["tipo"],
        "coerente": coerente,
        "calcolo_fiscale_azionabile": bool(metadati_ok and coerente),
        "fonte": voce.get("fonte"),
        "verificato_il": voce.get("verificato_il"),
        "motivo": (None if metadati_ok and coerente else
                   "Tipo incoerente con il registry." if not coerente else
                   "Voce registry priva di fonte o data di verifica."),
    }


def verifica_portafoglio(posizioni, registry=None):
    esiti = []
    for p in posizioni:
        esito = risolvi(p.get("isin"), p.get("tipo"), registry)
        esito["nome"] = p.get("nome")
        esiti.append(esito)
    return {
        "tutti_azionabili": all(e["calcolo_fiscale_azionabile"] for e in esiti),
        "non_verificati": [e for e in esiti if not e["calcolo_fiscale_azionabile"]],
        "strumenti": esiti,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve", help="valida e risolve un ISIN")
    r.add_argument("--isin", required=True)
    r.add_argument("--tipo")
    r.add_argument("--registry")
    a = p.parse_args(argv)
    try:
        reg = carica_registry(a.registry)
        out = risolvi(a.isin, a.tipo, reg)
    except ValueError as e:
        out = {"errore": str(e)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
