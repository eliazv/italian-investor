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

Testo verificato il 24/08/2026 sul TUIR ufficiale pubblicato dall'Agenzia delle
Entrate:

- **art. 44 c.1 lett. g)**: sono redditi di capitale «i proventi derivanti dalla
  gestione, nell'interesse collettivo di pluralita' di soggetti, di masse
  patrimoniali costituite con somme di denaro e beni affidati da terzi o
  provenienti dai relativi investimenti».
- **art. 45 c.1**: nei redditi di cui alla lett. g) «e' compresa anche la
  differenza tra la somma percepita o il valore normale dei beni ricevuti alla
  scadenza e il prezzo di emissione o la somma impiegata, apportata o affidata
  in gestione». E' qui che il **guadagno** su un OICR diventa reddito di
  capitale.
- **art. 67 c.1 lett. c-ter)**: sono redditi diversi le plusvalenze realizzate
  «mediante cessione a titolo oneroso ovvero rimborso di titoli non
  rappresentativi di merci, di certificati di massa, di valute estere [...] e di
  quote di partecipazione ad organismi d'investimento collettivo».
- **art. 68 c.5**: le plusvalenze delle lett. c-bis) e c-ter) «sono sommate
  algebricamente alle relative minusvalenze, nonche' ai redditi ed alle perdite
  di cui alla lettera c-quater) e alle plusvalenze ed altri proventi di cui alla
  lettera c-quinquies)»; l'eccedenza negativa «puo' essere portata in deduzione,
  fino a concorrenza, dalle plusvalenze e dagli altri redditi dei periodi
  d'imposta successivi **ma non oltre il quarto**, a condizione che sia indicata
  nella dichiarazione dei redditi relativa al periodo d'imposta» di realizzo.

Messi in fila: la compensazione dell'art. 68 c.5 opera **solo** tra le lettere
c-bis), c-ter), c-quater) e c-quinquies) dell'art. 67, cioe' tra redditi
diversi. Il guadagno su un OICR non e' li' dentro: e' reddito di capitale per
gli artt. 44 e 45. Ecco perche' lo zainetto non lo tocca, mentre la perdita
sullo stesso ETF rientra nella lett. c-ter) e lo alimenta.

L'aliquota ordinaria del 26% e' fissata dall'art. 3 c.1 del DL 66/2014, in
vigore dal 1o luglio 2014, e si applica sia ai redditi di capitale dell'art. 44
sia ai redditi diversi dell'art. 67 c.1 lett. da c-bis) a c-quinquies).

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

- Le minusvalenze sono utilizzabili entro il **quarto** periodo d'imposta
  successivo a quello di realizzo (art. 68 c.5, verificato il 24/08/2026), a
  condizione che siano indicate nella dichiarazione dell'anno di realizzo.
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

Attenzione a non estendere automaticamente questa regola agli OICR: il
meccanismo e la fonte applicativa sono distinti.

## ETF con componente in titoli di Stato

Non esiste "ETF governativo = 12,5%". Il meccanismo è: la quota di provento
riferibile a titoli pubblici italiani, di Stati White List ed enti assimilati
beneficia di un'imposizione effettiva ridotta, ottenuta applicando l'aliquota
ordinaria a una **frazione** della base imponibile.

La **Circolare Agenzia delle Entrate 19/E del 27/06/2014** chiarisce entrambi i
lati del meccanismo per gli OICR che investono in titoli pubblici:

- sui proventi, la quota riferibile ai titoli pubblici e' assoggettata al 26%
  limitatamente al **48,08%** del relativo ammontare;
- analogamente, le perdite riferibili ai titoli pubblici possono essere portate
  in deduzione per un importo **ridotto del 51,92%**, quindi rilevano al 48,08%.

La prassi e' disponibile nella Documentazione Economica e Finanziaria del MEF:
`https://def.finanze.it/DocTribFrontend/getPrassiDetail.do?id=%7B7953D773-A884-4630-A7EB-EF5187839207%7D`.

Conseguenza operativa: serve la **percentuale agevolata comunicata
dall'emittente o applicata dall'intermediario**. Per una perdita `L` e una quota
pubblica `q`, la minusvalenza fiscalmente rilevante e':

`L * ((1 - q) + q * 0,4808)`.

Se `quota_stato` non e' disponibile, non produrre un importo puntuale: il motore
restituisce un intervallo tra perdita interamente ordinaria (quota 0%) e perdita
interamente riferibile a titoli pubblici (quota 100%), marca `dato_mancante` e
richiede la percentuale.

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
