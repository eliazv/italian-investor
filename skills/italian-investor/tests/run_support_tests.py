#!/usr/bin/env python3
"""Test per zainetto, resolver ISIN, base fiscale e successione."""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from cost_basis import base_cmp, base_lifo, normalizza_lotto as normalizza_lotto_costo  # noqa: E402
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

    fresco = risolvi(
        "US0378331005", "azione", reg,
        data_riferimento="2026-08-31", max_age_giorni=30,
    )
    assert_eq("registry fresco azionabile", fresco["calcolo_fiscale_azionabile"], True, errori)
    assert_eq("eta registry", fresco["freschezza"]["eta_giorni"], 7, errori)
    assert_eq("registry non scaduto", fresco["freschezza"]["scaduta"], False, errori)

    stale = risolvi(
        "US0378331005", "azione", reg,
        data_riferimento="2026-08-31", max_age_giorni=5,
    )
    assert_eq("registry stale bloccato", stale["calcolo_fiscale_azionabile"], False, errori)
    assert_eq("registry stale flag", stale["freschezza"]["scaduta"], True, errori)

    data_errata = {
        "US0378331005": {
            "isin": "US0378331005",
            "tipo": "azione",
            "fonte": "fixture",
            "verificato_il": "31/08/2026",
        }
    }
    bad = risolvi("US0378331005", "azione", data_errata)
    assert_eq("data registry non ISO bloccata", bad["calcolo_fiscale_azionabile"], False, errori)
    return errori


def test_base_fiscale():
    errori = []
    raw = [
        {"data_acquisto": "2024-01-15", "quantita": 50, "costo_unitario_eur": 80, "costi_acquisto_eur": 5},
        {"data_acquisto": "2025-03-10", "quantita": 30, "costo_unitario_eur": 95, "costi_acquisto_eur": 3},
        {"data_acquisto": "2026-06-20", "quantita": 20, "costo_unitario_eur": 110, "costi_acquisto_eur": 2},
    ]
    lotti = [normalizza_lotto_costo(x, i) for i, x in enumerate(raw)]

    cmp_res = base_cmp(lotti, 25)
    assert_eq("CMP unitario", cmp_res["costo_medio_ponderato_unitario_eur"], 90.60, errori)
    assert_eq("CMP base vendita", cmp_res["base_costo_vendita_eur"], 2265.00, errori)
    assert_eq("CMP non sceglie la norma", cmp_res["regola_fiscale_verificata"], False, errori)

    lifo_res = base_lifo(lotti, 25)
    assert_eq("LIFO base vendita", lifo_res["base_costo_vendita_eur"], 2677.50, errori)
    assert_eq("LIFO primo lotto recente", lifo_res["lotti_utilizzati"][0]["data_acquisto"], "2026-06-20", errori)
    assert_eq("LIFO secondo lotto", lifo_res["lotti_utilizzati"][1]["quantita_utilizzata"], 5, errori)

    ambigui = [
        normalizza_lotto_costo({"data_acquisto": "2026-01-10", "quantita": 5, "costo_unitario_eur": 90}, 0),
        normalizza_lotto_costo({"data_acquisto": "2026-01-10", "quantita": 5, "costo_unitario_eur": 100}, 1),
    ]
    stop = base_lifo(ambigui, 3)
    assert_eq("LIFO stessa data hard stop", stop.get("errore"), "AMBIGUITA_STESSA_DATA", errori)
    assert_eq("LIFO non inventa base", stop.get("base_costo_vendita_eur"), None, errori)
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
    for nome, fn in (
        ("zainetto", test_zainetto),
        ("resolver", test_resolver),
        ("base_fiscale", test_base_fiscale),
    ):
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
