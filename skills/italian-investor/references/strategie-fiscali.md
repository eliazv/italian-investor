# Strategie fiscali e controlli operativi

Questo file raccoglie euristiche di pianificazione **tax-aware** e controlli che
vanno eseguiti prima di proporre un'operazione. Non trasforma una strategia in
una regola fiscale: aliquote, basi imponibili, esenzioni e qualificazione dello
strumento vanno sempre verificate secondo [fonti.md](fonti.md).

Ultima revisione della struttura: **31/08/2026**.

## 1. Prima del PMC: determinare la base fiscale corretta

Non usare un `pmc` fornito dal broker come se fosse automaticamente la base
fiscale valida per qualunque regime ed evento.

### Regime amministrato

Per i redditi diversi ricadenti nel regime del risparmio amministrato, l'art. 6
c.4 del D.Lgs. 461/1997 usa, per pluralità di titoli, quote, certificati o
rapporti appartenenti a categorie omogenee, il **costo o valore medio ponderato**
della relativa categoria. La prassi dell'Agenzia delle Entrate richiama
esplicitamente questo criterio.

### Regime dichiarativo

Per le fattispecie indicate dall'art. 67 c.1-bis TUIR applicabile fino al 2026,
si considerano ceduti per primi gli strumenti acquisiti più di recente
(**LIFO**). Questo può cambiare il risultato fiscale di una vendita parziale
rispetto a un semplice PMC.

Non estendere il LIFO meccanicamente a ogni componente fiscale di ETF/OICR: la
loro tassazione può generare contemporaneamente redditi di capitale e redditi
diversi secondo regole proprie. Prima del calcolo identifica l'evento e la
categoria reddituale che stai determinando.

### Regola operativa

Un calcolo basato su `pmc` è azionabile soltanto quando è stato verificato che
quel valore rappresenta la base fiscale corretta per **regime, strumento ed
evento**. Se in dichiarativo una vendita parziale dipende dai lotti, chiedi
almeno:

```text
data_acquisto,quantita,costo_unitario,valuta,costi
```

Se i lotti mancano, restituisci `BASE_FISCALE_NON_VERIFICATA` invece di stimare.

## 2. ETF ad accumulazione e a distribuzione

L'accumulazione può differire nel tempo l'imposizione a livello dell'investitore
rispetto a un prodotto che distribuisce periodicamente proventi, perché non
produce lo stesso flusso distribuito al partecipante. Non descriverla però come
"assenza di tasse sui dividendi": all'interno del fondo possono esistere
ritenute, imposte e altri tax leakage, e il provento dell'OICR resta soggetto al
trattamento fiscale applicabile quando si verifica l'evento imponibile.

Quando confronti share class ad accumulazione e distribuzione separa:

1. stessa esposizione, indice, domicilio e struttura del fondo;
2. trattamento fiscale del provento per il residente italiano;
3. tax leakage interno al fondo, se documentabile;
4. necessità di cash flow dell'investitore;
5. TER, tracking difference, spread e liquidità.

Non scegliere la classe ad accumulazione **solo** per motivi fiscali se cambia
materialmente il prodotto o il profilo di rischio.

## 3. Strategia multi-ISIN / secondo emittente

Quando una posizione ha una forte plusvalenza latente, può essere utile valutare
se destinare i nuovi acquisti a uno strumento economicamente equivalente ma con
ISIN differente, invece di continuare ad aumentare la stessa linea.

È una **strategia candidata**, non una garanzia fiscale. Prima di stimarne il
vantaggio verifica:

- che i due strumenti siano davvero sostituibili per esposizione, rischio,
  costi, replica, domicilio e liquidità;
- come il regime applicabile determina il costo fiscale delle due posizioni;
- come l'intermediario tratta categorie omogenee e basi di carico;
- che la futura vendita della linea scelta produca davvero la base imponibile
  prevista.

Non scrivere mai "ISIN diverso = PMC fiscalmente separato garantito" senza aver
verificato il regime e la contabilizzazione applicabile.

## 4. Ordine delle operazioni e minusvalenze

In regime amministrato una minusvalenza deve essere fiscalmente disponibile
quando viene utilizzata contro un successivo reddito diverso compensabile.
Quindi l'ordine delle operazioni può essere rilevante.

Prima di proporre una sequenza `realizza minus → realizza gain compensabile`:

1. verifica che la minus sia della categoria utilizzabile;
2. verifica broker, rapporto e scadenza;
3. verifica quando l'intermediario la rende disponibile nello zainetto;
4. verifica il trattamento delle operazioni eseguite nello stesso giorno e le
   relative date contabili.

Non assumere che due eseguiti nello stesso giorno vengano contabilizzati
nell'ordine desiderato.

## 5. Trasferimenti tra broker e certificazioni

Un trasferimento di strumenti o la chiusura/revoca di un rapporto non va
trattato automaticamente né come vendita imponibile né come trasferimento
perfetto di PMC e zainetto.

La disciplina del risparmio amministrato prevede certificazioni in specifici
casi; la prassi dell'Agenzia richiama il rilascio dei dati necessari per la
deduzione di minusvalenze in caso di revoca/chiusura del rapporto e per alcune
operazioni su OICR.

Per ogni trasferimento verifica separatamente:

```text
strumenti trasferiti
base fiscale comunicata al nuovo intermediario
minus certificate
anno/scadenza delle minus
regime vecchio e nuovo
continuita o chiusura del rapporto
```

Non spostare virtualmente lo zainetto da un broker all'altro senza una
certificazione o una regola verificata applicabile al caso.

