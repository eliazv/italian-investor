# Come ragionare sulla fiscalità italiana degli investimenti

Questo file non è un prontuario di aliquote. È lo schema di ragionamento.
I numeri stanno in [regole-correnti.md](regole-correnti.md) e vanno riverificati.

## Lo schema, sempre nello stesso ordine

```
ISIN
 → natura giuridica dello strumento (OICR? titolo? derivato cartolarizzato?)
 → evento fiscale (vendita? cedola? dividendo? rimborso? successione?)
 → categoria di reddito (capitale o diverso)
 → regime del contribuente (amministrato / dichiarativo / gestito)
 → norma applicabile, verificata e citata
```

Saltare un passaggio è il modo tipico in cui un LLM sbaglia. Il nome
commerciale ("ETF governativo", "obbligazionario") non determina nulla.

## Le due categorie che generano quasi tutti gli errori

Il TUIR distingue **redditi di capitale** (art. 44 e segg.) e **redditi
diversi** di natura finanziaria (art. 67-68).

> Nota di vigenza: dal 1° gennaio 2027 si applica il nuovo testo unico
> (D.Lgs. 117/2026) e la numerazione degli articoli cambia. Verifica quale
> testo si applica al periodo d'imposta del caso prima di citare un articolo.
> Vedi [fonti.md](fonti.md).

- I proventi positivi da OICR (fondi, ETF armonizzati) hanno natura di
  **reddito di capitale**.
- Le differenze negative da OICR sono trattate come **minusvalenze**, quindi
  redditi diversi, e alimentano lo "zainetto".

Da qui l'asimmetria: le **minusvalenze pregresse non abbattono la plusvalenza
di un ETF**, perché quest'ultima non è un reddito diverso. Vale invece il
contrario: la minusvalenza generata vendendo un ETF in perdita entra nello
zainetto ed è utilizzabile su redditi diversi futuri.

Cosa genera redditi diversi (quindi compensabili con lo zainetto): azioni,
obbligazioni singole, ETC/ETN, certificates, valute, derivati.

Cosa genera redditi di capitale (non compensabili con lo zainetto): plusvalenze
da OICR/ETF, dividendi, cedole, proventi da fondi.

**Verifica sempre** questa qualificazione sul caso concreto: per strumenti
ibridi o non armonizzati il trattamento cambia. Se lo strumento non è un OICR
armonizzato UE/SEE, fermati e verifica: il regime può essere diverso e
concorrere alla formazione del reddito complessivo.

## Zainetto fiscale

- Le minusvalenze sono utilizzabili entro il **quarto anno successivo** a
  quello di realizzo.
- L'utilizzo avviene su redditi diversi positivi, non su redditi di capitale.
- In regime amministrato lo zainetto è **per singolo intermediario**: minus
  presso il broker A non compensano plus presso il broker B senza trasferimento
  della posizione fiscale.
- Chiedi sempre gli importi **con l'anno di scadenza**, non il totale.

Non trasformare mai il recupero delle minus in una raccomandazione d'acquisto.
È un vincolo da considerare, non un obiettivo di investimento.

## Titoli pubblici agevolati: il 48,08% viene PRIMA della compensazione

Regola verificata il 24/08/2026 sul testo di Normattiva.

L'art. 3 c. 5 del DL 66/2014 (che sostituisce l'ultimo periodo degli artt. 5, 6
e 7 del D.Lgs. 461/1997, cioe' regime dichiarativo, amministrato e gestito)
dispone che «i redditi diversi derivanti dalle obbligazioni e dagli altri titoli
di cui all'articolo 31 del DPR 601/1973 ed equiparati e dalle obbligazioni
emesse dagli Stati inclusi nella lista [White List] ... **sono computati nella
misura del 48,08 per cento dell'ammontare realizzato**».

Conseguenze operative, entrambe facili da sbagliare:

1. **La riduzione precede la compensazione.** Su 1.000 EUR di plusvalenza da BTP
   con 400 EUR di minusvalenze in zainetto: il reddito diverso e' 480,80 EUR,
   da cui si sottraggono le minus, quindi imponibile 80,80 EUR e imposta
   21,01 EUR. Compensare prima e ridurre dopo darebbe 75 EUR: sovrastima
   l'imposta e spreca minusvalenze.
