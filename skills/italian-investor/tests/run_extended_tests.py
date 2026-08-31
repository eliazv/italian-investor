#!/usr/bin/env python3
"""Test estesi per eventi fiscali, lot-aware sale e qualita' dati."""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from cost_basis import carica_lotti  # noqa: E402
from event_tax import simula_provento  # noqa: E402
from lot_sale import simula_vendita_lotti  # noqa: E402
from portfolio_validator import valida_portafoglio  # noqa: E402


def near(value, expected, tol=0.01):
    return value is not None and abs(float(value) - float(expected)) <= tol


def test_eventi():
    errori = []

    az = simula_provento("azione", "dividendo", 100)
    if not near(az.get("imposta_stimata"), 26):
        errori.append("dividendo azione: imposta attesa 26, ottenuta %r" % az.get("imposta_stimata"))
    if az.get("categoria_reddito") != "reddito_di_capitale":
        errori.append("dividendo azione: categoria errata")

    btp = simula_provento("titolo_stato", "cedola", 100)
    if not near(btp.get("imposta_stimata"), 12.5):
        errori.append("cedola titolo Stato: imposta attesa 12.5")

    etf = simula_provento("etf", "distribuzione", 100, quota_stato=0.5)
    if not near(etf.get("imposta_stimata"), 19.25):
        errori.append("distribuzione ETF 50%% Stato: atteso 19.25, ottenuto %r" % etf.get("imposta_stimata"))

    etf_unknown = simula_provento("etf", "distribuzione", 100)
    sc = etf_unknown.get("imposta_scenario") or {}
    if etf_unknown.get("imposta_stimata") is not None or not near(sc.get("quota_agevolata_0"), 26) or not near(sc.get("quota_agevolata_100"), 12.5):
        errori.append("ETF senza quota_stato deve restituire scenario 12.5-26")

    foreign = simula_provento("azione", "dividendo", 100, ritenuta_estera=15, paese_fonte="US")
    if foreign.get("imposta_stimata") is not None or foreign.get("dato_mancante") != "trattamento_doppia_imposizione_estera":
        errori.append("dividendo con ritenuta estera deve fare hard-stop")

    cert = simula_provento("certificate", "cedola", 100)
    if "errore" not in cert:
        errori.append("provento certificate deve richiedere verifica prodotto")

    return errori


def test_lotti():
    errori = []
    lotti = carica_lotti(os.path.join(BASE, "examples", "lotti-esempio.csv"))

    amm = simula_vendita_lotti("azione", "amministrato", lotti, 140, 15)
    if amm.get("metodo_base") != "cmp":
        errori.append("amministrato deve scegliere CMP nei casi coperti")
    if not near(amm.get("base_fiscale", {}).get("base_costo_vendita_eur"), 1359):
        errori.append("base CMP attesa 1359")
    if not near(amm.get("imposta_stimata"), 192.66):
        errori.append("imposta vendita CMP attesa 192.66, ottenuta %r" % amm.get("imposta_stimata"))

    dic = simula_vendita_lotti("azione", "dichiarativo", lotti, 140, 15)
    if dic.get("metodo_base") != "lifo":
        errori.append("dichiarativo deve scegliere LIFO nei casi coperti")
    if not near(dic.get("base_fiscale", {}).get("base_costo_vendita_eur"), 1651.5):
        errori.append("base LIFO attesa 1651.5")
    if not near(dic.get("imposta_stimata"), 116.61):
        errori.append("imposta vendita LIFO attesa 116.61, ottenuta %r" % dic.get("imposta_stimata"))

    etf = simula_vendita_lotti("etf", "dichiarativo", lotti, 140, 15)
    if "errore" not in etf or etf.get("imposta_stimata") is not None:
        errori.append("ETF lot-aware automatico deve fare hard-stop")

    return errori


def test_validator():
    errori = []
    base = valida_portafoglio(os.path.join(BASE, "examples", "portafoglio-esempio.csv"))
    if not base.get("azionabile"):
        errori.append("portafoglio esempio dovrebbe essere strutturalmente valido: %r" % base.get("errori"))

    contenuto = (
        "isin,nome,tipo,quantita,pmc,prezzo,asset_class,valuta_esposizione,broker,quota_stato\n"
        "US0378331005,Apple A,azione,10,100,120,azionario,USD,BrokerA,0\n"
        "US0378331005,Apple B,azione,5,105,120,azionario,USD,BrokerA,0\n"
    )
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(contenuto)
            path = f.name
        dup = valida_portafoglio(path)
        if dup.get("azionabile"):
            errori.append("duplicato stesso ISIN/broker deve essere bloccante")
        if not any("falsare HHI" in x for x in dup.get("errori", [])):
            errori.append("duplicato deve spiegare l'impatto sulla concentrazione")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    return errori


def main():
    gruppi = (("eventi", test_eventi), ("lotti", test_lotti), ("validator", test_validator))
    falliti = 0
    for nome, fn in gruppi:
        errori = fn()
        if errori:
            falliti += 1
            print("FAIL  %s" % nome)
            for e in errori:
                print("      %s" % e)
        else:
            print("ok    %s" % nome)
    print("\n%d gruppi falliti" % falliti)
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
