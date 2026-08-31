---
name: italian-investor
description: Analisi di portafoglio tax-aware per residenti fiscali italiani. Da usare quando si analizza un portafoglio (ETF, azioni, BTP, obbligazioni, certificates), si simula una vendita o un ribilanciamento, si ragiona su minusvalenze/zainetto fiscale, successione o imposte su strumenti finanziari italiani. Impone verifica su fonti primarie invece che memoria del modello.
---

# Italian Investor

Analisi di portafoglio per un residente fiscale italiano, con la fiscalità
trattata come **dato da verificare**, non come conoscenza del modello.

La skill contiene una procedura anti-allucinazione e motori Python deterministici.
Il modello interpreta e spiega; non deve inventare norme, classificazioni di
strumenti, basi fiscali o aritmetica.

## Regola zero

Non usare mai la memoria interna del modello per:

- aliquote vigenti e basi imponibili;
- trattamento fiscale di uno strumento o di uno specifico evento;
- compensabilità e scadenza delle minusvalenze;
- criterio di determinazione della base fiscale/ordine dei lotti;
- imposta di successione e costo fiscale dell'erede;
- obblighi dichiarativi, monitoraggio, bollo, IVAFE o imposte di transazione;
- caratteristiche di prodotto (TER, duration, holdings, valuta, ISIN,
  percentuale di titoli pubblici agevolati).

Se non trovi una fonte autorevole: scrivi `NON VERIFICATO` e blocca la
conclusione che ne dipende.

## Procedura obbligatoria

1. **Qualità dati.** Esegui `scripts/portfolio_validator.py`. Non correggere
   silenziosamente quantità, prezzi, duplicati, unità obbligazionarie o ISIN.
2. **Profilo.** Verifica residenza fiscale, regime (amministrato / dichiarativo /
   gestito), broker, anno fiscale e zainetto per anno di realizzo.
3. **Strumento.** Parti da `ISIN → natura giuridica`. Il `tipo` del CSV è una
   dichiarazione, non una prova. Usa `instrument_resolver.py` e un registry
   verificato su KID/prospetto.
4. **Evento.** Identifica vendita, rimborso, cedola, interesse, dividendo,
   distribuzione o successione. Non esiste una sola categoria fiscale per
   strumento. Usa `event_tax.py` per i flussi periodici coperti e
   `tax_engine.py` per le vendite semplici.
5. **Base fiscale.** Prima di usare `pmc`, determina il criterio applicabile.
   Nei casi coperti il lot engine usa CMP in amministrato e LIFO in
   dichiarativo. ETF/OICR non vengono assimilati automaticamente.
6. **Lotti di posizione.** Per vendite parziali azionabili usa un dataset
   `ISIN + broker + data_acquisto + quantità + costo`. Passalo a
   `portfolio.py ribilancia --lotti-posizioni-csv ...`. Il motore verifica che
   la somma dei lotti coincida con la quantità del portfolio.
7. **Riconciliazione.** Se hai sia portfolio sia lotti, esegui
   `portfolio_basis.py` prima di fidarti del PMC. Una differenza tra costo da
   PMC e costo ricostruito dai lotti non va corretta automaticamente: può
   dipendere da commissioni, trasferimenti, corporate action, valuta o dati
   broker e va spiegata.
8. **Zainetto.** Preferisci il CSV strutturato `broker,regime,anno_realizzo,importo`.
   In amministrato usa solo minus compatibili con intermediario/regime/scadenza;
   in dichiarativo i lotti dichiarativi possono essere aggregati anche se
   originati da intermediari diversi, nei casi previsti.
9. **Valuta e flussi esteri.** Distingui valuta di esposizione da valuta
   fiscalmente rilevante. Per redditi esteri verifica Paese, ritenuta,
   convenzione, intermediario e doppia imposizione prima del calcolo.
10. **Fonti.** Per ogni conclusione fiscale rilevante recupera una fonte corrente
    secondo `references/fonti.md`. Verifica la vigenza per il periodo d'imposta.
11. **Tax drag.** Considera imposta immediata, bollo/IVAFE se applicabili,
    ritenute estere non recuperabili, imposte di transazione, commissioni,
    spread e cambio.
