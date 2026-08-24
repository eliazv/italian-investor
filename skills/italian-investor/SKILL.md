---
name: italian-investor
description: Analisi di portafoglio tax-aware per residenti fiscali italiani. Da usare quando si analizza un portafoglio (ETF, azioni, BTP, obbligazioni, certificates), si simula una vendita o un ribilanciamento, si ragiona su minusvalenze/zainetto fiscale, successione o imposte su strumenti finanziari italiani. Impone verifica su fonti primarie invece che memoria del modello.
---

# Italian Investor

Analisi di portafoglio per un residente fiscale italiano, con la fiscalità
trattata come **dato da verificare**, non come conoscenza del modello.

Questa skill non contiene "la risposta fiscale". Contiene la **procedura** per
arrivarci senza allucinare, più un motore deterministico in Python per i calcoli.

## Regola zero

Non usare mai la memoria interna del modello per:

- aliquote vigenti;
- trattamento fiscale di uno strumento;
- compensabilità di minusvalenze;
- imposta di successione e costo fiscale dell'erede;
- caratteristiche di un prodotto (TER, duration, holdings, valuta, ISIN).

Se non trovi una fonte autorevole: **non dedurre la regola**. Scrivi
`NON VERIFICATO` e blocca la conclusione che ne dipende.

Non inventare mai: ISIN, TER, rendimento, duration, rating, composizione del
fondo, quota di titoli di Stato, esposizione valutaria. Se il dato manca, va
chiesto all'utente o recuperato dal KID/prospetto.

## Procedura

1. **Profilo.** Verifica residenza fiscale, regime (amministrato / dichiarativo
   / gestito), broker, orizzonte, target di allocazione, minusvalenze in
   zainetto con anno di scadenza. Se il regime non è noto, chiedilo: cambia
   completamente chi calcola e versa l'imposta.
2. **Strumenti.** Per ogni riga risali a `ISIN → natura giuridica → categoria
   fiscale`. Mai dedurre il trattamento dal nome commerciale. Un "ETF
   obbligazionario governativo" non è automaticamente al 12,5%: serve la quota
   agevolata comunicata dall'emittente/intermediario.
3. **Calcoli.** Esegui i numeri con `scripts/`, non a mente. Vedi
   [scripts/portfolio.py](scripts/portfolio.py) e
   [scripts/tax_engine.py](scripts/tax_engine.py).
4. **Norma.** Per ogni conclusione fiscale rilevante recupera una fonte
   corrente secondo [references/fonti.md](references/fonti.md) e cita
   articolo/circolare con la data.
5. **Separazione.** Distingui sempre `dato → legge → calcolo → opinione`.
6. **Claim audit.** Chiudi ogni analisi con la tabella di audit (sotto).
7. **Revisione avversariale.** Prima di consegnare, rileggi le tue
   raccomandazioni cercando attivamente almeno cinque motivi per cui potrebbero
   essere sbagliate: fiscalità, esposizione valutaria, concentrazione,
   assunzioni sui rendimenti, costi di transazione.
8. **Stop.** Se manca un dato che cambierebbe la conclusione (regime, PMC,
   quota agevolata, scadenza delle minus), fermati e chiedilo. Non stimarlo.

## Riferimenti

- [references/fonti.md](references/fonti.md) — gerarchia delle fonti e quando
  una claim va verificata.
- [references/fiscalita.md](references/fiscalita.md) — come ragionare su
  redditi di capitale vs redditi diversi, zainetto, successione.
- [references/regole-correnti.md](references/regole-correnti.md) — i numeri che
  cambiano nel tempo, con data di ultima verifica. **Ricontrollali** prima di
  usarli.

## Script

Tutti gli script sono stdlib-only, senza dipendenze, e stampano JSON.

```bash
python scripts/portfolio.py analizza portafoglio.csv
python scripts/portfolio.py ribilancia portafoglio.csv --target azionario=70,obbligazionario=25,liquidita=5
python scripts/tax_engine.py vendita --tipo etf --pmc 90 --prezzo 120 --quantita 100 --minus 2000
python scripts/tax_engine.py classifica --tipo btp
python tests/run_tests.py
```

Formato del CSV atteso: vedi
[examples/portafoglio-esempio.csv](examples/portafoglio-esempio.csv).

Gli script restituiscono, oltre ai numeri, i campi `verificare` e `fonti`:
riportali nell'output finale, non scartarli.

Quando un dato necessario manca, il motore **non produce un importo singolo**:
restituisce `imposta_stimata: null`, il campo `dato_mancante` e un
`imposta_scenario` con i due estremi. In quel caso riporta l'intervallo e chiedi
il dato: non scegliere un estremo e non presentarlo come stima.

## Claim audit (obbligatoria)

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

Una riga per ogni affermazione che influenza una decisione. Se una riga ha
confidenza Bassa o fonte assente, la raccomandazione collegata va marcata come
non azionabile.

## Limiti

Questa skill produce **analisi e simulazioni**, non consulenza finanziaria né
fiscale. Non suggerire operazioni motivate solo dal recupero di minusvalenze.
Le imposte effettive le calcola e le versa l'intermediario in regime
amministrato: i numeri qui sono stime da confrontare con il rendiconto fiscale.

## Convenzioni del CSV

Obbligazioni: `quantita` = valore nominale, `pmc` e `prezzo` in frazione
(corso 101,30 → `1.0130`). `valuta_esposizione` è la valuta dei sottostanti,
non quella di quotazione. `quota_stato` (0–1) è la quota agevolata comunicata
dall'emittente: se manca, il calcolo gira a 0% e lo dichiara.
