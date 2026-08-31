#!/usr/bin/env python3
"""Test estesi per eventi fiscali, lot-aware sale e qualita' dati."""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from cost_basis import carica_lotti  # noqa: E402
from event_tax import simula_provento  # noqa: E402
from lot_sale import TIPI_LOT_AWARE, simula_vendita_lotti  # noqa: E402
from portfolio import analizza, leggi, ribilancia  # noqa: E402
from portfolio_lots import (  # noqa: E402
    carica_lotti_portafoglio,
    indicizza,
    valida_copertura,
)
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

    italia = simula_provento("azione", "dividendo", 100, paese_fonte="IT")
    if not near(italia.get("imposta_stimata"), 26):
        errori.append("paese_fonte=IT non deve attivare il ramo estero")

    btp = simula_provento("titolo_stato", "cedola", 100)
    if not near(btp.get("imposta_stimata"), 12.5):
        errori.append("cedola titolo Stato: imposta attesa 12.5")

    etf = simula_provento("etf", "distribuzione", 100, quota_stato=0.5)
    if not near(etf.get("imposta_stimata"), 19.25):
        errori.append("distribuzione ETF 50%% Stato: atteso 19.25, ottenuto %r" % etf.get("imposta_stimata"))

    etf_unknown = simula_provento("etf", "distribuzione", 100)
    sc = etf_unknown.get("imposta_scenario") or {}
    if (etf_unknown.get("imposta_stimata") is not None or
            not near(sc.get("quota_agevolata_0"), 26) or
            not near(sc.get("quota_agevolata_100"), 12.5)):
        errori.append("ETF senza quota_stato deve restituire scenario 12.5-26")

    foreign = simula_provento(
        "azione", "dividendo", 100, ritenuta_estera=15, paese_fonte="US"
    )
    if (foreign.get("imposta_stimata") is not None or
            foreign.get("dato_mancante") != "trattamento_doppia_imposizione_estera"):
        errori.append("dividendo con ritenuta estera deve fare hard-stop")

    foreign_no_withholding = simula_provento("azione", "dividendo", 100, paese_fonte="US")
    if (foreign_no_withholding.get("imposta_stimata") is not None or
            foreign_no_withholding.get("dato_mancante") != "trattamento_doppia_imposizione_estera"):
        errori.append("fonte estera deve fare hard-stop anche se la ritenuta non e' stata indicata")

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
    residui_amm = amm.get("lotti_residui") or []
    if not near(sum(x["quantita"] for x in residui_amm), 85, 0.000001):
        errori.append("CMP deve lasciare 85 unita residue")
    if not near(sum(x["costo_totale_eur"] for x in residui_amm), 7701, 0.001):
        errori.append("CMP deve preservare il costo residuo 7701")

    dic = simula_vendita_lotti("azione", "dichiarativo", lotti, 140, 15)
    if dic.get("metodo_base") != "lifo":
        errori.append("dichiarativo deve scegliere LIFO nei casi coperti")
    if not near(dic.get("base_fiscale", {}).get("base_costo_vendita_eur"), 1651.5):
        errori.append("base LIFO attesa 1651.5")
    if not near(dic.get("imposta_stimata"), 116.61):
        errori.append("imposta vendita LIFO attesa 116.61, ottenuta %r" % dic.get("imposta_stimata"))
    residui_dic = dic.get("lotti_residui") or []
    if not near(sum(x["quantita"] for x in residui_dic), 85, 0.000001):
        errori.append("LIFO deve lasciare 85 unita residue")
    seconda = simula_vendita_lotti("azione", "dichiarativo", residui_dic, 140, 10)
    if not near(seconda.get("base_fiscale", {}).get("base_costo_vendita_eur"), 1026):
        errori.append("vendita LIFO sequenziale: base attesa 1026")

    etf = simula_vendita_lotti("etf", "dichiarativo", lotti, 140, 15)
    if "errore" not in etf or etf.get("imposta_stimata") is not None:
        errori.append("ETF lot-aware automatico deve fare hard-stop")

    return errori


