---
name: italian-investor
description: Analisi di portafoglio tax-aware per residenti fiscali italiani. Da usare quando si analizza un portafoglio (ETF, azioni, BTP, obbligazioni, certificates), si simula una vendita o un ribilanciamento, si ragiona su minusvalenze/zainetto fiscale, successione o imposte su strumenti finanziari italiani. Impone verifica su fonti primarie invece che memoria del modello.
---

# Italian Investor

Analisi di portafoglio per un residente fiscale italiano, con la fiscalità
trattata come **dato da verificare**, non come conoscenza del modello.

La skill contiene una procedura anti-allucinazione e piccoli motori Python
deterministici. Il modello interpreta e spiega; non deve inventare norme,
classificazioni di strumenti o aritmetica fiscale.

## Regola zero

Non usare mai la memoria interna del modello per:

- aliquote vigenti e basi imponibili;
- trattamento fiscale di uno strumento;
- compensabilità e scadenza delle minusvalenze;
- imposta di successione e costo fiscale dell'erede;
- caratteristiche di prodotto (TER, duration, holdings, valuta, ISIN,
  percentuale di titoli pubblici agevolati).

Se non trovi una fonte autorevole: **non dedurre la regola**. Scrivi
`NON VERIFICATO` e blocca la conclusione che ne dipende.

## Procedura

1. **Profilo.** Verifica residenza fiscale, regime (amministrato / dichiarativo
   / gestito), broker, orizzonte, target e minusvalenze con anno di realizzo.
2. **Strumenti.** Parti sempre da `ISIN → natura giuridica → categoria fiscale`.
   Il campo `tipo` del CSV è una dichiarazione dell'utente, non una prova. Usa
   `scripts/instrument_resolver.py` o il registry ISIN verificato. Non dedurre
   il tipo dal prefisso ISIN o dal nome commerciale. Per ETC/ETN consulta la
   sezione `Taxation in Italy` del prospetto specifico.
3. **Zainetto.** Preferisci il CSV strutturato a un saldo unico. Ogni lotto deve
   avere `broker, regime, anno_realizzo, importo`. In amministrato una vendita
   usa solo le minus disponibili presso lo stesso intermediario e non scadute;
   in dichiarativo il simulatore può aggregare i lotti marcati dichiarativo.
4. **Calcoli.** Esegui i numeri con gli script, non a mente. Per il portfolio usa
   `portfolio.py`; per una vendita `tax_engine.py`; per lo zainetto
   `zainetto.py`; per successione `successione.py`.
5. **Norma.** Per ogni conclusione fiscale rilevante recupera una fonte
   corrente secondo [references/fonti.md](references/fonti.md), verificane la
   vigenza alla data rilevante e cita norma/articolo/circolare.
6. **Separazione.** Distingui sempre `dato → legge → calcolo → opinione`.
7. **Claim audit.** Chiudi ogni analisi con la tabella di audit.
8. **Revisione avversariale.** Cerca attivamente errori su fiscalità,
   classificazione strumento, valuta, concentrazione, assunzioni sui rendimenti,
   costi e ordine delle operazioni.
9. **Stop.** Se manca un dato che può cambiare la conclusione (regime, broker,
   PMC, quota agevolata, scadenza minus, KID/prospetto), fermati. Non stimarlo.

## Riferimenti

- [references/fonti.md](references/fonti.md) — gerarchia delle fonti e vigenza.
- [references/fiscalita.md](references/fiscalita.md) — redditi di capitale vs
  diversi, titoli pubblici, OICR, zainetto, successione.
- [references/regole-correnti.md](references/regole-correnti.md) — valori
  variabili nel tempo, con data di verifica.

## Script

Tutti gli script sono stdlib-only e stampano JSON.

