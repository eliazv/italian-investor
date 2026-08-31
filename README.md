# Italian Investor — Agent Skill per portafogli e fiscalità italiana

[![test](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml/badge.svg)](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml)

**Italian Investor** è una Agent Skill open source per analizzare il portafoglio
di un residente fiscale italiano con una regola semplice: **la fiscalità non si
prende dalla memoria del modello**.

Il progetto combina fonti primarie, validazione dei dati, calcoli Python
deterministici e hard-stop quando mancano informazioni sufficienti. Distingue
strumento, evento fiscale, regime, broker, base fiscale e zainetto.

> Analisi e simulazione, **non** consulenza finanziaria né fiscale e non un software per compilare automaticamente la dichiarazione dei redditi.

## Cosa copre

- ETF/OICR, azioni, BTP e altri titoli pubblici agevolati, obbligazioni e
  certificates nei casi esplicitamente coperti;
- vendita, dividendo, cedola/interesse e distribuzione OICR come eventi distinti;
- minusvalenze e zainetto per broker, regime, anno e scadenza;
- base fiscale CMP/LIFO nei casi verificati;
- vendite parziali con lotti reali;
- **ribilanciamento con zainetto + lotti fiscali per ISIN e broker**;
- quota OICR riferibile a titoli pubblici;
- controlli su valuta, redditi esteri, Tobin tax e tax drag;
- alcuni casi di successione;
- validazione strutturale del portfolio e registry ISIN con controllo opzionale
  di freschezza.

ETC/ETN, OICR non armonizzati, cripto, PIR, previdenza e strumenti con
trattamento non generalizzabile vengono bloccati quando manca una regola
verificata applicabile.

## Errori che la skill evita

- compensare una minus con un guadagno ETF classificato come reddito di capitale;
- trattare un ETF governativo come automaticamente tassato tutto al 12,5%;
- usare un `pmc` qualsiasi come base fiscale universale;
- usare CMP e LIFO senza distinguere regime, strumento ed evento;
- riutilizzare in sequenza lotti già venduti;
- fare una vendita parziale dichiarativa usando un PMC medio come se fosse LIFO;
- classificare una cedola come il capital gain della vendita;
- calcolare un dividendo estero ignorando la doppia imposizione;
- usare le minus di un broker su un altro;
- sottostimare la concentrazione perché lo stesso ISIN è detenuto su più broker;
- fidarsi di un registry strumenti vecchio indefinitamente;
- estendere per analogia la fiscalità ETF a ETC/ETN;
- confondere valuta di esposizione e valuta fiscalmente rilevante.

## Flusso consigliato

```text
portfolio.csv
        ↓
portfolio_validator.py
        ↓
registry ISIN verificato
        ↓
evento fiscale
        ↓
regime + broker + lotti posizione + zainetto
        ↓
fonte primaria vigente
        ↓
motore deterministico
        ↓
interpretazione + claim audit
```

La skill **non è un provider di market data**. Prezzi, holdings, duration,
rating, TER, quota titoli pubblici e caratteristiche del prodotto devono
provenire da fonti attendibili.

## Uso rapido

```bash
# Qualità dati
python skills/italian-investor/scripts/portfolio_validator.py valida portafoglio.csv

# Analisi portfolio
python skills/italian-investor/scripts/portfolio.py analizza portafoglio.csv

# Registry ISIN con policy opzionale di freschezza
python skills/italian-investor/scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv \
  --max-age-giorni 365 --data-riferimento 2026-08-31

# Vendita semplice
python skills/italian-investor/scripts/tax_engine.py vendita \
  --tipo etf --pmc 90 --prezzo 120 --quantita 100 --quota-stato 0.35

# Base fiscale da lotti + residuo
python skills/italian-investor/scripts/cost_basis.py consuma lotti.csv \
  --metodo lifo --quantita 15

# Vendita singola lot-aware
python skills/italian-investor/scripts/lot_sale.py vendita \
  --tipo azione --regime dichiarativo --lotti lotti.csv \
  --prezzo 140 --quantita 15

# Dataset multi-posizione dei lotti
python skills/italian-investor/scripts/portfolio_lots.py lotti-portafoglio.csv

# Zainetto
python skills/italian-investor/scripts/zainetto.py stato zainetto.csv \
  --anno-fiscale 2026

# Ribilanciamento end-to-end con zainetto + lotti reali
python skills/italian-investor/scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 \
  --regime dichiarativo \
  --lotti-posizioni-csv lotti-portafoglio.csv

# Dividendo / cedola / distribuzione
python skills/italian-investor/scripts/event_tax.py provento \
  --tipo azione --evento dividendo --lordo 100

# Successione nei casi coperti
python skills/italian-investor/scripts/successione.py costo \
  --tipo titolo_stato --esente-successione --valore-normale 10250
```

## Lotti fiscali nel ribilanciamento

La novità della **v0.5.1** è l'integrazione dei lotti direttamente dentro
`portfolio.py ribilancia`.

Formato:

```text
isin,broker,data_acquisto,quantita,costo_unitario_eur,costi_acquisto_eur
US0378331005,BrokerA,2024-01-10,20,130,2
US0378331005,BrokerA,2026-06-10,20,160,2
```

Quando `--lotti-posizioni-csv` è presente:

