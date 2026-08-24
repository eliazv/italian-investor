# Italian Investor — Claude Skill per l'analisi di portafoglio e la fiscalità italiana

[![test](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml/badge.svg)](https://github.com/eliazv/italian-investor/actions/workflows/tests.yml)

**Italian Investor** è una [Agent Skill](https://code.claude.com/docs/en/skills)
open source che permette a Claude (e ad altri agenti compatibili) di analizzare
il portafoglio di un **residente fiscale italiano** senza allucinare sulla
fiscalità: tassazione di ETF, azioni, BTP, obbligazioni, ETC/ETN e certificates,
compensazione delle minusvalenze e **zainetto fiscale**, ribilanciamento
tax-aware, successione.

La differenza rispetto a un prompt "sei un consulente finanziario italiano": qui
la fiscalità non è memorizzata nel modello, è **una procedura di verifica su
fonti primarie** (Normattiva, Agenzia delle Entrate, MEF, CONSOB) più un motore
di calcolo deterministico in Python con test di regressione.

> Analisi e simulazione, **non** consulenza finanziaria né fiscale.

## Perché serve

I modelli generalisti sbagliano sistematicamente su alcuni punti del regime
italiano, perché ragionano con schemi anglosassoni:

- applicano le minusvalenze in zainetto alle plusvalenze da ETF (non è
  possibile: sono redditi di capitale, non redditi diversi);
- assumono che un ETF obbligazionario governativo sia tassato al 12,5% (dipende
  dalla quota agevolata comunicata dall'emittente);
- comprimono la successione in una frase sola, confondendo imposta di
  successione, costo fiscale dell'erede e plusvalenza maturata dal defunto;
- confondono la valuta di quotazione di un ETF con l'esposizione valutaria dei
  sottostanti.

Questa skill blocca esattamente questi errori: li ha come **casi di test**.

## Installazione

Come plugin Claude Code (un comando, aggiornabile):

```
/plugin marketplace add eliazv/italian-investor
/plugin install italian-investor@italian-investor
```

Oppure manualmente, copiando la cartella della skill:

```bash
git clone https://github.com/eliazv/italian-investor.git
cp -r italian-investor/skills/italian-investor ~/.claude/skills/
```

Serve solo Python 3 (nessuna dipendenza esterna).

## Uso

Chiedi in linguaggio naturale, con il tuo CSV o l'export del tuo Google Sheet:

```
Analizza il mio portafoglio.
Quante tasse pago se vendo 100 quote di questo ETF in gain?
Le mie minusvalenze del 2023 possono compensare questa plusvalenza?
Come ribilancio a 60/35/5 minimizzando il tax drag?
```

Gli script sono eseguibili anche da soli:

```bash
python skills/italian-investor/scripts/portfolio.py analizza portafoglio.csv
python skills/italian-investor/scripts/portfolio.py ribilancia portafoglio.csv \
    --target azionario=45,obbligazionario=50,liquidita=5 \
    --minus 2000 --versamento-mensile 1000
python skills/italian-investor/scripts/tax_engine.py vendita \
    --tipo etf --pmc 90 --prezzo 120 --quantita 100 --minus 2000
python skills/italian-investor/tests/run_tests.py
```

## Domande a cui questa skill risponde

### Le minusvalenze si possono compensare con le plusvalenze da ETF?

No. Il provento positivo di un OICR/ETF è **reddito di capitale**, mentre le
minusvalenze in zainetto sono **redditi diversi**: non si incontrano. Vale il
contrario, invece, per la minusvalenza realizzata vendendo un ETF in perdita,
che alimenta lo zainetto. Il motore lo rende esplicito: chiedendo la vendita di
un ETF in gain con 5.000 € di minus disponibili restituisce
`minusvalenze_utilizzate: 0` e un avviso.

### Che cosa compensa le minusvalenze in zainetto?

I redditi diversi di natura finanziaria: capital gain da **azioni,
obbligazioni singole, ETC/ETN, certificates**, valute e derivati. Le
minusvalenze sono utilizzabili entro il quarto anno successivo a quello di
realizzo e, in regime amministrato, lo zainetto è **per singolo intermediario**.

### Un ETF su titoli di Stato è tassato al 12,5%?

Non automaticamente. L'imposizione ridotta si applica alla **quota di provento
riferibile a titoli pubblici italiani, White List ed enti assimilati**,
comunicata dall'emittente o applicata dall'intermediario. Se il dato manca, la
skill non produce un importo singolo: restituisce un **intervallo** (imposta con
quota 0% e con quota 100%), marca `dato_mancante` e chiede la percentuale, invece
di stimarla.

La stessa percentuale conta anche quando l'OICR è venduto in perdita. La
Circolare Agenzia delle Entrate 19/E del 27/06/2014 chiarisce che la perdita
riferibile ai titoli pubblici è deducibile per un importo ridotto del 51,92%:
in pratica quella componente rileva al **48,08%**. Per esempio, su una perdita
di 1.000 € con quota pubblica 50%, la minusvalenza fiscalmente rilevante è
740,40 €. Se la quota non è nota, il motore restituisce uno scenario invece di
inventarla.

### Perché l'aliquota agevolata dà 12,5008% e non 12,5%?

Perché si ottiene computando il reddito diverso nella misura del 48,08%
dell'ammontare realizzato e applicando poi il 26%. Su 1.000 € di plusvalenza
l'imposta è 125,01 €, non 125,00 €.

### Le minusvalenze si sottraggono prima o dopo il 48,08%?

Dopo. L'art. 3 c. 5 del DL 66/2014 riduce il **reddito diverso**, quindi la
compensazione con lo zainetto avviene su un importo già ridotto: 1.000 € di gain
su BTP con 400 € di minus fanno 480,80 − 400 = 80,80 € imponibili, cioè 21,01 €
di imposta. Compensare prima e ridurre dopo darebbe 75 € — sovrastima l'imposta e
spreca minusvalenze. Per lo stesso motivo una perdita di 1.000 € su un titolo
pubblico agevolato entra in zainetto per 480,80 €, non per 1.000 €.

### Che cosa succede fiscalmente in successione?

Sono **quattro problemi distinti**, che non vanno compressi in una frase:
l'imposta di successione (da cui i titoli del debito pubblico italiano e
assimilati sono esclusi dall'attivo ereditario), il costo fiscalmente
riconosciuto all'erede (che spesso produce uno *step-up* del valore di carico),
la plusvalenza maturata dal de cuius e la natura dello strumento. La skill
impone di trattarli separatamente e di citare la norma per ciascuno.

### Conviene vendere per ribilanciare?

La skill non risponde d'istinto: confronta quattro strategie con i numeri —
ribilanciamento immediato, solo nuovi versamenti, parziale, tax-aware — su
imposta stimata, controvalore venduto, drift residuo e tempo. Sul portafoglio di
esempio la strategia tax-aware costa 390 € contro 777 € di quella immediata. Il
drift residuo è calcolato **al netto delle imposte**: l'imposta esce dal
portafoglio, quindi si reinveste meno di quanto si è venduto e il target non
viene centrato esattamente.

## Come funziona

```
SKILL.md                       la procedura: 8 passi, regole anti-allucinazione
references/fonti.md            gerarchia delle fonti Tier 1-4 + permalink ufficiali
references/fiscalita.md        schema di ragionamento fiscale, incl. successione
references/regole-correnti.md  i numeri che cambiano, con data di verifica
scripts/tax_engine.py          classificazione strumenti e simulazione vendite
scripts/portfolio.py           metriche, esposizioni, strategie di ribilanciamento
tests/                         20 casi fiscali/comportamentali, eseguiti in CI
```

Principi:

1. **Mai la fiscalità dalla memoria del modello.** Aliquote, qualificazioni,
   compensazioni e successione vanno verificate su fonte corrente; se la fonte
   manca, la risposta è `NON VERIFICATO` e la conclusione si blocca.
2. **Mai inventare dati di prodotto.** ISIN, TER, duration, rating,
   composizione, quota agevolata: si recuperano dal KID o si chiedono.
3. **Calcoli in Python, non a mente.** Deterministici, testati, ripetibili.
4. **Rifiuto esplicito quando non si può calcolare.** Cripto, ETF non
   armonizzati, fondi pensione e PIR sono riconosciuti ma non calcolati: il
   motore si ferma e chiede verifica.
5. **Claim audit finale.** Ogni affermazione etichettata come dato, legge,
   calcolo o opinione, con fonte e livello di confidenza.
6. **Revisione avversariale.** Un secondo passaggio cerca attivamente errori
   nelle raccomandazioni appena prodotte.

## Formato dati

CSV o export di un Google Sheet, una riga per posizione. Colonne richieste:
`isin, nome, tipo, quantita, pmc, prezzo, asset_class`. Opzionali ma
consigliate: `valuta_esposizione, area, settore, broker, quota_stato`.

- `tipo`: `etf`, `oicr`, `azione`, `obbligazione`, `titolo_stato`, `etc_etn`,
  `certificate`, `liquidita`. È un dato dichiarato in input: prima di usare il
  risultato fiscale va verificato che sia coerente con la natura giuridica
  ricavata dall'ISIN/KID.
- Obbligazioni: `quantita` = valore nominale, `pmc`/`prezzo` in frazione
  (corso 101,30 → `1.0130`).
- `valuta_esposizione`: la valuta dei **sottostanti**, non quella di quotazione.
- `quota_stato`: quota agevolata del fondo, da 0 a 1.

Esempio pronto:
[skills/italian-investor/examples/portafoglio-esempio.csv](skills/italian-investor/examples/portafoglio-esempio.csv).

## Stato e limiti

Versione 0.3. Le regole portanti sono state verificate il 24/08/2026 leggendo il
**testo letterale** delle norme: TUIR artt. 44 c.1 lett. g), 45 c.1, 67 c.1
lett. c-bis)/c-ter)/c-quinquies), 68 c.5 (testo ufficiale Agenzia delle Entrate),
DL 66/2014 art. 3 commi 1 e 5 (Normattiva) e Circolare Agenzia delle Entrate
19/E del 27/06/2014 per il trattamento della componente in titoli pubblici degli
OICR. Ogni caso verificato porta la norma/prassi in `fonte` e `articolo`.

