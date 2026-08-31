#!/usr/bin/env python3
"""Motore deterministico per proventi periodici e altri flussi finanziari.

Separa gli eventi fiscali dalla vendita: una stessa obbligazione, per esempio,
puo' generare un reddito di capitale con la cedola e un reddito diverso con il
capital gain da cessione.

Il modulo copre solo casi semplici e verificabili. Se esistono ritenute estere,
strumenti ibridi o qualificazioni dipendenti dal prospetto restituisce hard-stop.

Esempi:

    python scripts/event_tax.py classifica --tipo obbligazione --evento cedola
    python scripts/event_tax.py provento --tipo azione --evento dividendo --lordo 100
    python scripts/event_tax.py provento --tipo etf --evento distribuzione \
        --lordo 100 --quota-stato 0.30
"""

import argparse
import json
import sys

ALIQUOTA_ORDINARIA = 0.26
FRAZIONE_IMPONIBILE_AGEVOLATA = 0.4808
ALIQUOTA_TITOLI_PUBBLICI = 0.125

CAPITALE = "reddito_di_capitale"
DIVERSO = "reddito_diverso"

# Regole relative all'EVENTO, non alla natura complessiva dello strumento.
EVENTI = {
    ("azione", "dividendo"): {
        "categoria": CAPITALE,
        "aliquota": "ordinaria",
        "nota": "Dividendo percepito da persona fisica residente fuori dall'impresa.",
    },
    ("obbligazione", "cedola"): {
        "categoria": CAPITALE,
        "aliquota": "ordinaria",
        "nota": "Interessi/premi/altri proventi di obbligazione corporate.",
    },
    ("obbligazione", "interesse"): {
        "categoria": CAPITALE,
        "aliquota": "ordinaria",
        "nota": "Interessi/premi/altri proventi di obbligazione corporate.",
    },
    ("titolo_stato", "cedola"): {
        "categoria": CAPITALE,
        "aliquota": "titolo_pubblico",
        "nota": "Provento di titolo pubblico agevolato; verificare l'ammissibilita' del titolo.",
    },
    ("titolo_stato", "interesse"): {
        "categoria": CAPITALE,
        "aliquota": "titolo_pubblico",
        "nota": "Provento di titolo pubblico agevolato; verificare l'ammissibilita' del titolo.",
    },
    ("etf", "distribuzione"): {
        "categoria": CAPITALE,
        "aliquota": "oicr_mista",
        "nota": "Provento distribuito da OICR/ETF; la quota titoli pubblici puo' ridurre l'aliquota effettiva.",
    },
    ("oicr", "distribuzione"): {
        "categoria": CAPITALE,
        "aliquota": "oicr_mista",
        "nota": "Provento distribuito da OICR; la quota titoli pubblici puo' ridurre l'aliquota effettiva.",
    },
    ("liquidita", "interesse"): {
        "categoria": CAPITALE,
        "aliquota": "ordinaria",
        "nota": "Interesse su liquidita/deposito nel caso ordinario coperto.",
    },
}

DA_ACCERTARE = {
    "certificate": "Il trattamento del flusso periodico di un certificate dipende dalla struttura del prodotto: verificare prospetto/term sheet.",
    "etc_etn": "ETC/ETN: qualificazione fiscale da verificare sul prospetto specifico.",
    "etf_non_armonizzato": "OICR non armonizzato: il regime puo' differire; verificare caso per caso.",
    "cripto": "Cripto-attivita': regime autonomo e variabile nel tempo, fuori da questo helper.",
    "pir": "PIR: eventuale esenzione dipende dai requisiti del piano e non viene calcolata qui.",
    "fondo_pensione": "Previdenza complementare: regime autonomo, fuori da questo helper.",
}

FONTI = [
    "DL 66/2014 art. 3: aliquota ordinaria del 26% per interessi, premi, altri proventi ex art. 44 TUIR e redditi diversi finanziari, con eccezioni per titoli pubblici agevolati.",
    "DPR 600/1973 art. 27: ritenuta del 26% sui dividendi corrisposti a persone fisiche residenti fuori dall'impresa.",
    "DPR 600/1973 art. 26-quinquies / disciplina OICR: proventi da partecipazione a OICR come redditi di capitale; verificare testo vigente e prodotto.",
    "Agenzia delle Entrate, Circolare 19/E del 27/06/2014: componente di OICR riferibile a titoli pubblici agevolati.",
]


def _quota_valida(quota_stato):
    if quota_stato is None:
        return None
    try:
        q = float(quota_stato)
    except (TypeError, ValueError):
        raise ValueError("quota_stato deve essere un numero tra 0 e 1")
    if not 0.0 <= q <= 1.0:
        raise ValueError("quota_stato deve essere compresa tra 0 e 1")
    return q


def classifica_evento(tipo, evento):
    tipo = str(tipo).strip().lower()
    evento = str(evento).strip().lower()
    if tipo in DA_ACCERTARE:
        return {
            "tipo": tipo,
            "evento": evento,
            "calcolabile": False,
            "motivo": DA_ACCERTARE[tipo],
            "fonti": FONTI,
        }
    regola = EVENTI.get((tipo, evento))
    if not regola:
        return {
            "tipo": tipo,
            "evento": evento,
            "calcolabile": False,
            "motivo": (
                "Combinazione tipo/evento non coperta. Non dedurre la categoria fiscale "
                "dalla sola natura dello strumento."
            ),
            "eventi_coperti": ["%s:%s" % k for k in sorted(EVENTI)],
            "fonti": FONTI,
        }
    return {
        "tipo": tipo,
        "evento": evento,
        "calcolabile": True,
        "categoria_reddito": regola["categoria"],
        "compensabile_con_minus": regola["categoria"] == DIVERSO,
        "schema_aliquota": regola["aliquota"],
        "nota": regola["nota"],
        "fonti": FONTI,
    }