def test_registry_lotti_e_ribilanciamento():
    errori = []
    portfolio_path = None
    lotti_path = None
    try:
        portfolio = (
            "isin,nome,tipo,quantita,pmc,prezzo,asset_class,valuta_esposizione,valuta_quotazione,area,settore,broker,quota_stato\n"
            "US0378331005,Apple,azione,40,145,212,azionario,USD,USD,usa,tecnologia,BrokerA,0\n"
            "CASH-EUR,Liquidita,liquidita,1,1520,1520,liquidita,EUR,EUR,italia,cash,BrokerA,0\n"
        )
        lotti_txt = (
            "isin,broker,data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur\n"
            "US0378331005,BrokerA,2024-01-10,20,130,2\n"
            "US0378331005,BrokerA,2026-06-10,20,160,2\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(portfolio)
            portfolio_path = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(lotti_txt)
            lotti_path = f.name

        posizioni, _ = leggi(portfolio_path)
        idx = indicizza(carica_lotti_portafoglio(lotti_path))
        copertura = valida_copertura(posizioni, idx, TIPI_LOT_AWARE)
        if not copertura.get("azionabile"):
            errori.append("copertura lotti valida rifiutata: %r" % copertura.get("errori"))

        target = {"azionario": 0.5, "liquidita": 0.5}
        legacy = ribilancia(posizioni, target, regime="dichiarativo")
        lot_aware = ribilancia(posizioni, target, regime="dichiarativo", lotti_posizioni=idx)
        if lot_aware.get("base_fiscale_modalita") != "lotti_per_isin_broker":
            errori.append("ribilanciamento non segnala modalita lot-aware")
        det = lot_aware.get("strategie", [{}])[0].get("dettagli_vendite", [])
        if not det or det[0].get("metodo_base") != "lifo":
            errori.append("strategia A dichiarativa deve usare LIFO sulla vendita Apple")
        if not det or det[0].get("modalita_base") != "lot_aware":
            errori.append("dettaglio vendita deve indicare base lot-aware")
        if (lot_aware["strategie"][0]["imposta_stimata"] >=
                legacy["strategie"][0]["imposta_stimata"]):
            errori.append("con lotto recente a costo 160 la simulazione LIFO dovrebbe tassare meno del PMC 145")
        residui = lot_aware["strategie"][0].get("lotti_posizioni_dopo", [])
        apple = [x for x in residui if x.get("isin") == "US0378331005"]
        if not apple or not (0 < apple[0]["quantita"] < 40):
            errori.append("la strategia deve riportare la quantita Apple residua")

        # Un mismatch quantitativo deve bloccare la copertura.
        idx_bad = dict(idx)
        key = ("US0378331005", "BrokerA")
        idx_bad[key] = idx_bad[key][:-1]
        bad = valida_copertura(posizioni, idx_bad, TIPI_LOT_AWARE)
        if bad.get("azionabile"):
            errori.append("mismatch quantita portfolio/lotti deve essere bloccante")
    finally:
        for path in (portfolio_path, lotti_path):
            if path and os.path.exists(path):
                os.unlink(path)
    return errori


def test_validator_e_concentrazione():
    errori = []
    base = valida_portafoglio(os.path.join(BASE, "examples", "portafoglio-esempio.csv"))
    if not base.get("azionabile"):
        errori.append("portafoglio esempio dovrebbe essere strutturalmente valido: %r" % base.get("errori"))

    contenuto_dup = (
        "isin,nome,tipo,quantita,pmc,prezzo,asset_class,valuta_esposizione,broker,quota_stato\n"
        "US0378331005,Apple A,azione,10,100,120,azionario,USD,BrokerA,0\n"
        "US0378331005,Apple B,azione,5,105,120,azionario,USD,BrokerA,0\n"
    )
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(contenuto_dup)
            path = f.name
        dup = valida_portafoglio(path)
        if dup.get("azionabile"):
            errori.append("duplicato stesso ISIN/broker deve essere bloccante")
        if not any("falsare HHI" in x for x in dup.get("errori", [])):
            errori.append("duplicato deve spiegare l'impatto sulla concentrazione")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    contenuto_multi = (
        "isin,nome,tipo,quantita,pmc,prezzo,asset_class,valuta_esposizione,broker,quota_stato\n"
        "US0378331005,Apple A,azione,5,100,100,azionario,USD,BrokerA,0\n"
        "US0378331005,Apple B,azione,5,100,100,azionario,USD,BrokerB,0\n"
        "US5949181045,Microsoft,azione,10,50,50,azionario,USD,BrokerA,0\n"
    )
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(contenuto_multi)
            path = f.name
        check = valida_portafoglio(path)
        if not check.get("azionabile"):
            errori.append("stesso ISIN su broker diversi non deve essere bloccante")
        posizioni, lacune = leggi(path)
        out = analizza(posizioni, lacune)
        if not near(out.get("concentrazione", {}).get("hhi"), 0.5556, 0.0001):
            errori.append("HHI deve aggregare Apple per ISIN: ottenuto %r" % out.get("concentrazione", {}).get("hhi"))
        if out.get("strumenti_unici") != 2:
            errori.append("strumenti_unici atteso 2")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    return errori


def main():
    gruppi = (
        ("eventi", test_eventi),
        ("lotti", test_lotti),
        ("registry_lotti_ribilanciamento", test_registry_lotti_e_ribilanciamento),
        ("validator_concentrazione", test_validator_e_concentrazione),
    )
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