## 6. Valuta estera: esposizione e valuta fiscale sono problemi diversi

`valuta_esposizione` descrive il rischio economico dei sottostanti; non basta per
calcolare la fiscalità di un'operazione.

L'art. 9 c.2 TUIR, per i casi cui si applica, richiede di valutare corrispettivi,
proventi, spese e oneri in valuta estera al cambio del giorno in cui sono stati
percepiti o sostenuti, o del giorno antecedente più prossimo e, in mancanza, al
cambio del mese.

Per strumenti o flussi non denominati in euro conserva quindi almeno:

```text
valuta_quotazione,data_acquisto,data_vendita,cambio_acquisto,cambio_vendita,fonte_cambio
```

Non calcolare la plusvalenza fiscale convertendo semplicemente il gain finale al
cambio odierno. E non confondere la valuta di quotazione con la valuta economica
dell'investimento.

## 7. Broker esteri, monitoraggio e redditi di fonte estera

Un broker estero può cambiare sia gli adempimenti sia il momento in cui le
imposte vengono liquidate. Le istruzioni 730/REDDITI 2026 dell'Agenzia prevedono
il quadro W/RW per il monitoraggio degli investimenti e delle attività
finanziarie estere e per IVAFE nei casi applicabili.

Per dividendi, interessi e altri redditi di capitale di fonte estera ricevuti
senza intermediario residente non applicare automaticamente "26% sul netto" o
"26% sul lordo". Prima ricostruisci:

```text
paese_fonte
importo_lordo
ritenuta_estera
convenzione_applicabile
intermediario_residente_si_no
categoria_reddito
credito_imposta_o_imposta_sostitutiva_da_verificare
```

Le istruzioni REDDITI 2026 prevedono, per determinati redditi di capitale di
fonte estera percepiti direttamente, un'imposizione sostitutiva nella stessa
misura della ritenuta italiana prevista per redditi della stessa natura. Il
credito per imposte estere e le eventuali opzioni dipendono però dal caso:
**hard-stop** se mancano fonte, Paese e modalità di incasso.

## 8. Imposta sulle transazioni finanziarie (Tobin tax)

Prima di proporre compravendite frequenti di azioni italiane, strumenti
partecipativi o derivati collegati, verifica se l'operazione rientra
nell'imposta sulle transazioni finanziarie prevista dall'art. 1 c.491 e seguenti
della L. 228/2012.

Non hardcodare nella strategia aliquote, soglie, capitalizzazioni o esenzioni:
sono dati correnti da verificare. Se applicabile, l'imposta entra nel costo totale
della strategia e può rendere inefficiente un tax-loss harvesting marginale.

## 9. Tax drag totale, non solo imposta sulla plusvalenza

Quando confronti due strategie calcola o almeno elenca separatamente:

```text
imposta immediata su proventi/plus
+ bollo o IVAFE se applicabili
+ ritenute estere non recuperabili
+ imposta sulle transazioni se applicabile
+ commissioni broker
+ spread bid/ask
+ costi di cambio
+ altri oneri inerenti verificati
= costo fiscale/operativo immediato
```

Poi separa il **timing** dell'imposta: pagare la stessa imposta più tardi può
avere un valore economico perché il capitale resta investito più a lungo. Non
trasformare però il differimento in "risparmio fiscale" senza distinguere valore
attuale e imposta finale attesa.

## 10. Ordine preferenziale per un ribilanciamento tax-aware

Quando più soluzioni raggiungono lo stesso obiettivo di rischio, valuta in questo
ordine, senza trasformarlo in una prescrizione automatica:

1. nuovi versamenti verso le componenti sottopesate;
2. flussi di cassa/distribuzioni già disponibili;
3. ribilanciamento progressivo;
4. vendita di posizioni con perdita o gain fiscale ridotto, se coerente con il
   portafoglio;
5. vendita di posizioni con forte gain latente solo dopo aver quantificato il
   tax drag e il beneficio della riallocazione.

## Hard-stop specifici

Non usare come scorciatoie le seguenti frasi:

- "ETF sintetico: la tassazione dipende dal collateral" — va verificata la
  disciplina fiscale del fondo/prodotto, non dedotta dal paniere collaterale;
- "ETF governativo = tutto al 12,5%" — serve la quota fiscalmente agevolata
  applicabile;
- "ISIN diverso = costo fiscale separato garantito" — verificare regime e
  contabilizzazione;
- "broker estero = basta pagare IVAFE" — possono esserci monitoraggio,
  dichiarazione dei redditi e altri adempimenti;
- "minus e plus nello stesso giorno si compensano sicuramente" — verificare la
  contabilizzazione dell'intermediario;
- "accumulazione = dividendi esentasse" — è una formulazione scorretta.

## Fonti primarie da aprire prima di rendere azionabile una conclusione

- DPR 917/1986 (TUIR), artt. 9, 44-45, 67-68, testo multivigente su Normattiva;
- D.Lgs. 461/1997, in particolare artt. 5-7 per i regimi di tassazione delle
  plus/minus finanziarie;
- Agenzia delle Entrate / Documentazione Economica e Finanziaria, circolari sul
  risparmio amministrato e sugli OICR;
- istruzioni 730/2026 e REDDITI PF 2026 per quadri W/RW, T e RM;
- L. 228/2012 art. 1 c.491 e seguenti per l'imposta sulle transazioni
  finanziarie;
- KID/prospetto e documentazione dell'intermediario per il singolo prodotto e
  per le regole operative del rapporto.
