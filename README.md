# Italian Investor — Agent Skill per portafogli e fiscalità italiana

[![test](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml/badge.svg)](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml)

**Italian Investor** è una Agent Skill open source per analizzare il portafoglio
di un residente fiscale italiano con una regola semplice: **la fiscalità non si
prende dalla memoria del modello**.

Il progetto combina verifica su fonti primarie, validazione dei dati, calcoli
Python deterministici e hard-stop quando mancano informazioni sufficienti.
Distingue inoltre **strumento ed evento fiscale**: una obbligazione, per esempio,
può produrre un reddito diverso quando viene venduta e un reddito di capitale
quando paga una cedola.

> Analisi e simulazione, **non** consulenza finanziaria né fiscale e non un software per compilare automaticamente la dichiarazione dei redditi.

## Cosa copre

- ETF/OICR, azioni, BTP e altri titoli pubblici agevolati, obbligazioni e
  certificates nei casi esplicitamente coperti;
- vendita, rimborso, dividendo, cedola/interesse e distribuzione OICR come eventi
  distinti;
- minusvalenze e zainetto per broker, regime, anno e scadenza;
- base fiscale da lotti con CMP/LIFO nei casi verificati;
- ribilanciamento tax-aware e costo fiscale immediato;
- quota OICR riferibile a titoli pubblici;
- valuta estera, broker/redditi esteri, Tobin tax e tax drag come controlli da
  verificare prima di rendere una conclusione azionabile;
- alcuni casi di successione;
- validazione strutturale del portfolio e verifica ISIN/tipo tramite registry.

ETC/ETN, OICR non armonizzati, cripto, PIR, previdenza e strumenti con
trattamento non generalizzabile vengono bloccati quando manca una regola
verificata applicabile.

## Errori che la skill evita

Tra gli errori esplicitamente intercettati:

- compensare una minus con un guadagno ETF classificato come reddito di capitale;
- trattare un ETF governativo come automaticamente tassato tutto al 12,5%;
- applicare il 48,08% nel punto sbagliato rispetto alla compensazione;
- usare un `pmc` qualsiasi come se fosse sempre la base fiscale corretta;
- usare CMP e LIFO senza distinguere regime, strumento ed evento;
- classificare la cedola di una obbligazione come il capital gain della vendita;
- calcolare un dividendo estero ignorando ritenuta alla fonte e convenzione;
- usare le minus di un broker come se fossero disponibili su un altro;
- spostare virtualmente lo zainetto senza certificazione/regola verificata;
- sottostimare la concentrazione perché lo stesso ISIN è detenuto su più broker;
- fidarsi di `tipo=etf` senza verifica ISIN/KID/prospetto;
- estendere per analogia la fiscalità ETF a ETC/ETN;
- confondere valuta di esposizione e valuta fiscalmente rilevante;
- comprimere successione, costo fiscale dell'erede e futura tassazione in una
  sola regola.

## Flusso consigliato

```text
CSV / dati portfolio
        |
        v
validazione strutturale
        |
        v
ISIN -> natura giuridica
        |
        v
evento fiscale
        |
        v
regime + broker + base fiscale/lotti + zainetto
        |
        v
fonte primaria vigente
        |
        v
motore deterministico
        |
        v
interpretazione + claim audit
```

La skill **non è un provider di market data**. Prezzi, holdings, duration,
rating, TER, quota titoli pubblici e caratteristiche del prodotto devono
provenire da fonti attendibili e poi essere passati al motore.

## Uso rapido

```bash
# 1. Qualità dati
python skills/italian-investor/scripts/portfolio_validator.py valida portafoglio.csv

# 2. Analisi portfolio
python skills/italian-investor/scripts/portfolio.py analizza portafoglio.csv

# 3. Verifica ISIN/tipo
python skills/italian-investor/scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv

# 4. Vendita semplice
python skills/italian-investor/scripts/tax_engine.py vendita \
  --tipo etf --pmc 90 --prezzo 120 --quantita 100 --quota-stato 0.35

# 5. Base fiscale da lotti
python skills/italian-investor/scripts/cost_basis.py calcola lotti.csv \
  --metodo lifo --quantita 15

# 6. Vendita lot-aware nei casi coperti
python skills/italian-investor/scripts/lot_sale.py vendita \
  --tipo azione --regime dichiarativo --lotti lotti.csv \
  --prezzo 140 --quantita 15

# 7. Dividendo / cedola / distribuzione
python skills/italian-investor/scripts/event_tax.py provento \
  --tipo azione --evento dividendo --lordo 100
python skills/italian-investor/scripts/event_tax.py provento \
  --tipo etf --evento distribuzione --lordo 100 --quota-stato 0.30

# 8. Zainetto
python skills/italian-investor/scripts/zainetto.py stato zainetto.csv \
  --anno-fiscale 2026

# 9. Ribilanciamento
python skills/italian-investor/scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 \
  --regime amministrato

# 10. Successione nei casi coperti
python skills/italian-investor/scripts/successione.py costo \
  --tipo titolo_stato --esente-successione --valore-normale 10250
```