12. **Separazione.** Distingui sempre `dato → legge → calcolo → opinione`.
13. **Claim audit.** Chiudi ogni analisi con la tabella di audit.
14. **Stop.** Se manca un dato che può cambiare la conclusione, non stimarlo.

## Riferimenti

- `references/fonti.md` — gerarchia fonti e controllo di vigenza.
- `references/fiscalita.md` — redditi di capitale/diversi, titoli pubblici,
  OICR, zainetto, successione.
- `references/eventi-fiscali.md` — routing per vendita, dividendo, cedola,
  interesse e distribuzione OICR.
- `references/strategie-fiscali.md` — base fiscale, multi-ISIN, ordine
  operazioni, trasferimenti broker, valuta, redditi esteri, Tobin tax, tax drag.
- `references/regole-correnti.md` — snapshot di valori variabili nel tempo.

## Flusso operativo consigliato

```text
portfolio.csv
   ↓
portfolio_validator.py
   ↓
registry ISIN verificato + policy freschezza
   ↓
evento fiscale
   ↓
lotti posizione → riconciliazione PMC/base fiscale
   ↓
regime + zainetto
   ↓
motore deterministico
   ↓
interpretazione + claim audit + fonti
```

## Script principali

Tutti gli script sono stdlib-only e stampano JSON.

```bash
# Qualità dati
python scripts/portfolio_validator.py valida portafoglio.csv

# Analisi portfolio
python scripts/portfolio.py analizza portafoglio.csv

# Registry ISIN con controllo opzionale di freschezza
python scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv \
  --max-age-giorni 365 --data-riferimento 2026-08-31

# Zainetto
python scripts/zainetto.py stato zainetto.csv --anno-fiscale 2026

# Base fiscale CMP/LIFO e stato residuo
python scripts/cost_basis.py calcola lotti.csv --metodo lifo --quantita 15
python scripts/cost_basis.py consuma lotti.csv --metodo lifo --quantita 15

# Vendita singola lot-aware
python scripts/lot_sale.py vendita --tipo azione --regime dichiarativo \
  --lotti lotti.csv --prezzo 140 --quantita 15

# Dataset lotti multi-posizione
python scripts/portfolio_lots.py lotti-portafoglio.csv

# Riconcilia PMC del portfolio con la base ricostruita dai lotti
python scripts/portfolio_basis.py portafoglio.csv lotti-portafoglio.csv

# Ribilanciamento con zainetto + lotti reali per ISIN/broker
python scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 \
  --regime dichiarativo \
  --lotti-posizioni-csv lotti-portafoglio.csv

# Evento periodico
python scripts/event_tax.py provento --tipo azione --evento dividendo --lordo 100
python scripts/event_tax.py provento --tipo etf --evento distribuzione \
  --lordo 100 --quota-stato 0.30

# Successione nei casi coperti
python scripts/successione.py costo --tipo titolo_stato \
  --esente-successione --valore-normale 10250
```

## Dataset portfolio

Colonne richieste:

```text
isin,nome,tipo,quantita,pmc,prezzo,asset_class
```

Consigliate:

```text
valuta_esposizione,valuta_quotazione,area,settore,broker,quota_stato
```

Per obbligazioni `quantita` è il valore nominale; `pmc` e `prezzo` sono in
frazione (`101,30` → `1.0130`).

Lo stesso ISIN su broker diversi resta separato fiscalmente, ma HHI/top-5 sono
aggregati per ISIN per rappresentare la concentrazione economica reale.

## Dataset lotti di posizione

Per vendite parziali di azioni, obbligazioni, titoli pubblici e certificates nei
casi coperti usa:

```text
isin,broker,data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur
US0378331005,BrokerA,2024-01-10,20,130,2
US0378331005,BrokerA,2026-06-10,20,160,2
```

Regole operative:

- `ISIN + broker` identifica la posizione fiscale simulata;
- la somma delle quantità dei lotti deve coincidere con la quantità del portfolio;
- i costi devono essere già convertiti in EUR con il cambio fiscalmente
  rilevante verificato;
- ogni strategia di ribilanciamento riparte dagli stessi lotti iniziali;
- all'interno di una strategia i lotti vengono consumati operazione per
  operazione e lo stato residuo viene riportato nell'output;
- in CMP il residuo è un pool simulato che mantiene il costo medio: non usarlo
  per inferire un successivo LIFO dopo un cambio di regime;
