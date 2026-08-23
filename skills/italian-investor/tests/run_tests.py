#!/usr/bin/env python3
"""Test di regressione sulle regole fiscali implementate in scripts/tax_engine.py.

I casi stanno in tests/casi_fiscali.json. Ogni modifica al motore deve passarli.
Se una verifica normativa dimostra che un caso atteso e' sbagliato, si corregge
prima il caso (citando la fonte nel campo "perche"), poi il motore.

    python tests/run_tests.py
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from tax_engine import simula_vendita  # noqa: E402


def esegui(caso):
    i = caso["input"]
    res = simula_vendita(i["tipo"], i["pmc"], i["prezzo"], i["quantita"],
                         i.get("minus_disponibili", 0.0),
                         i.get("quota_stato", 0.0),
                         i.get("costi", 0.0))
    errori = []
    for chiave, atteso in caso["atteso"].items():
        if chiave == "errore_atteso":
            if atteso and "errore" not in res:
                errori.append("atteso un rifiuto di calcolo, il motore ha risposto")
            continue
        if chiave == "verificare_contiene":
            if not any(atteso in v for v in res.get("verificare", [])):
                errori.append("avviso mancante: %r" % atteso)
            continue
        ottenuto = res.get(chiave)
        if atteso is None:
            if ottenuto is not None:
                errori.append("%s: atteso null, ottenuto %r" % (chiave, ottenuto))
        elif isinstance(atteso, (int, float)):
            if ottenuto is None or abs(float(ottenuto) - float(atteso)) > 0.01:
                errori.append("%s: atteso %s, ottenuto %s" % (chiave, atteso, ottenuto))
        elif ottenuto != atteso:
            errori.append("%s: atteso %r, ottenuto %r" % (chiave, atteso, ottenuto))
    return errori


def main():
    with open(os.path.join(BASE, "tests", "casi_fiscali.json"), encoding="utf-8") as f:
        casi = json.load(f)

    falliti = 0
    for caso in casi:
        errori = esegui(caso)
        if errori:
            falliti += 1
            print("FAIL  %s" % caso["nome"])
            for e in errori:
                print("      %s" % e)
        else:
            print("ok    %s" % caso["nome"])

    print("\n%d casi, %d falliti" % (len(casi), falliti))
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
