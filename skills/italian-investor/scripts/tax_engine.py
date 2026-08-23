#!/usr/bin/env python3
"""Motore fiscale deterministico per strumenti finanziari, residente in Italia.

Non contiene giudizi: classifica lo strumento, applica l'aritmetica e dichiara
esplicitamente cosa resta da verificare. Nessuna dipendenza esterna.

    python scripts/tax_engine.py classifica --tipo etf
    python scripts/tax_engine.py vendita --tipo etf --pmc 90 --prezzo 120 \
        --quantita 100 --minus 2000
"""

import argparse
import json
import sys

# Aliquota e frazione imponibile agevolata: valori di riferimento, NON fonte.
# Vanno riverificati (references/regole-correnti.md) prima dell'uso.
ALIQUOTA_ORDINARIA = 0.26
FRAZIONE_IMPONIBILE_AGEVOLATA = 0.4808  # 26% * 0.4808 = 12,5% effettivo

CAPITALE = "reddito_di_capitale"
DIVERSO = "reddito_diverso"

# categoria_plus: natura del provento positivo
# categoria_minus: natura della differenza negativa
# agevolato: la componente beneficia dell'imposizione ridotta
CATEGORIE = {
    "etf": dict(categoria_plus=CAPITALE, categoria_minus=DIVERSO, agevolato=False,
                nota="OICR armonizzato: plus reddito di capitale, minus reddito diverso"),
    "oicr": dict(categoria_plus=CAPITALE, categoria_minus=DIVERSO, agevolato=False,
                 nota="Fondo comune / OICR armonizzato"),
    "azione": dict(categoria_plus=DIVERSO, categoria_minus=DIVERSO, agevolato=False,
                   nota="Partecipazione non qualificata"),
    "obbligazione": dict(categoria_plus=DIVERSO, categoria_minus=DIVERSO, agevolato=False,
                         nota="Obbligazione corporate: capital gain reddito diverso"),
    "titolo_stato": dict(categoria_plus=DIVERSO, categoria_minus=DIVERSO, agevolato=True,
                         nota="Titolo di Stato IT / White List / ente assimilato"),
    "etc_etn": dict(categoria_plus=DIVERSO, categoria_minus=DIVERSO, agevolato=False,
                    nota="ETC/ETN: non sono OICR"),
    "certificate": dict(categoria_plus=DIVERSO, categoria_minus=DIVERSO, agevolato=False,
                        nota="Certificate: reddito diverso"),
    "liquidita": dict(categoria_plus=CAPITALE, categoria_minus=None, agevolato=False,
                      nota="Interessi: reddito di capitale, nessuna minusvalenza"),
}

# Tipi per cui il motore NON calcola: il regime dipende da elementi da accertare.
DA_ACCERTARE = {
    "etf_non_armonizzato": "OICR non armonizzato: il regime puo differire e concorrere "
                           "al reddito complessivo. Verificare caso per caso.",
    "cripto": "Regime delle cripto-attivita modificato piu volte: verificare l'anno "
              "d'imposta prima di qualunque calcolo.",
    "fondo_pensione": "Previdenza complementare: regime autonomo, fuori dallo schema "
                      "redditi di capitale / redditi diversi.",
    "pir": "PIR: possibile esenzione subordinata a requisiti di durata e composizione.",
}

FONTI_DA_CITARE = [
    "TUIR art. 44 (redditi di capitale) - DPR 917/1986, Normattiva: "
    "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:"
    "decreto.del.presidente.della.repubblica:1986-12-22;917",
    "TUIR art. 67-68 (redditi diversi, minusvalenze) - DPR 917/1986, Normattiva",
    "Istruzioni ai modelli dichiarativi / prassi Agenzia delle Entrate: "
    "https://www.agenziaentrate.gov.it/portale/",
    "Vigenza: dal 01/01/2027 si applica il nuovo testo unico D.Lgs. 117/2026 e la "
    "numerazione degli articoli cambia. Verificare il periodo d'imposta del caso.",
]


def classifica(tipo):
    tipo = tipo.lower().strip()
    if tipo in DA_ACCERTARE:
        return {
            "tipo": tipo,
            "calcolabile": False,
            "motivo": DA_ACCERTARE[tipo],
            "verificare": [DA_ACCERTARE[tipo]],
            "fonti": FONTI_DA_CITARE,
        }
    if tipo not in CATEGORIE:
        return {
            "tipo": tipo,
            "calcolabile": False,
            "motivo": "Tipo non riconosciuto. Risalire da ISIN alla natura giuridica "
                      "prima di procedere.",
            "tipi_noti": sorted(CATEGORIE) + sorted(DA_ACCERTARE),
            "verificare": ["Natura giuridica dello strumento non determinata"],
            "fonti": FONTI_DA_CITARE,
        }
    c = CATEGORIE[tipo]
    return {
        "tipo": tipo,
        "calcolabile": True,
        "categoria_plusvalenza": c["categoria_plus"],
        "categoria_minusvalenza": c["categoria_minus"],
        "plus_compensabile_con_zainetto": c["categoria_plus"] == DIVERSO,
        "minus_alimenta_zainetto": c["categoria_minus"] == DIVERSO,
        "componente_agevolata": c["agevolato"],
        "nota": c["nota"],
        "fonti": FONTI_DA_CITARE,
    }