- ETF/OICR restano fuori dal routing automatico CMP/LIFO.

Esempio: `examples/lotti-portafoglio-esempio.csv`.

## Riconciliazione PMC / base fiscale

`scripts/portfolio_basis.py` confronta, per ogni posizione coperta dal lot
engine:

```text
quantità portfolio vs quantità lotti
PMC dichiarato vs costo medio ricostruito
costo totale da PMC vs costo totale dei lotti
differenza in euro
```

È un controllo, non una correzione automatica. Se i due costi divergono, marca
la posizione `verificare_pmc_e_base_fiscale` e cerca la causa prima di usare il
valore in una simulazione azionabile. ETF/OICR restano esplicitamente fuori da
questa riconciliazione automatica.

## Base fiscale e ribilanciamento

Il campo `pmc` è un input operativo, **non una prova della base fiscale**.

Nei casi coperti:

- amministrato → costo medio ponderato;
- dichiarativo → LIFO;
- `lot_sale.py` collega la base da lotti al `tax_engine.py`;
- `portfolio.py` può consumare lotti e zainetto nello stesso scenario;
- la strategia tax-aware ordina le vendite usando la base fiscale dello
  scenario, senza mutare i lotti delle strategie alternative.

Se `--lotti-posizioni-csv` non è fornito, `portfolio.py` mantiene la modalità
legacy basata sul PMC e lo dichiara esplicitamente. In dichiarativo una vendita
parziale basata solo sul PMC non va presentata come definitiva.

## Evento fiscale prima della categoria

Esempi coperti:

```text
azione + vendita           -> reddito diverso
azione + dividendo         -> reddito di capitale
obbligazione + vendita     -> reddito diverso
obbligazione + cedola      -> reddito di capitale
titolo pubblico + vendita  -> reddito diverso con disciplina agevolata
titolo pubblico + cedola   -> reddito di capitale agevolato
ETF/OICR + distribuzione   -> reddito di capitale
```

Per una fonte estera `event_tax.py` fa hard-stop anche se l'utente non ha già
indicato una ritenuta: il Paese estero basta a richiedere la verifica della
doppia imposizione.

## Registry strumenti e freschezza

Formato:

```text
isin,tipo,fonte,verificato_il
```

`verificato_il` deve essere ISO `YYYY-MM-DD`. `--max-age-giorni` è opzionale e
non ha un default implicito: quando viene impostato, una voce troppo vecchia o
con data futura rispetto a `--data-riferimento` diventa non azionabile.

Riconoscere il tipo non implica che il motore conosca automaticamente la sua
fiscalità: ETC/ETN, OICR non armonizzati, cripto, PIR e previdenza possono essere
identificati dal resolver e restare in hard-stop fiscale.

## Zainetto strutturato

Formato:

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

In amministrato il broker limita i lotti utilizzabili. In dichiarativo il
simulatore può aggregare i lotti marcati dichiarativo anche se provengono da
intermediari diversi. Il motore consuma prima le scadenze più vicine: è una
strategia di simulazione, non una regola contabile attribuita al broker.

## Output incompleto

Quando manca un dato necessario, il motore preferisce `null`, scenario min/max
o hard-stop alla falsa precisione. Esempi:

- `quota_stato` mancante su OICR;
- lotti mancanti o quantità incoerenti;
- più lotti LIFO nella stessa data con vendita parziale e ordine intraday ignoto;
- ritenute/redditi esteri senza disciplina verificata;
- strumento identificato ma fiscalità prodotto-specifica non verificata.

## Claim audit obbligatoria

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

Una riga per ogni affermazione che può influenzare una decisione. Se fonte o
confidenza non sono adeguate, marca la conclusione come non azionabile.

## Test

```bash
python tests/run_tests.py
python tests/run_support_tests.py
python tests/run_extended_tests.py
```

La CI esegue anche smoke test del flusso portfolio, compresi ribilanciamento con
zainetto + lotti e riconciliazione PMC/base fiscale, e verifica l'allineamento
delle versioni dei manifest.

## Limiti

Questa skill produce **analisi e simulazioni**, non consulenza finanziaria né
fiscale. Le imposte effettive in amministrato restano quelle determinate
dall'intermediario. Non suggerire operazioni motivate soltanto dal recupero di
minusvalenze.
