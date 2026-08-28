# Italian Investor — Agent Skill per l'analisi di portafoglio e la fiscalità italiana

[![test](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml/badge.svg)](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml)

**Italian Investor** è una Agent Skill open source per analizzare il portafoglio
di un residente fiscale italiano con una regola semplice: **la fiscalità non si
prende dalla memoria del modello**.

Il progetto combina procedura di verifica su fonti primarie, calcoli Python
deterministici e hard-stop quando mancano dati o classificazioni affidabili.
Copre ETF/OICR, azioni, BTP e altri titoli pubblici agevolati, obbligazioni,
certificates, minusvalenze/zainetto fiscale, ribilanciamento tax-aware e alcuni
casi di successione. ETC/ETN e strumenti con trattamento non generalizzabile
vengono bloccati finché non viene verificato il prospetto specifico.

> Analisi e simulazione, **non** consulenza finanziaria né fiscale e non un software per compilare automaticamente la dichiarazione dei redditi.

## Compatibilità e distribuzione

La sorgente canonica e provider-neutral è `skills/italian-investor/`.

- **Claude Code**: plugin installabile tramite il marketplace GitHub incluso in `.claude-plugin/`.
- **ChatGPT + Codex**: plugin OpenAI skills-only, con manifest nativo in `.codex-plugin/plugin.json` e marketplace repo in `.agents/plugins/marketplace.json` per test/distribuzione locale.
- **OpenAI Skills API**: la stessa directory Agent Skill può essere caricata e versionata in un progetto API senza duplicare le istruzioni.

La pubblicazione nella Plugin Directory e il caricamento tramite Skills API sono due flussi separati: la Skills API non rende automaticamente pubblica la skill nella directory.

Per procedura di submission, test reviewer e upload API vedi **[OPENAI.md](OPENAI.md)**.

## Cosa evita

Errori tipici che un LLM generalista può commettere:

- compensare le minusvalenze con un guadagno da ETF;
- trattare un ETF governativo come automaticamente tassato tutto al 12,5%;
- applicare il 48,08% nel punto sbagliato rispetto alla compensazione;
- ignorare la riduzione della perdita OICR riferibile a titoli pubblici;
- usare le minus di un broker come se fossero disponibili su un altro;
- ignorare l'anno di scadenza dello zainetto;
- fidarsi del campo `tipo=etf` senza verificare l'ISIN/KID/prospetto;
- estendere per analogia la fiscalità di ETF a ETC/ETN;
- comprimere successione, costo fiscale dell'erede e futura plusvalenza in una singola regola.

## Installazione

### Claude Code

```bash
/plugin marketplace add eliazv/italian-investor
/plugin install italian-investor@italian-investor
```

Oppure:

```bash
git clone https://github.com/eliazv/italian-investor.git
cp -r italian-investor/skills/italian-investor ~/.claude/skills/
```

### ChatGPT / Codex

Il repository contiene il manifest OpenAI `.codex-plugin/plugin.json` e un repo marketplace `.agents/plugins/marketplace.json`. Per sviluppo/test apri il repository come progetto, riavvia ChatGPT desktop dopo modifiche al marketplace/plugin e verifica **Italian Investor** tra i plugin disponibili sulle superfici in cui i repo marketplace sono abilitati.

Per pubblicarlo nella directory universale ChatGPT + Codex usa il **Plugin Submission Portal**, scegliendo **Skills only**. La checklist completa e i materiali reviewer sono in [OPENAI.md](OPENAI.md) e [openai/submission-tests.md](openai/submission-tests.md).

### OpenAI Skills API

Con una API key OpenAI configurata:

```bash
export OPENAI_API_KEY="..."
bash ./tools/openai/upload-skill.sh
```

Per creare una nuova versione di una skill API esistente e impostarla come default:

```bash
bash ./tools/openai/upload-skill.sh skill_XXXXXXXX
```

Il core della skill richiede solo Python 3; l'helper opzionale per la Skills API richiede `curl` e `zip`.

## Flusso consigliato

```text
Google Sheet / CSV portfolio
          |
          v
verifica ISIN / natura giuridica
          |
          v
portfolio + zainetto per broker/anno
          |
          v
motore fiscale deterministico
          |
          v
ribilanciamento / scenari
          |
          v
modello: interpretazione + claim audit + fonti
```

La skill **non è un provider di market data**: prezzi, holdings, duration,
rating, TER e dati di prodotto vanno recuperati da fonti esterne attendibili
(KID/prospetto, emittente, broker o data provider) e poi passati al motore.

## Uso rapido

```bash
python skills/italian-investor/scripts/portfolio.py analizza portafoglio.csv

python skills/italian-investor/scripts/zainetto.py stato zainetto.csv \
  --anno-fiscale 2026

python skills/italian-investor/scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 \
  --regime amministrato

python skills/italian-investor/scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv

python skills/italian-investor/scripts/portfolio.py analizza portafoglio.csv \
  --registry strumenti.csv --strict-instruments

python skills/italian-investor/scripts/tax_engine.py vendita \
  --tipo etf --pmc 90 --prezzo 120 --quantita 100 --quota-stato 0.35

python skills/italian-investor/scripts/successione.py costo \
  --tipo titolo_stato --esente-successione --valore-normale 10250

python skills/italian-investor/tests/run_tests.py
python skills/italian-investor/tests/run_support_tests.py
```

