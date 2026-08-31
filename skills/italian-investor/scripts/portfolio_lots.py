#!/usr/bin/env python3
"""Registry dei lotti fiscali per posizione `ISIN + broker`.

Il portfolio principale resta aggregato per posizione; questo modulo conserva i
lotti necessari alle vendite parziali. Non decide il regime fiscale e non
converte valute: i costi devono essere gia' espressi in EUR secondo il criterio
fiscale verificato.

Formato CSV:

    isin,broker,data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur

`costi_acquisto_eur` e' opzionale.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

from cost_basis import normalizza_lotto
from instrument_resolver import normalizza_isin, valida_isin

RICHIESTE = {
    "isin", "broker", "data_acquisto", "quantita", "costo_unitario_eur"
}
EPS = 1e-7


def chiave(isin, broker):
    return (normalizza_isin(isin), str(broker or "").strip())


def carica_lotti_portafoglio(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    if not righe:
        raise ValueError("CSV lotti portafoglio vuoto")
    mancanti = RICHIESTE - set(righe[0])
    if mancanti:
        raise ValueError(
            "colonne mancanti nel CSV lotti portafoglio: %s"
            % ", ".join(sorted(mancanti))
        )

    out = []
    for i, row in enumerate(righe):
        isin = normalizza_isin(row.get("isin"))
        broker = str(row.get("broker") or "").strip()
        if not valida_isin(isin):
            raise ValueError("riga %d: ISIN non valido nei lotti: %s" % (i + 2, isin))
        if not broker:
            raise ValueError("riga %d: broker mancante nei lotti" % (i + 2))
        lotto = normalizza_lotto(row, i)
        out.append({
            "isin": isin,
            "broker": broker,
            "lotto": lotto,
        })
    return out


def indicizza(records):
    idx = defaultdict(list)
    for record in records:
        idx[chiave(record["isin"], record["broker"])].append(record["lotto"])
    return dict(idx)


def copia_indice(indice):
    return {
        key: [dict(lotto) for lotto in lotti]
        for key, lotti in indice.items()
    }


def riepilogo(indice):
    out = []
    for (isin, broker), lotti in sorted(indice.items()):
        q = sum(float(x["quantita"]) for x in lotti)
        costo = sum(float(x["costo_totale_eur"]) for x in lotti)
        out.append({
            "isin": isin,
            "broker": broker,
            "lotti": len(lotti),
            "quantita": round(q, 8),
            "costo_fiscale_totale_eur": round(costo, 2),
            "costo_medio_fiscale_eur": round(costo / q, 8) if q else None,
        })
    return out


def valida_copertura(posizioni, indice, tipi_richiesti=None):
    """Verifica coerenza quantitativa dei lotti rispetto al portfolio.

    `tipi_richiesti` limita i tipi per cui la copertura e' obbligatoria. Gli
    altri strumenti possono essere presenti nel portfolio senza lotti, perche'
    la loro base fiscale non viene dedotta automaticamente da questo modulo.
    """
    tipi_richiesti = set(tipi_richiesti or ())
    errori = []
    warning = []
    portfolio_keys = set()

    for p in posizioni:
        key = chiave(p.get("isin"), p.get("broker"))
        portfolio_keys.add(key)
        tipo = str(p.get("tipo") or "").strip().lower()
        if tipo not in tipi_richiesti:
            continue
        lotti = indice.get(key)
        if not lotti:
            errori.append(
                "%s / %s (%s): lotti fiscali mancanti"
                % (p.get("isin"), p.get("broker"), p.get("nome"))
            )
            continue
        q_lotti = sum(float(x["quantita"]) for x in lotti)
        q_port = float(p.get("quantita") or 0.0)
        tolleranza = max(EPS, abs(q_port) * 1e-8)
        if abs(q_lotti - q_port) > tolleranza:
            errori.append(
                "%s / %s: quantita portfolio %.8g != somma lotti %.8g"
                % (p.get("isin"), p.get("broker"), q_port, q_lotti)
            )

    for key, lotti in indice.items():
        if key not in portfolio_keys:
            warning.append(
                "%s / %s: %d lotti non collegati ad alcuna posizione del portfolio"
                % (key[0], key[1], len(lotti))
            )

    return {
        "azionabile": not errori,
        "errori": errori,
        "warning": warning,
        "posizioni_lotti": riepilogo(indice),
    }


def sostituisci_lotti(indice, isin, broker, lotti_residui):
    key = chiave(isin, broker)
    nuovo = copia_indice(indice)
    if lotti_residui:
        nuovo[key] = [dict(x) for x in lotti_residui]
    else:
        nuovo.pop(key, None)
    return nuovo


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("csv")
    args = p.parse_args(argv)
    try:
        idx = indicizza(carica_lotti_portafoglio(args.csv))
        out = {"posizioni_lotti": riepilogo(idx)}
    except (OSError, ValueError) as exc:
        out = {"errore": str(exc)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