def simula_provento(tipo, evento, lordo, quota_stato=None,
                    ritenuta_estera=0.0, paese_fonte=None):
    info = classifica_evento(tipo, evento)
    if not info["calcolabile"]:
        return {
            "errore": info["motivo"],
            "tipo": tipo,
            "evento": evento,
            "imposta_stimata": None,
            "fonti": info["fonti"],
        }

    try:
        lordo = float(lordo)
        ritenuta_estera = float(ritenuta_estera or 0.0)
        quota_stato = _quota_valida(quota_stato)
    except ValueError as exc:
        return {"errore": str(exc), "imposta_stimata": None, "fonti": info["fonti"]}

    if lordo < 0 or ritenuta_estera < 0:
        return {
            "errore": "lordo e ritenuta_estera non possono essere negativi",
            "imposta_stimata": None,
            "fonti": info["fonti"],
        }

    # La doppia imposizione internazionale non viene compressa in una formula
    # generica: paese, convenzione, aliquota convenzionale e modalita' di incasso
    # possono cambiare il risultato.
    if ritenuta_estera > 0:
        return {
            "tipo": tipo,
            "evento": evento,
            "categoria_reddito": info["categoria_reddito"],
            "lordo": round(lordo, 2),
            "ritenuta_estera": round(ritenuta_estera, 2),
            "paese_fonte": paese_fonte,
            "imposta_stimata": None,
            "dato_mancante": "trattamento_doppia_imposizione_estera",
            "verificare": [
                "Verificare Paese fonte, convenzione, aliquota convenzionale, eventuale credito d'imposta e modalita' di incasso.",
            ],
            "fonti": info["fonti"],
        }

    schema = info["schema_aliquota"]
    verificare = []
    scenario = None

    if schema == "ordinaria":
        imposta = lordo * ALIQUOTA_ORDINARIA
        aliquota_effettiva = ALIQUOTA_ORDINARIA
    elif schema == "titolo_pubblico":
        imposta = lordo * ALIQUOTA_TITOLI_PUBBLICI
        aliquota_effettiva = ALIQUOTA_TITOLI_PUBBLICI
        verificare.append(
            "Confermare che il titolo rientri tra i titoli pubblici/White List agevolati."
        )
    elif schema == "oicr_mista":
        if quota_stato is None:
            imposta_max = lordo * ALIQUOTA_ORDINARIA
            imposta_min = lordo * ALIQUOTA_ORDINARIA * FRAZIONE_IMPONIBILE_AGEVOLATA
            scenario = {
                "quota_agevolata_0": round(imposta_max, 2),
                "quota_agevolata_100": round(imposta_min, 2),
            }
            return {
                "tipo": tipo,
                "evento": evento,
                "categoria_reddito": info["categoria_reddito"],
                "lordo": round(lordo, 2),
                "quota_stato": None,
                "imposta_stimata": None,
                "imposta_scenario": scenario,
                "netto_stimato": None,
                "dato_mancante": "quota_stato",
                "compensabile_con_minus": False,
                "verificare": [
                    "Recuperare la quota fiscalmente agevolata comunicata/applicabile al fondo; non usare le holdings correnti come sostituto automatico."
                ],
                "fonti": info["fonti"],
            }
        base_factor = (1.0 - quota_stato) + quota_stato * FRAZIONE_IMPONIBILE_AGEVOLATA
        imposta = lordo * ALIQUOTA_ORDINARIA * base_factor
        aliquota_effettiva = imposta / lordo if lordo else 0.0
        verificare.append(
            "Confermare la quota agevolata sulla comunicazione dell'emittente/intermediario."
        )
    else:
        return {"errore": "schema aliquota non gestito", "imposta_stimata": None}

    return {
        "tipo": tipo,
        "evento": evento,
        "categoria_reddito": info["categoria_reddito"],
        "lordo": round(lordo, 2),
        "quota_stato": quota_stato,
        "imposta_stimata": round(imposta, 2),
        "netto_stimato": round(lordo - imposta, 2),
        "aliquota_effettiva": round(aliquota_effettiva, 6),
        "compensabile_con_minus": False,
        "verificare": verificare,
        "fonti": info["fonti"],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classifica", help="classifica uno specifico evento fiscale")
    c.add_argument("--tipo", required=True)
    c.add_argument("--evento", required=True)

    f = sub.add_parser("provento", help="simula un provento periodico semplice")
    f.add_argument("--tipo", required=True)
    f.add_argument("--evento", required=True)
    f.add_argument("--lordo", required=True, type=float)
    f.add_argument("--quota-stato", type=float)
    f.add_argument("--ritenuta-estera", type=float, default=0.0)
    f.add_argument("--paese-fonte")

    args = p.parse_args(argv)
    if args.cmd == "classifica":
        out = classifica_evento(args.tipo, args.evento)
    else:
        out = simula_provento(
            args.tipo, args.evento, args.lordo,
            args.quota_stato, args.ritenuta_estera, args.paese_fonte,
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