1. il motore raggruppa i lotti per `ISIN + broker`;
2. verifica che la quantità totale coincida con quella del portfolio;
3. per i tipi coperti applica CMP in amministrato o LIFO in dichiarativo;
4. simula la vendita con la base fiscale derivata dai lotti;
5. aggiorna lo zainetto;
6. consuma i lotti realmente usati e porta il residuo alla vendita successiva;
7. riporta in output metodo, base fiscale, quantità venduta e lotti residui;
8. riparte dai lotti iniziali per ogni strategia alternativa, evitando
   contaminazioni tra scenario A/B/C/D.

Per il CMP il residuo mantiene proporzionalmente il pool e il costo medio: è uno
stato di simulazione nello stesso regime, non una ricostruzione valida per un
successivo cambio a LIFO.

ETF/OICR restano fuori dal routing automatico CMP/LIFO e continuano a richiedere
la verifica della loro disciplina specifica.

Esempio completo:
`skills/italian-investor/examples/lotti-portafoglio-esempio.csv`.

## Evento fiscale prima della categoria

```text
azione + vendita           -> reddito diverso nei casi coperti
azione + dividendo         -> reddito di capitale
obbligazione + vendita     -> reddito diverso
obbligazione + cedola      -> reddito di capitale
titolo pubblico + vendita  -> reddito diverso con disciplina agevolata
titolo pubblico + cedola   -> reddito di capitale agevolato
ETF/OICR + distribuzione   -> reddito di capitale
```

Vedi `references/eventi-fiscali.md` e `scripts/event_tax.py`.

## Registry strumenti e freschezza

Formato:

```text
isin,tipo,fonte,verificato_il
```

`verificato_il` deve essere `YYYY-MM-DD`. Con `--max-age-giorni` una verifica
troppo vecchia diventa non azionabile. Nessuna soglia viene inventata di
default.

## Validazione e concentrazione

`portfolio_validator.py` blocca quantità/prezzi non validi, ISIN invalidi,
tipi incoerenti, `quota_stato` fuori intervallo e duplicati dello stesso
`ISIN + broker`.

Lo stesso ISIN su broker diversi resta separato fiscalmente, ma HHI e top-5
sono aggregati per ISIN per misurare correttamente la concentrazione economica.

## Zainetto per broker e scadenza

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

Il simulatore consuma prima le minus con scadenza più vicina per minimizzare il
rischio di perderle. È una strategia del motore, non una regola contabile
attribuita all'intermediario.

## Fonti e anti-allucinazione

Gerarchia principale:

1. Normattiva, Agenzia delle Entrate, MEF, CONSOB, EUR-Lex/ESMA;
2. KID/prospetto/emittente e documenti di quotazione;
3. database finanziari e documentazione del broker;
4. blog/forum solo come pista di ricerca.

I valori variabili nel tempo stanno in `references/regole-correnti.md`.
Una regola senza fonte adeguata resta `NON VERIFICATO`.

## Test

```bash
python skills/italian-investor/tests/run_tests.py
python skills/italian-investor/tests/run_support_tests.py
python skills/italian-investor/tests/run_extended_tests.py
```

La CI esegue anche smoke test del ribilanciamento con zainetto + lotti e verifica
che le versioni dei manifest Claude, marketplace Claude e Codex coincidano.

## Compatibilità e distribuzione

La sorgente canonica è `skills/italian-investor/`.

- **Claude Code**: `.claude-plugin/`.
- **ChatGPT + Codex**: `.codex-plugin/plugin.json` e `.agents/plugins/marketplace.json`.
- **OpenAI Skills API**: stessa directory Agent Skill.

Per submission e test reviewer vedi [OPENAI.md](OPENAI.md).

## Struttura principale

```text
skills/italian-investor/
├── SKILL.md
├── references/
│   ├── fonti.md
│   ├── fiscalita.md
│   ├── eventi-fiscali.md
│   ├── strategie-fiscali.md
│   └── regole-correnti.md
├── scripts/
│   ├── portfolio_validator.py
│   ├── instrument_resolver.py
│   ├── portfolio_lots.py
│   ├── portfolio.py
│   ├── tax_engine.py
│   ├── event_tax.py
│   ├── cost_basis.py
│   ├── lot_sale.py
│   ├── zainetto.py
│   └── successione.py
├── examples/
│   ├── portafoglio-esempio.csv
│   ├── lotti-esempio.csv
│   ├── lotti-portafoglio-esempio.csv
│   ├── zainetto-esempio.csv
│   └── strumenti-registry-esempio.csv
└── tests/
    ├── casi_fiscali.json
    ├── casi_successione.json
    ├── run_tests.py
    ├── run_support_tests.py
    └── run_extended_tests.py
```

## Stato

**v0.5.1** — aggiunge ribilanciamento lot-aware end-to-end, stato residuo dei
lotti, validazione quantità portfolio/lotti e integrazione simultanea con lo
zainetto fiscale.

Il nuovo testo unico delle imposte sui redditi (D.Lgs. 117/2026) è applicabile
dal 1° gennaio 2027 e cambia la numerazione dei riferimenti: la skill impone di
verificare il testo vigente per il periodo d'imposta analizzato.

## Supporto e policy

- [Supporto](SUPPORT.md)
- [Privacy policy](PRIVACY.md)
- [Termini d'uso](TERMS.md)

## Licenza

MIT — vedi [LICENSE](LICENSE).
