#!/usr/bin/env python3
"""Calcoli deterministici e volutamente limitati sulla successione di titoli.

Implementa solo cio' che e' direttamente supportato dalle fonti citate:
- TUIR art. 68 c.6: costo fiscale per titoli/partecipazioni acquisiti per
  successione = valore definito o, in mancanza, dichiarato; per titoli esenti
  dall'imposta di successione = valore normale alla data di apertura;
- gli oneri inerenti, inclusa l'imposta di successione attribuibile al bene,
  aumentano il costo;
- D.Lgs. 346/1990 art. 12: alcuni titoli pubblici sono esclusi dall'attivo
  ereditario.

Non estende automaticamente queste regole a OICR/ETF, certificates o strumenti
ibridi: per tali strumenti restituisce un hard stop finche' non viene verificata
la disciplina specifica.
"""

import argparse
import json
import sys

TIPI_ART68_6 = {"azione", "obbligazione", "titolo_stato"}

FONTI = [
    "TUIR art. 68 c.6 (DPR 917/1986): costo in successione e oneri inerenti, "
    "Normattiva",
    "D.Lgs. 346/1990 art. 12: beni non compresi nell'attivo ereditario, "
    "Normattiva",
]


def r(x):
    return round(float(x), 2)


def costo_fiscale_successione(tipo, valore_dichiarato=None, valore_definito=None,
                              valore_normale=None, esente_successione=False,
                              imposta_successione_attribuita=0.0,
                              valore_corrente=None):
    tipo = str(tipo).strip().lower()
    if tipo not in TIPI_ART68_6:
        return {
            "errore": ("Tipo non coperto dal motore successione: %s. Verificare la "
                       "disciplina specifica prima di estendere per analogia." % tipo),
            "tipo": tipo,
            "calcolabile": False,
            "fonti": FONTI,
        }

    imposta = max(0.0, float(imposta_successione_attribuita or 0.0))
    if esente_successione:
        if valore_normale is None:
            return {
                "errore": "Per un titolo esente serve il valore normale alla data di apertura della successione.",
                "tipo": tipo,
                "calcolabile": False,
                "dato_mancante": "valore_normale",
                "fonti": FONTI,
            }
        base = float(valore_normale)
        criterio = "valore_normale_data_apertura"
    else:
        if valore_definito is not None:
            base = float(valore_definito)
            criterio = "valore_definito_imposta_successione"
        elif valore_dichiarato is not None:
            base = float(valore_dichiarato)
            criterio = "valore_dichiarato_imposta_successione"
        else:
            return {
                "errore": "Serve il valore definito o, in mancanza, dichiarato ai fini dell'imposta di successione.",
                "tipo": tipo,
                "calcolabile": False,
                "dato_mancante": "valore_successione",
                "fonti": FONTI,
            }

    costo = base + imposta
    out = {
        "tipo": tipo,
        "calcolabile": True,
        "esente_imposta_successione": bool(esente_successione),
        "criterio_costo": criterio,
        "costo_base": r(base),
        "imposta_successione_attribuita": r(imposta),
        "costo_fiscale_riconosciuto": r(costo),
        "fonti": FONTI,
        "verificare": [
            "L'eventuale imposta di successione attribuita al singolo bene deve essere documentabile.",
            "Non confondere esclusione dall'attivo ereditario con il trattamento fiscale della futura vendita.",
        ],
    }
    if valore_corrente is not None:
        valore_corrente = float(valore_corrente)
        out["valore_corrente"] = r(valore_corrente)
        out["differenza_vs_costo_fiscale"] = r(valore_corrente - costo)
    return out


def attivo_ereditario(esente_art12):
    """Non inferisce l'esenzione: riceve un fatto gia' verificato sul titolo."""
    return {
        "esente_art12_verificato": bool(esente_art12),
        "compreso_nell_attivo_ereditario": not bool(esente_art12),
        "fonte": "D.Lgs. 346/1990 art. 12",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("costo", help="calcola il costo fiscale riconosciuto all'erede")
    c.add_argument("--tipo", required=True)
    c.add_argument("--valore-dichiarato", type=float)
    c.add_argument("--valore-definito", type=float)
    c.add_argument("--valore-normale", type=float)
    c.add_argument("--esente-successione", action="store_true")
    c.add_argument("--imposta-successione-attribuita", type=float, default=0.0)
    c.add_argument("--valore-corrente", type=float)

    a = sub.add_parser("attivo", help="separa l'esenzione dall'attivo ereditario dal costo fiscale")
    a.add_argument("--esente-art12", action="store_true")

    args = p.parse_args(argv)
    if args.cmd == "attivo":
        out = attivo_ereditario(args.esente_art12)
    else:
        out = costo_fiscale_successione(
            args.tipo,
            args.valore_dichiarato,
            args.valore_definito,
            args.valore_normale,
            args.esente_successione,
            args.imposta_successione_attribuita,
            args.valore_corrente,
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out.get("errore") else 0


if __name__ == "__main__":
    sys.exit(main())