## Zainetto fiscale per broker e scadenza

Il vecchio `--minus 2000` resta come modalità legacy, ma il formato consigliato è un CSV a lotti:

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

La scadenza è calcolata come quarto periodo d'imposta successivo all'anno di realizzo. In **amministrato** il simulatore rende disponibili solo le minus non scadute dello stesso broker della vendita. In **dichiarativo** può aggregare i lotti marcati dichiarativo.

Quando simula più vendite, consuma prima i lotti con la scadenza più vicina. Questa è una scelta di ottimizzazione del simulatore, non una pretesa sull'ordine contabile applicato dal singolo intermediario.

Esempio: `skills/italian-investor/examples/zainetto-esempio.csv`.

## Instrument resolver

`instrument_resolver.py` non tenta di indovinare il prodotto dal prefisso ISIN. Valida formalmente l'ISIN tramite check digit e confronta il `tipo` dichiarato nel portfolio con un registry verificato su KID/prospetto:

```text
isin,tipo,fonte,verificato_il
US0378331005,azione,prospetto/emittente,2026-08-24
```

Se l'ISIN manca dal registry, il tipo è incoerente oppure mancano fonte/data, `--strict-instruments` blocca l'analisi fiscale.

Esempio/template: `skills/italian-investor/examples/strumenti-registry-esempio.csv`.

## Fiscalità implementata

Tra le regole già sottoposte a test di regressione:

- guadagno OICR/ETF come reddito di capitale e asimmetria con le minus;
- perdita OICR come reddito diverso;
- quota OICR riferibile a titoli pubblici agevolati;
- 26% ordinario;
- titoli pubblici: reddito diverso computato al 48,08% **prima** della compensazione;
- perdita su titolo pubblico ridotta al 48,08%;
- azioni, obbligazioni e certificates nei casi coperti;
- commissioni/oneri inerenti nel calcolo del costo;
- hard-stop su cripto, OICR non armonizzati, PIR, previdenza ed ETC/ETN quando non esiste una qualificazione verificata applicabile.

Se `quota_stato` di un OICR manca, il motore restituisce uno **scenario** e non un numero fittiziamente preciso. Se è fuori dall'intervallo 0..1, viene rifiutata.

## Successione

La skill separa sempre:

1. cosa entra nell'attivo ereditario;
2. eventuale imposta di successione;
3. costo fiscalmente riconosciuto all'erede;
4. trattamento fiscale della futura vendita/provento.

`scripts/successione.py` implementa in modo deterministico solo la parte coperta direttamente dall'art. 68 c.6 per azioni/titoli/obbligazioni: valore definito o, in mancanza, dichiarato; per titoli esenti, valore normale alla data di apertura; oneri inerenti documentabili aggiunti al costo. ETF/OICR e strumenti ibridi restano fuori da **questo specifico helper**: hanno regole proprie da verificare e non vengono assimilati per analogia.

I casi sono in `tests/casi_successione.json` e fanno parte della CI.

## Fonti e anti-allucinazione

Gerarchia principale:

1. Normattiva, Agenzia delle Entrate, MEF, CONSOB, EUR-Lex/ESMA;
2. KID/prospetti dell'emittente e documenti di quotazione;
3. database finanziari e documentazione del broker;
4. blog/forum solo come pista di ricerca.

Ogni test marcato `normativo` deve contenere `fonte`, `articolo` e `verificato_il`, altrimenti la CI fallisce.

La skill chiude le analisi con un **claim audit**:

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

## Struttura

```text
.codex-plugin/plugin.json
.agents/plugins/marketplace.json
.claude-plugin/
OPENAI.md
PRIVACY.md
SUPPORT.md
TERMS.md
openai/submission-tests.md
tools/openai/upload-skill.sh
skills/italian-investor/
├── SKILL.md
├── references/
│   ├── fonti.md
│   ├── fiscalita.md
│   └── regole-correnti.md
├── scripts/
│   ├── tax_engine.py
│   ├── portfolio.py
│   ├── zainetto.py
│   ├── instrument_resolver.py
│   └── successione.py
├── examples/
│   ├── portafoglio-esempio.csv
│   ├── zainetto-esempio.csv
│   └── strumenti-registry-esempio.csv
└── tests/
    ├── casi_fiscali.json
    ├── casi_successione.json
    ├── run_tests.py
    └── run_support_tests.py
```

## Stato

**v0.4.0**. Le regole portanti sono corredate da riferimenti normativi/prassi e test automatici. La CI esegue casi fiscali, zainetto, resolver ISIN, successione e smoke test del flusso portfolio.

Il nuovo testo unico delle imposte sui redditi (D.Lgs. 117/2026) è applicabile dal 1° gennaio 2027 e cambia la numerazione dei riferimenti: la skill impone di verificare il testo vigente per il periodo d'imposta analizzato.

## Supporto e policy

- [Supporto](SUPPORT.md)
- [Privacy policy](PRIVACY.md)
- [Termini d'uso](TERMS.md)

## Licenza

MIT — vedi [LICENSE](LICENSE).