## Evento fiscale prima della categoria

Una classificazione fiscale è riferita a un **evento**, non semplicemente al
nome dello strumento.

```text
azione + vendita          -> reddito diverso nei casi coperti
azione + dividendo        -> reddito di capitale
obbligazione + vendita    -> reddito diverso nei casi coperti
obbligazione + cedola     -> reddito di capitale
titolo pubblico + vendita -> reddito diverso con disciplina agevolata
titolo pubblico + cedola  -> reddito di capitale agevolato
ETF/OICR + distribuzione  -> reddito di capitale
```

Vedi `references/eventi-fiscali.md` e `scripts/event_tax.py`.

## Base fiscale e lotti

Il campo `pmc` del portfolio è un input dichiarato, **non una prova della base
fiscale**.

Nei casi coperti:

- amministrato: `cost_basis.py` può applicare il costo medio ponderato;
- dichiarativo: può applicare LIFO quando la fattispecie verificata lo richiede;
- `lot_sale.py` collega la base derivata dai lotti alla simulazione fiscale;
- ETF/OICR non vengono assimilati automaticamente alle regole lot-aware delle
  altre categorie.

Il file esempio è `skills/italian-investor/examples/lotti-esempio.csv`.

## Zainetto per broker e scadenza

Formato consigliato:

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

Il simulatore distingue broker/regime e scadenza. Quando simula più utilizzi
consuma prima i lotti con scadenza più vicina: è una **strategia del motore**,
non una regola contabile attribuita all'intermediario.

## Validazione e concentrazione

`portfolio_validator.py` blocca dati che renderebbero l'analisi inaffidabile,
come quantità non positive, ISIN invalidi, tipi incoerenti e duplicati dello
stesso `ISIN + broker`.

Se lo stesso ISIN è presente su broker differenti, resta separato nel contesto
fiscale ma `portfolio.py` lo **aggrega per ISIN** nel calcolo di HHI e top-5, in
modo da misurare correttamente la concentrazione economica.

## Fonti e anti-allucinazione

Gerarchia principale:

1. Normattiva, Agenzia delle Entrate, MEF, CONSOB, EUR-Lex/ESMA;
2. KID/prospetto/emittente e documenti di quotazione;
3. database finanziari e documentazione del broker;
4. blog/forum solo come pista di ricerca.

I valori variabili nel tempo sono separati in `references/regole-correnti.md`.
Una regola senza fonte adeguata resta `NON VERIFICATO`.

La skill chiude le analisi con un **claim audit**:

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

## Test

```bash
python skills/italian-investor/tests/run_tests.py
python skills/italian-investor/tests/run_support_tests.py
python skills/italian-investor/tests/run_extended_tests.py
```

La CI esegue inoltre smoke test degli script e verifica che le versioni dei
manifest Claude, marketplace Claude e Codex siano identiche.

## Compatibilità e distribuzione

La sorgente canonica e provider-neutral è `skills/italian-investor/`.

- **Claude Code**: marketplace/plugin in `.claude-plugin/`.
- **ChatGPT + Codex**: manifest nativo in `.codex-plugin/plugin.json` e repo
  marketplace in `.agents/plugins/marketplace.json`.
- **OpenAI Skills API**: la stessa directory della skill può essere caricata e
  versionata senza duplicare le istruzioni.

Per submission e test reviewer vedi [OPENAI.md](OPENAI.md).

### Claude Code

```bash
/plugin marketplace add eliazv/italian-investor
/plugin install italian-investor@italian-investor
```

### OpenAI Skills API

```bash
export OPENAI_API_KEY="..."
bash ./tools/openai/upload-skill.sh
```

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

**v0.5.0** — aggiunge classificazione per evento fiscale, proventi periodici,
base fiscale e vendite a lotti, validazione portfolio, HHI aggregato per ISIN e
controlli CI più forti sui manifest.

Il nuovo testo unico delle imposte sui redditi (D.Lgs. 117/2026) è applicabile
dal 1° gennaio 2027 e cambia la numerazione dei riferimenti: la skill impone di
verificare il testo vigente per il periodo d'imposta analizzato.

## Supporto e policy

- [Supporto](SUPPORT.md)
- [Privacy policy](PRIVACY.md)
- [Termini d'uso](TERMS.md)

## Licenza

MIT — vedi [LICENSE](LICENSE).
