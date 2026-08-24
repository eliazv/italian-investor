#!/usr/bin/env python3
"""Test per zainetto strutturato, resolver ISIN e successione."""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from instrument_resolver import risolvi, valida_isin  # noqa: E402
from successione import costo_fiscale_successione  # noqa: E402
from zainetto import disponibile, consuma, normalizza_lotto  # noqa: E402


def assert_eq(nome, ottenuto, atteso, errori):
    if isinstance(atteso, (int, float)) and not isinstance(atteso, bool):
        if ottenuto is None or abs(float(ottenuto) - float(atteso)) > 0.01:
            errori.append("%s: atteso %r, ottenuto %r" % (nome, atteso, ottenuto))
    elif ottenuto != atteso:
        errori.append("%s: atteso %r, ottenuto %r" % (nome, atteso, ottenuto))


def test_zainetto():
    errori = []
    lotti = [
        normalizza_lotto({"broker": "BrokerA", "regime": "amministrato", "anno_realizzo": 2022, "importo": 500}),
        normalizza_lotto({"broker": "BrokerA", "regime": "amministrato", "anno_realizzo": 2023, "importo": 800}),
        normalizza_lotto({"broker": "BrokerB", "regime": "amministrato", "anno_realizzo": 2022, "importo": 900}),
        normalizza_lotto({"broker": "BrokerEstero", "regime": "dichiarativo", "anno_realizzo": 2024, "importo": 600}),
    ]
    assert_eq("BrokerA disponibile 2026", disponibile(lotti, "BrokerA", 2026), 1300, errori)
    assert_eq("BrokerB isolato", disponibile(lotti, "BrokerB", 2026), 900, errori)
    assert_eq("BrokerA 2027 perde lotto 2022", disponibile(lotti, "BrokerA", 2027), 800, errori)
    assert_eq("Dichiarativo aggregabile", disponibile(lotti, "qualsiasi", 2026, "dichiarativo"), 600, errori)
    res = consuma(lotti, 700, "BrokerA", 2026)
    assert_eq("consumo totale", res["utilizzato"], 700, errori)
    assert_eq("primo lotto consumato", res["utilizzi"][0]["anno_realizzo"], 2022, errori)
    assert_eq("secondo lotto usato", res["utilizzi"][1]["utilizzato"], 200, errori)
    return errori


def test_resolver():
    errori = []
    assert_eq("Apple ISIN valido", valida_isin("US0378331005"), True, errori)
    assert_eq("ISIN errato", valida_isin("US0378331004"), False, errori)
    reg = {
        "US0378331005": {
            "isin": "US0378331005",
            "tipo": "azione",
            "fonte": "fixture KID/prospetto",
            "verificato_il": "2026-08-24",
        }
    }
    ok = risolvi("US0378331005", "azione", reg)
    assert_eq("resolver azionabile", ok["calcolo_fiscale_azionabile"], True, errori)
    mismatch = risolvi("US0378331005", "etf", reg)
    assert_eq("mismatch bloccato", mismatch["calcolo_fiscale_azionabile"], False, errori)
    unknown = risolvi("IE00BK5BQT80", "etf", reg)
    assert_eq("unknown non azionabile", unknown["calcolo_fiscale_azionabile"], False, errori)
    return errori


def test_successione():
    with open(os.path.join(BASE, "tests", "casi_successione.json"), encoding="utf-8") as f:
        casi = json.load(f)
    errori_tot = []
    for caso in casi:
        errori = []
        if caso.get("tipo_caso", "normativo") == "normativo":
            for campo in ("fonte", "articolo", "verificato_il"):
                if not caso.get(campo):
                    errori.append("metadato normativo mancante: %s" % campo)
        res = costo_fiscale_successione(**caso["input"])
        for chiave, atteso in caso["atteso"].items():
            if chiave == "errore_atteso":
                if atteso and "errore" not in res:
                    errori.append("atteso hard stop")
                continue
            assert_eq(chiave, res.get(chiave), atteso, errori)
        if errori:
            errori_tot.append((caso["nome"], errori))
    return errori_tot


def main():
    falliti = 0
    for nome, fn in (("zainetto", test_zainetto), ("resolver", test_resolver)):
        errori = fn()
        if errori:
            falliti += 1
            print("FAIL  %s" % nome)
            for e in errori:
                print("      %s" % e)
        else:
            print("ok    %s" % nome)

    succ = test_successione()
    if succ:
        falliti += len(succ)
        for nome, errori in succ:
            print("FAIL  successione: %s" % nome)
            for e in errori:
                print("      %s" % e)
    else:
        print("ok    successione (%d casi)" % len(json.load(open(os.path.join(BASE, "tests", "casi_successione.json"), encoding="utf-8"))))

    print("\n%d gruppi/casi falliti" % falliti)
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