```bash
# Analisi base
python scripts/portfolio.py analizza portafoglio.csv

# Zainetto strutturato per broker e scadenza
python scripts/zainetto.py stato zainetto.csv --anno-fiscale 2026
python scripts/zainetto.py compensa zainetto.csv --importo 700 \
  --broker Directa --regime amministrato --anno-fiscale 2026

# Ribilanciamento usando il vero zainetto fiscale disponibile per posizione
python scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 --regime amministrato

# Verifica ISIN/tipo contro un registry costruito da KID/prospetti verificati
python scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv

# Blocca il portfolio se anche uno strumento non e' verificato
python scripts/portfolio.py analizza portafoglio.csv \
  --registry strumenti.csv --strict-instruments

# Successione: solo casi coperti esplicitamente dal motore
python scripts/successione.py costo --tipo azione --valore-dichiarato 10000
python scripts/successione.py costo --tipo titolo_stato \
  --esente-successione --valore-normale 10250

# Test
python tests/run_tests.py
python tests/run_support_tests.py
```

Esempi:

- [examples/portafoglio-esempio.csv](examples/portafoglio-esempio.csv)
- [examples/zainetto-esempio.csv](examples/zainetto-esempio.csv)
- [examples/strumenti-registry-esempio.csv](examples/strumenti-registry-esempio.csv)

## Instrument resolver

Il resolver **non cerca di indovinare** che cosa sia un ISIN. Valida il check
digit ISO 6166/Luhn e, se gli viene fornito un registry, confronta il tipo del
portfolio con una classificazione verificata su KID/prospetto.

Una riga di registry è azionabile solo con:

```text
isin,tipo,fonte,verificato_il
```

Se l'ISIN non è nel registry, il tipo è incoerente o mancano fonte/data, la
conclusione fiscale va bloccata in modalità `--strict-instruments`.

## Zainetto strutturato

Formato:

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

La scadenza viene calcolata come quarto periodo d'imposta successivo all'anno
di realizzo. Il simulatore consuma prima i lotti con scadenza più vicina per
minimizzare il rischio di perderli: **questa è una strategia del simulatore, non
una regola contabile imposta al broker**.

`--minus 2000` resta disponibile solo come modalità legacy semplificata.

## Successione

Non usare mai la parola "affrancamento" come scorciatoia. Separa almeno:

1. inclusione/esclusione dall'attivo ereditario;
2. eventuale imposta di successione;
3. costo fiscalmente riconosciuto all'erede;
4. futura tassazione del rendimento/cessione, che dipende dalla natura dello
   strumento.

`scripts/successione.py` implementa soltanto i casi direttamente coperti dalla
regola dell'art. 68 c.6 per azioni/titoli/obbligazioni: valore definito o, in
mancanza, dichiarato; per titoli esenti, valore normale alla data di apertura;
oneri inerenti documentabili aggiunti al costo. Per ETF/OICR e strumenti
ibridi il modulo fa hard-stop invece di estendere la regola per analogia.

## Output incompleto

Quando un dato necessario manca, il motore non produce falsa precisione. Può
restituire `imposta_stimata: null`, `dato_mancante` e uno scenario min/max. Lo
stesso vale per la minusvalenza fiscalmente rilevante di un OICR quando manca
la percentuale agevolata.

## Claim audit (obbligatoria)

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

Una riga per ogni affermazione che può influenzare una decisione. Se fonte o
confidenza non sono adeguate, marca la conclusione come non azionabile.

## Limiti

Questa skill produce **analisi e simulazioni**, non consulenza finanziaria né
fiscale. Le imposte effettive in amministrato restano quelle determinate
dall'intermediario. Non suggerire operazioni motivate soltanto dal recupero di
minusvalenze.

## Convenzioni portfolio CSV

Colonne richieste: `isin,nome,tipo,quantita,pmc,prezzo,asset_class`.
Consigliate: `valuta_esposizione,area,settore,broker,quota_stato`.

Obbligazioni: `quantita` = valore nominale, `pmc` e `prezzo` in frazione
(corso 101,30 → `1.0130`). `valuta_esposizione` è la valuta economica dei
sottostanti, non quella di quotazione. `quota_stato` è compresa tra 0 e 1 e
deve provenire dall'emittente/intermediario; se manca non assumere 0.
