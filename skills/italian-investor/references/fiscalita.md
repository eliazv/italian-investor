# Come ragionare sulla fiscalità italiana degli investimenti

Questo file non è un prontuario di aliquote. È lo schema di ragionamento.
I numeri stanno in [regole-correnti.md](regole-correnti.md) e vanno riverificati.

## Lo schema, sempre nello stesso ordine

```text
ISIN
 → natura giuridica dello strumento
 → evento fiscale (vendita? cedola? dividendo? rimborso? successione?)
 → categoria di reddito (capitale o diverso)
 → regime del contribuente
 → broker/intermediario e zainetto disponibile
 → norma applicabile, verificata e citata
```

Saltare un passaggio è il modo tipico in cui un LLM sbaglia. Il nome
commerciale non determina il trattamento fiscale.

## Redditi di capitale e redditi diversi

Il TUIR distingue redditi di capitale (art. 44 e segg.) e redditi diversi di
natura finanziaria (art. 67-68, per i periodi d'imposta fino al 2026).

Testo verificato il 24/08/2026:

- art. 44 c.1 lett. g): proventi della gestione collettiva come redditi di capitale;
- art. 45 c.1: comprende anche la differenza positiva tra quanto percepito e la somma impiegata/affidata;
- art. 67 c.1 lett. c-ter): include cessioni/rimborsi di quote OICR tra i redditi diversi;
- art. 68 c.5: compensazione tra le categorie di redditi diversi indicate dalla norma e riporto dell'eccedenza non oltre il quarto periodo d'imposta successivo.

Conseguenza operativa: il guadagno di un OICR/ETF armonizzato è reddito di
capitale e non viene abbattuto dallo zainetto; la differenza negativa può invece
alimentare lo zainetto come reddito diverso nei limiti fiscalmente rilevanti.

## Zainetto fiscale: broker, regime e scadenza

Per un'analisi azionabile non trattare lo zainetto come un solo numero. Per ogni
lotto conserva almeno:

```text
broker,regime,anno_realizzo,importo
```

La scadenza è il quarto periodo d'imposta successivo all'anno di realizzo.
`scripts/zainetto.py` calcola lo stato dei lotti e simula la compensazione.

- In **regime amministrato**, una vendita usa soltanto le minus disponibili
  presso lo stesso intermediario, salvo trasferimenti/certificazioni fiscali da
  gestire come evento separato e documentato.
- In **regime dichiarativo**, il simulatore può aggregare i lotti marcati
  dichiarativo ai fini della simulazione annuale.
- Il simulatore usa prima i lotti con scadenza più vicina per non perderli. È
  una strategia di simulazione, non una regola imposta al broker sull'ordine
  contabile delle compensazioni.

Chiedi sempre anno di realizzo/scadenza, broker e regime, non soltanto il totale.

## Titoli pubblici agevolati: 48,08% prima della compensazione

Regola verificata il 24/08/2026 sul testo di Normattiva.

L'art. 3 c.5 del DL 66/2014 dispone che i redditi diversi derivanti dai titoli
pubblici agevolati siano computati nella misura del 48,08% dell'ammontare
realizzato nei regimi richiamati dalla norma.

Conseguenze:

1. su 1.000 EUR di gain BTP con 400 EUR di minus: 480,80 - 400 = 80,80 EUR imponibili;
2. una perdita di 1.000 EUR sul titolo pubblico genera 480,80 EUR di minus fiscalmente rilevante.

Non applicare la stessa meccanica agli OICR: per essi vale la disciplina della
quota riferibile ai titoli pubblici.

## OICR con componente in titoli pubblici

Non esiste "ETF governativo = 12,5%". Serve la quota comunicata
dall'emittente/intermediario.

La Circolare Agenzia delle Entrate 19/E del 27/06/2014 chiarisce anche il lato
negativo: la parte della perdita riferibile ai titoli pubblici è ridotta del
51,92%, quindi rileva al 48,08%. Il motore applica:

```text
perdita_rilevante = perdita * ((1 - quota_stato) + quota_stato * 0,4808)
```

Se `quota_stato` manca, non viene inventata: il motore restituisce uno scenario
min/max sia per l'imposta sia per la minusvalenza deducibile.

## ETC/ETN

Non applicare automaticamente la disciplina degli ETF. Borsa Italiana rimanda
alla sezione `Taxation in Italy` del prospetto/supplemento del singolo ETC/ETN.
Il motore fa hard-stop finché la qualificazione specifica non è stata verificata.

## Commissioni e oneri inerenti

L'art. 68 c.6 include nel costo gli oneri inerenti alla produzione della
plus/minus, compresa l'imposta di successione/donazione ed esclusi gli interessi
passivi. Le istruzioni dell'Agenzia richiamano tra gli esempi anche commissioni
d'intermediazione, spese notarili e tassa sui contratti di borsa.

## Regimi

- **Amministrato**: l'intermediario applica le imposte operazione per operazione
  e gestisce lo zainetto.
- **Dichiarativo**: il contribuente determina i risultati in dichiarazione;
  cambiano tempi e gestione delle compensazioni.
- **Gestito**: si tassa il risultato della gestione secondo regole proprie; non
  riusare meccanicamente le simulazioni dell'amministrato.

Broker esteri senza sostituto d'imposta possono comportare dichiarativo, RW e
IVAFE: verificare il caso concreto.

## Successione: separare quattro problemi

1. **Attivo ereditario** — il D.Lgs. 346/1990 art. 12 esclude, tra gli altri, i
   titoli del debito pubblico italiano e i corrispondenti titoli UE/SEE indicati
   dalla norma. Non confondere questa esclusione con la White List fiscale.
2. **Imposta di successione** — dipende da bene, rapporto di parentela,
   franchigie e altre regole vigenti.
3. **Costo fiscalmente riconosciuto all'erede** — per le fattispecie coperte
   dall'art. 68 c.6 si assume il valore definito o, in mancanza, dichiarato; per
   titoli esenti dall'imposta di successione, il valore normale alla data di
   apertura. Gli oneri inerenti documentabili possono aumentare il costo.
4. **Futura tassazione** — dipende dalla natura dello strumento e dall'evento
   futuro; non dedurla dal solo fatto che il bene sia stato ereditato.

`scripts/successione.py` implementa in modo deterministico soltanto il punto 3
per azioni/titoli/obbligazioni coperti direttamente dalla regola. ETF/OICR e
strumenti ibridi richiedono una disciplina specifica: il helper non li assimila
per analogia.

La donazione segue regole proprie: non estendere il ragionamento della
successione.

## Impatto fiscale del ribilanciamento

Prima di suggerire una vendita con gain latente:

1. quantifica l'imposta immediata;
2. applica soltanto le minus realmente disponibili per broker/regime/anno;
3. confronta il beneficio della riallocazione con il tax drag;
4. valuta nuovi versamenti, ribilanciamento progressivo e scelta dei lotti;
5. verifica commissioni, spread e vincoli operativi.

Usa `scripts/portfolio.py ribilancia` con `--zainetto-csv` e `--anno-fiscale`
quando i dati sono disponibili.
