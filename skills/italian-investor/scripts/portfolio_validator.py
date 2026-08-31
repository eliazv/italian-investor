#!/usr/bin/env python3
"""Valida un CSV portfolio prima di analisi fiscali o di rischio.

Il validatore non corregge i dati: segnala errori bloccanti e warning. In
particolare intercetta duplicati che falserebbero metriche di concentrazione,
valori numerici impossibili, unita' sospette sulle obbligazioni e dati fiscali
mancanti.

    python scripts/portfolio_validator.py valida examples/portafoglio-esempio.csv
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict

from instrument_resolver import TIPI_NOTI, normalizza_isin, valida_isin

RICHIESTE = {"isin", "nome", "tipo", "quantita", "pmc", "prezzo", "asset_class"}
VALUTA_RE = re.compile(r"^[A-Z]{3}$")


def _numero(row, campo, n_riga, errori, minimo=None, strettamente=False):
    raw = str(row.get(campo) or "").strip()
    try:
        val = float(raw)
    except ValueError:
        errori.append("riga %d: %s non numerico" % (n_riga, campo))
        return None
    if not math.isfinite(val):
        errori.append("riga %d: %s deve essere finito" % (n_riga, campo))
        return None
    if minimo is not None:
        if strettamente and val <= minimo:
            errori.append("riga %d: %s deve essere > %s" % (n_riga, campo, minimo))
        elif not strettamente and val < minimo:
            errori.append("riga %d: %s deve essere >= %s" % (n_riga, campo, minimo))
    return val


def valida_portafoglio(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        colonne = set(reader.fieldnames or [])
        righe = list(reader)

    errori = []
    warning = []
    mancanti = []

    if not righe:
        return {"azionabile": False, "errori": ["CSV vuoto"], "warning": [], "dati_mancanti": []}

    missing_cols = sorted(RICHIESTE - colonne)
    if missing_cols:
        return {
            "azionabile": False,
            "errori": ["colonne mancanti: %s" % ", ".join(missing_cols)],
            "warning": [],
            "dati_mancanti": [],
        }

    per_isin = defaultdict(list)
    per_isin_broker = defaultdict(list)
    tipi_isin = defaultdict(set)

    for idx, row in enumerate(righe, start=2):
        isin = normalizza_isin(row.get("isin"))
        tipo = str(row.get("tipo") or "").strip().lower()
        nome = str(row.get("nome") or "").strip()
        broker = str(row.get("broker") or "").strip()
        asset_class = str(row.get("asset_class") or "").strip().lower()

        if not nome:
            errori.append("riga %d: nome mancante" % idx)
        if not tipo:
            errori.append("riga %d: tipo mancante" % idx)
        elif tipo not in TIPI_NOTI:
            errori.append("riga %d: tipo non riconosciuto: %s" % (idx, tipo))
        if not asset_class:
            errori.append("riga %d: asset_class mancante" % idx)

        if isin.startswith("CASH-"):
            if tipo != "liquidita":
                errori.append("riga %d: identificatore CASH-* richiede tipo=liquidita" % idx)
        elif not valida_isin(isin):
            errori.append("riga %d: ISIN formalmente non valido: %s" % (idx, isin))

        quantita = _numero(row, "quantita", idx, errori, 0.0, strettamente=True)
        pmc = _numero(row, "pmc", idx, errori, 0.0)
        prezzo = _numero(row, "prezzo", idx, errori, 0.0)

        quota_raw = str(row.get("quota_stato") or "").strip()
        if quota_raw:
            try:
                quota = float(quota_raw)
                if not math.isfinite(quota) or not 0.0 <= quota <= 1.0:
                    errori.append("riga %d: quota_stato deve essere tra 0 e 1" % idx)
            except ValueError:
                errori.append("riga %d: quota_stato non numerica" % idx)
        elif tipo in ("etf", "oicr"):
            mancanti.append("riga %d %s: quota_stato non indicata" % (idx, nome or isin))

        valuta = str(row.get("valuta_esposizione") or "").strip().upper()
        if not valuta:
            mancanti.append("riga %d %s: valuta_esposizione non indicata" % (idx, nome or isin))
        elif not VALUTA_RE.match(valuta):
            warning.append("riga %d: valuta_esposizione sospetta: %s" % (idx, valuta))

        if not broker:
            mancanti.append("riga %d %s: broker non indicato" % (idx, nome or isin))

        if tipo in ("obbligazione", "titolo_stato") and prezzo is not None and pmc is not None:
            if prezzo > 2.0 or pmc > 2.0:
                warning.append(
                    "riga %d %s: pmc/prezzo obbligazionario sembrano espressi in corso percentuale; "
                    "la convenzione del portfolio richiede frazione (101,30 -> 1.0130)" % (idx, nome or isin)
                )

        if tipo == "liquidita" and asset_class != "liquidita":
            warning.append("riga %d %s: tipo=liquidita ma asset_class=%s" % (idx, nome or isin, asset_class))

        per_isin[isin].append(idx)
        per_isin_broker[(isin, broker or "<mancante>")].append(idx)
        tipi_isin[isin].add(tipo)

    for isin, tipi in tipi_isin.items():
        if len(tipi) > 1:
            errori.append("ISIN %s ha tipi incoerenti: %s" % (isin, ", ".join(sorted(tipi))))

    for (isin, broker), linee in sorted(per_isin_broker.items()):
        if len(linee) > 1:
            errori.append(
                "ISIN %s duplicato sul broker %s alle righe %s: portfolio.py lo tratterebbe "
                "come posizioni separate e potrebbe falsare HHI/pesi. Consolidare la posizione "
                "e conservare i lotti in un CSV lotti separato." %
                (isin, broker, ",".join(map(str, linee)))
            )

    for isin, linee in sorted(per_isin.items()):
        if len(linee) > 1:
            brokers = {str(righe[n - 2].get("broker") or "").strip() for n in linee}
            if len(brokers) > 1:
                warning.append(
                    "ISIN %s presente su piu' broker (righe %s): e' corretto mantenerli separati "
                    "fiscalmente, ma per la concentrazione economica va aggregato per ISIN." %
                    (isin, ",".join(map(str, linee)))
                )

    warning.append(
        "Il campo pmc non e' automaticamente una base fiscale verificata: per vendite parziali usare i lotti e il criterio applicabile al regime."
    )

    return {
        "azionabile": not errori,
        "righe": len(righe),
        "errori": errori,
        "warning": warning,
        "dati_mancanti": mancanti,
        "qualita": {
            "errori": len(errori),
            "warning": len(warning),
            "dati_mancanti": len(mancanti),
        },
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("valida")
    v.add_argument("csv")
    args = p.parse_args(argv)

    try:
        out = valida_portafoglio(args.csv)
    except OSError as exc:
        out = {"azionabile": False, "errori": [str(exc)], "warning": [], "dati_mancanti": []}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("azionabile") else 1


if __name__ == "__main__":
    sys.exit(main())