2. **Vale anche per le perdite.** Una minusvalenza di 1.000 EUR su un titolo
   pubblico agevolato entra in zainetto per 480,80 EUR, non per 1.000.

Attenzione a non estendere questa regola agli OICR: e' un meccanismo diverso.

## ETF con componente in titoli di Stato

Non esiste "ETF governativo = 12,5%". Il meccanismo è: la quota di provento
riferibile a titoli pubblici italiani, di Stati White List ed enti assimilati
beneficia di un'imposizione effettiva ridotta, ottenuta applicando l'aliquota
ordinaria a una **frazione** della base imponibile.

Conseguenza operativa: serve la **percentuale agevolata comunicata
dall'emittente o applicata dall'intermediario**. Se non ce l'hai, non stimarla e
non produrre un importo puntuale: il motore restituisce un **intervallo**
(imposta con quota 0% e con quota 100%) e marca `dato_mancante`. Riporta
l'intervallo, mai uno dei due estremi come se fosse il risultato.

Sulle **perdite** di un OICR con componente governativa il motore non applica
alcuna riduzione e segnala `NON VERIFICATO`: non e' stata reperita una fonte
primaria che confermi la riduzione della quota deducibile, e una regola non
verificata non si implementa. L'importo va quindi trattato come limite
superiore.

## Regimi

- **Amministrato**: l'intermediario fa da sostituto, tassa operazione per
  operazione, gestisce lo zainetto. È l'assunzione di default per un retail
  italiano, ma va confermata.
- **Dichiarativo**: il contribuente calcola in dichiarazione (quadro RT);
  cambia la compensazione e i tempi.
- **Gestito**: si tassa il risultato maturato della gestione, non le singole
  operazioni. Le regole di compensazione viste sopra **non si applicano allo
  stesso modo**: se il cliente è in gestito, non riusare l'analisi
  dell'amministrato.

Broker esteri senza sostituto d'imposta implicano dichiarativo, quadro RW e
IVAFE: verifica prima di assumere.

## Successione: quattro problemi distinti

Non comprimerli mai in una frase sola.

1. **Imposta di successione** — dovuta sull'attivo ereditario, con franchigie
   per grado di parentela. Il Testo unico esclude dall'attivo i titoli del
   debito pubblico italiano e i titoli equiparati/di Stati UE-SEE previsti
   dalla norma. Attenzione: "esente da imposta di successione" ≠ "White List";
   sono elenchi e concetti diversi, da verificare strumento per strumento.
2. **Costo fiscalmente riconosciuto all'erede** — l'art. 68 TUIR assume come
   costo il valore dichiarato o definito ai fini dell'imposta di successione;
   per i titoli esenti da tale imposta si assume il valore normale alla data di
   apertura della successione. In pratica si produce spesso uno **step-up del
   costo fiscale**.
3. **Plusvalenza maturata dal de cuius** — per effetto del punto 2 può non
   essere tassata in capo all'erede. Non è però un "affrancamento" e non vale
   indistintamente per ogni strumento e ogni situazione.
4. **Natura dello strumento** — determina sia il punto 1 sia il punto 2.

Quindi: né "in successione si paga tutto", né "in successione gli ETF sono
affrancati". Entrambe le sintesi sono sbagliate. Rispondi separando i quattro
livelli e cita la norma per ciascuno.

La donazione segue regole proprie (continuità del costo del donante nei casi
previsti): non estendere per analogia il ragionamento della successione.

## Impatto fiscale del ribilanciamento

Prima di suggerire una vendita con plusvalenza latente:

1. quantifica l'imposta immediata;
2. confrontala con il beneficio della riallocazione;
3. valuta le alternative: nuovi versamenti, ribilanciamento progressivo,
   vendita selettiva dei lotti con minore gain, uso di flussi (cedole,
   dividendi) invece che di vendite.

Usa `scripts/portfolio.py ribilancia` per confrontare le strategie con i numeri
invece che a intuito.