def simula_vendita(tipo, pmc, prezzo, quantita, minus_disponibili=0.0,
                   quota_stato=0.0, costi=0.0):
    """Simula la vendita di una posizione. Importi in euro, quota_stato in 0..1."""
    info = classifica(tipo)
    if not info["calcolabile"]:
        return {"errore": info["motivo"], "verificare": info["verificare"],
                "fonti": info["fonti"], "imposta_stimata": None}

    verificare = []
    costi = max(0.0, float(costi))
    controvalore = prezzo * quantita
    costo = pmc * quantita
    risultato = controvalore - costo - costi

    out = {
        "tipo": tipo,
        "controvalore": r(controvalore),
        "costo_carico": r(costo),
        "risultato_lordo": r(risultato),
        "categoria_reddito": (info["categoria_plusvalenza"] if risultato > 0
                              else info["categoria_minusvalenza"]),
        "verificare": verificare,
        "fonti": info["fonti"],
    }

    if risultato <= 0:
        minus_generate = -risultato if info["minus_alimenta_zainetto"] else 0.0
        out.update({
            "imposta_stimata": 0.0,
            "minusvalenza_generata": r(minus_generate),
            "zainetto_dopo": r(minus_disponibili + minus_generate),
        })
        if not info["minus_alimenta_zainetto"]:
            verificare.append("La differenza negativa su questo strumento potrebbe non "
                              "essere deducibile: verificare.")
        verificare.append("Minusvalenze utilizzabili entro il 4o anno successivo a quello "
                          "di realizzo: verificare il termine vigente.")
        return out

    compensabile = info["plus_compensabile_con_zainetto"]
    minus_usate = min(max(0.0, minus_disponibili), risultato) if compensabile else 0.0
    imponibile = risultato - minus_usate

    if info["componente_agevolata"]:
        quota_agev = 1.0
    else:
        quota_agev = clamp01(quota_stato)
        if tipo in ("etf", "oicr") and quota_agev == 0.0:
            verificare.append("Quota di titoli di Stato/White List del fondo non fornita: "
                              "calcolo eseguito a 0% agevolato. Recuperare la percentuale "
                              "comunicata dall'emittente o dall'intermediario.")
        elif quota_agev > 0.0:
            verificare.append("Quota agevolata assunta pari a %.2f%%: confermarla sulla "
                              "comunicazione dell'emittente/intermediario."
                              % (quota_agev * 100))

    base_agevolata = imponibile * quota_agev
    base_ordinaria = imponibile - base_agevolata
    imposta = (base_ordinaria * ALIQUOTA_ORDINARIA
               + base_agevolata * FRAZIONE_IMPONIBILE_AGEVOLATA * ALIQUOTA_ORDINARIA)

    if not compensabile and minus_disponibili > 0:
        verificare.append("Plusvalenza qualificata come reddito di capitale: NON abbattuta "
                          "dalle minusvalenze in zainetto. Verificare la qualificazione "
                          "dello strumento prima di considerare definitivo il risultato.")
    if minus_usate > 0:
        verificare.append("Compensazione applicata sull'intero risultato prima "
                          "dell'eventuale riduzione della base imponibile: verificare "
                          "l'ordine applicato dall'intermediario.")
    verificare.append("Aliquota e frazione imponibile sono valori di riferimento non "
                      "verificati (references/regole-correnti.md).")

    out.update({
        "minusvalenze_disponibili": r(minus_disponibili),
        "minusvalenze_utilizzate": r(minus_usate),
        "zainetto_residuo": r(max(0.0, minus_disponibili) - minus_usate),
        "imponibile": r(imponibile),
        "quota_agevolata_applicata": quota_agev,
        "imposta_stimata": r(imposta),
        "netto_incassato": r(controvalore - imposta - costi),
        "aliquota_effettiva_su_risultato": r(imposta / risultato),
    })
    return out


def clamp01(x):
    return max(0.0, min(1.0, float(x)))


def r(x):
    return round(float(x), 2)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classifica", help="natura fiscale di un tipo di strumento")
    c.add_argument("--tipo", required=True)

    v = sub.add_parser("vendita", help="simula la vendita di una posizione")
    v.add_argument("--tipo", required=True)
    v.add_argument("--pmc", type=float, required=True, help="prezzo medio di carico")
    v.add_argument("--prezzo", type=float, required=True, help="prezzo di vendita")
    v.add_argument("--quantita", type=float, required=True)
    v.add_argument("--minus", type=float, default=0.0, help="minusvalenze in zainetto")
    v.add_argument("--quota-stato", type=float, default=0.0,
                   help="quota agevolata del fondo, da 0 a 1")
    v.add_argument("--costi", type=float, default=0.0, help="commissioni di negoziazione")

    a = p.parse_args(argv)
    if a.cmd == "classifica":
        res = classifica(a.tipo)
    else:
        res = simula_vendita(a.tipo, a.pmc, a.prezzo, a.quantita,
                             a.minus, a.quota_stato, a.costi)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 1 if "errore" in res else 0


if __name__ == "__main__":
    sys.exit(main())