Restano **due assunzioni non verificate nel test suite**, che `run_tests.py`
elenca a ogni esecuzione: la qualificazione di ETC/ETN e la deducibilità degli
oneri di negoziazione. Vanno confermate prima di usare quelle specifiche regole
su un patrimonio reale.

Nota di vigenza: il D.Lgs. 117/2026 ha riordinato le imposte sui redditi in un
nuovo testo unico, applicabile dal **1° gennaio 2027**, che sostituisce il
DPR 917/1986 e cambia la numerazione degli articoli. Fino al periodo d'imposta
2026 si cita il TUIR storico.

In regime amministrato l'imposta effettiva è quella calcolata
dall'intermediario: i numeri prodotti qui sono stime da confrontare con il
rendiconto fiscale del broker.

## Contribuire

Convenzioni del repo (bump di `version` a ogni release, test obbligatori, niente
regole fiscali senza fonte) in [CLAUDE.md](CLAUDE.md).

Il contributo più utile è un **caso fiscale**: aggiungi una voce a
`skills/italian-investor/tests/casi_fiscali.json` con il risultato atteso e la
fonte nel campo `perche`, poi verifica che
`python skills/italian-investor/tests/run_tests.py` passi. Correzioni normative
sono benvenute purché accompagnate da una fonte Tier 1 o 2.

## Licenza

MIT — vedi [LICENSE](LICENSE).

---

*Parole chiave: fiscalità investimenti Italia, tassazione ETF, compensazione
minusvalenze, zainetto fiscale, capital gain 26%, titoli di Stato 12,5%, regime
amministrato, ribilanciamento portafoglio, imposta di successione titoli, Claude
Skill italiana, Italian tax-aware portfolio analysis, Agent Skill finanza.*
