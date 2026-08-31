# Come ragionare sulla fiscalità italiana degli investimenti

Questo file non è un prontuario di aliquote. È lo schema di ragionamento.
I numeri stanno in [regole-correnti.md](regole-correnti.md) e vanno riverificati.
Le strategie operative stanno in
[strategie-fiscali.md](strategie-fiscali.md).

## Lo schema, sempre nello stesso ordine

```text
ISIN
 → natura giuridica dello strumento
 → evento fiscale (vendita? cedola? dividendo? rimborso? successione?)
 → categoria di reddito (capitale o diverso)
 → regime del contribuente
 → base fiscale / lotti / valuta
 → broker/intermediario e zainetto disponibile
 → altri attriti fiscali e operativi
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

## Base fiscale: non assumere che PMC significhi sempre la stessa cosa

Una plus/minus corretta richiede prima di sapere **quale costo fiscale** usare.

### Amministrato

Per i redditi diversi ricadenti nel regime del risparmio amministrato, l'art. 6
c.4 del D.Lgs. 461/1997 e la prassi dell'Agenzia richiamano il costo o valore
medio ponderato per ciascuna categoria omogenea di titoli, quote, certificati o
rapporti.

### Dichiarativo

Per le fattispecie indicate dall'art. 67 c.1-bis TUIR fino al 2026, si
considerano ceduti per primi gli strumenti acquisiti più di recente (LIFO).
Una vendita parziale può quindi avere un risultato fiscale diverso da quello
ottenuto applicando un PMC aggregato.

### OICR/ETF

Non riusare meccanicamente la stessa base per la componente positiva e quella
negativa. L'OICR può produrre reddito di capitale e, separatamente, un reddito
diverso negativo fiscalmente rilevante. Prima del calcolo identifica quale
componente stai determinando e la relativa regola.

Se il risultato dipende dai lotti e i lotti non sono disponibili, restituisci
`BASE_FISCALE_NON_VERIFICATA`.

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

### Ordine delle operazioni

In amministrato non assumere che una minus generata e una plus compensabile
nello stesso giorno vengano automaticamente contabilizzate nell'ordine più
favorevole. Verifica con l'intermediario quando la minus entra nello zainetto e
quale ordine contabile viene applicato.

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

## Accumulazione vs distribuzione

Una share class ad accumulazione non va descritta come "dividendi esentasse".
L'assenza di un flusso distribuito periodicamente al partecipante può differire
nel tempo l'imposizione a livello dell'investitore rispetto a una share class a
distribuzione, ma restano possibili ritenute e tax leakage all'interno del
fondo e resta da tassare il provento dell'OICR quando si verifica l'evento
fiscalmente rilevante.

Prima di confrontare due classi verifica che siano comparabili per indice,
domicilio, replica, valuta, TER, tracking difference, spread e liquidità. Il
vantaggio di differimento non va isolato dal resto del prodotto.

## ETC/ETN

Non applicare automaticamente la disciplina degli ETF. Borsa Italiana rimanda
alla sezione `Taxation in Italy` del prospetto/supplemento del singolo ETC/ETN.
Il motore fa hard-stop finché la qualificazione specifica non è stata verificata.

## Commissioni e oneri inerenti

L'art. 68 c.6 include nel costo gli oneri inerenti alla produzione della
plus/minus, compresa l'imposta di successione/donazione ed esclusi gli interessi
passivi. Le istruzioni dell'Agenzia richiamano tra gli esempi anche commissioni
d'intermediazione, spese notarili e tassa sui contratti di borsa.

## Valuta estera

La valuta economica dell'esposizione non coincide necessariamente con la valuta
di quotazione né con il cambio da usare nel calcolo fiscale.

L'art. 9 c.2 TUIR prevede, per i casi cui si applica, che corrispettivi,
proventi, spese e oneri in valuta estera siano valutati al cambio del giorno in
cui sono percepiti o sostenuti, o del giorno antecedente più prossimo e, in
mancanza, al cambio del mese.

Per un calcolo in valuta conserva date, importi originali, valuta e fonte dei
cambi. Non convertire semplicemente il gain finale al cambio corrente.

## Regimi

- **Amministrato**: l'intermediario applica le imposte operazione per operazione
  e gestisce lo zainetto.
- **Dichiarativo**: il contribuente determina i risultati in dichiarazione;
  cambiano tempi, criterio dei lotti nelle fattispecie previste e gestione delle
  compensazioni.
- **Gestito**: si tassa il risultato della gestione secondo regole proprie; non
  riusare meccanicamente le simulazioni dell'amministrato.

## Broker esteri, monitoraggio e redditi esteri

Broker esteri senza sostituto d'imposta possono comportare dichiarativo,
monitoraggio W/RW e IVAFE: verificare il caso concreto. Le istruzioni 730/2026 e
REDDITI PF 2026 dell'Agenzia includono espressamente gli investimenti e le
attività finanziarie estere nei quadri di monitoraggio applicabili.

Per dividendi, interessi e altri redditi di capitale esteri ricevuti direttamente
non assumere una tassazione uniforme. Le istruzioni REDDITI PF 2026 prevedono
per determinate fattispecie un'imposta sostitutiva nella stessa misura della
ritenuta italiana prevista per redditi della stessa natura; ritenuta estera,
convenzione, credito d'imposta e presenza di un intermediario residente possono
cambiare il risultato.

Chiedi almeno Paese fonte, lordo, ritenuta estera, intermediario e natura del
reddito prima di calcolare.

## Trasferimenti tra intermediari

Revoca, chiusura di un rapporto e trasferimento di strumenti/minus richiedono
un controllo documentale. La prassi dell'Agenzia richiama il rilascio di
certificazioni contenenti i dati necessari per utilizzare determinate
minusvalenze in caso di revoca/chiusura del rapporto e per specifiche operazioni
su OICR.

Non spostare virtualmente PMC o zainetto tra broker senza aver verificato la
continuità della base fiscale, la certificazione e il regime di partenza/arrivo.

## Imposta sulle transazioni finanziarie

Per acquisti/vendite di azioni italiane, strumenti partecipativi e derivati
potenzialmente rientranti nella disciplina, verifica l'art. 1 c.491 e seguenti
della L. 228/2012 e la normativa attuativa corrente. Non hardcodare soglie,
aliquote o esenzioni senza verifica aggiornata.

L'imposta, quando applicabile, fa parte del costo della strategia.

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

1. verifica la base fiscale corretta e, se necessario, i lotti;
2. quantifica l'imposta immediata;
3. applica soltanto le minus realmente disponibili per broker/regime/anno;
4. aggiungi bollo/IVAFE, ritenute estere non recuperabili, imposte di
   transazione, commissioni, spread e cambio quando applicabili;
5. confronta il beneficio della riallocazione con il tax drag totale;
6. valuta nuovi versamenti, cash flow, ribilanciamento progressivo e strategie
   multi-ISIN soltanto dopo averne verificato la base fiscale;
7. separa il risparmio d'imposta dal semplice **differimento** dell'imposta.

Usa `scripts/portfolio.py ribilancia` con `--zainetto-csv` e `--anno-fiscale`
quando i dati sono disponibili, sapendo che il motore non può correggere un PMC
che non rappresenta la base fiscale applicabile.
