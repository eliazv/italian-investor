# Eventi fiscali: non classificare uno strumento una volta sola

Una stessa posizione può generare categorie reddituali diverse a seconda
dell'**evento**. La skill deve quindi ragionare almeno con la coppia:

```text
strumento + evento
```

non con il solo `tipo` dello strumento.

Verifica strutturale aggiornata al **31/08/2026**. Aliquote e dettagli applicativi
restano soggetti alla regola generale di verifica su fonte primaria corrente.

## Matrice minima

| Strumento | Evento | Categoria di riferimento | Nota |
| --- | --- | --- | --- |
| Azione | vendita con gain/loss | reddito diverso | art. 67 TUIR per le fattispecie finanziarie coperte |
| Azione | dividendo | reddito di capitale | ritenuta sui dividendi; verificare fonte/qualifica del percettore |
| Obbligazione corporate | vendita con gain/loss | reddito diverso | separare il capital gain dalla cedola |
| Obbligazione corporate | cedola/interesse/premio | reddito di capitale | DL 66/2014 art. 3 porta la misura ordinaria al 26% nei casi coperti |
| Titolo pubblico agevolato | vendita con gain/loss | reddito diverso agevolato | 48,08% prima della compensazione nei regimi richiamati |
| Titolo pubblico agevolato | cedola/interesse/premio | reddito di capitale agevolato | non confondere il meccanismo del capital gain con quello del provento |
| ETF/OICR armonizzato | cessione/rimborso con differenza positiva | reddito di capitale | non compensabile con zainetto |
| ETF/OICR armonizzato | differenza negativa | reddito diverso | quota pubblica della perdita ridotta secondo la disciplina applicabile |
| ETF/OICR armonizzato | distribuzione | reddito di capitale | eventuale quota titoli pubblici incide sul carico effettivo |

Questa tabella è uno **schema di routing**. Non sostituisce la verifica del
prodotto, del regime e della norma vigente.

## Dividendi

Per una persona fisica residente che detiene partecipazioni fuori dall'attività
d'impresa, l'art. 27 DPR 600/1973 prevede, nelle fattispecie coperte, una
ritenuta del 26% sugli utili corrisposti.

Per dividendi esteri non comprimere il problema in `lordo × 26%` o
`netto × 26%`: prima verifica ritenuta alla fonte estera, convenzione,
intermediario che interviene nell'incasso ed eventuale credito/opzione.

`scripts/event_tax.py` fa quindi hard-stop quando viene indicata una ritenuta
estera, invece di inventare il recupero fiscale.

## Obbligazioni: cedola != capital gain

Il DL 66/2014 art. 3 distingue chiaramente i redditi di capitale ex art. 44 TUIR
(interessi, premi e altri proventi) dai redditi diversi finanziari ex art. 67.
Per questo una classificazione generica come:

```text
obbligazione = reddito diverso
```

è incompleta. È corretta per il capital gain da cessione nei casi coperti, non
per la cedola/interesse.

Per i titoli pubblici agevolati verifica separatamente:

1. tassazione del provento periodico;
2. riduzione al 48,08% del reddito diverso da cessione nei regimi richiamati;
3. ammissibilità del titolo alla disciplina agevolata.

Non descrivere la cedola come se fosse un capital gain ridotto al 48,08%: il
risultato economico può coincidere con il 12,5% ma il percorso normativo è
diverso.

## ETF/OICR: distribuzione, cessione e perdita

I proventi da partecipazione a OICR rientrano tra i redditi di capitale; la
disciplina considera sia proventi distribuiti sia proventi realizzati in sede di
rimborso/cessione/liquidazione secondo le regole applicabili al prodotto.

La componente riferibile a titoli pubblici agevolati richiede la percentuale
fiscalmente rilevante comunicata/applicabile al fondo. Non sostituirla con la
fotografia delle holdings correnti.

Quindi:

- `distribuzione ETF` -> `scripts/event_tax.py`;
- `vendita/rimborso ETF` -> `scripts/tax_engine.py`;
- quota pubblica ignota -> scenario, non numero puntuale;
- OICR non armonizzato -> hard-stop e verifica specifica.

## Certificates, ETC/ETN e strumenti ibridi

Non estendere automaticamente una classificazione da un evento all'altro.

- **Certificates**: il trattamento dei flussi dipende dalla struttura e dal
  payoff; `event_tax.py` blocca il provento periodico finché non viene verificato
  il prodotto.
- **ETC/ETN**: mantenere il controllo sul prospetto/supplemento e sulla sezione
  fiscale italiana.
- **Strumenti ibridi**: partire dalla natura giuridica e dal singolo flusso,
  non dal nome commerciale.

## Sequenza operativa

Prima di calcolare una tassa:

```text
ISIN
 -> natura giuridica
 -> evento (vendita / rimborso / cedola / dividendo / distribuzione / interesse)
 -> categoria reddituale
 -> eventuale componente agevolata
 -> regime/intermediario
 -> base fiscale o importo lordo rilevante
 -> norma corrente
 -> calcolo
```

Se l'evento non è esplicitamente supportato, restituisci
`EVENTO_FISCALE_NON_VERIFICATO` invece di riciclare la classificazione della
vendita.

## Fonti primarie da verificare

- DPR 917/1986, artt. 44, 45, 67 e 68 per i periodi d'imposta fino al 2026;
- DPR 600/1973, art. 27 per i dividendi e art. 26-quinquies per OICR nei casi
  applicabili;
- DL 66/2014, art. 3 per aliquota ordinaria, eccezioni titoli pubblici e OICR;
- Agenzia delle Entrate, Circolare 19/E del 27/06/2014 per la componente OICR
  riferibile a titoli pubblici;
- istruzioni dichiarative correnti per redditi percepiti senza intermediario
  residente e redditi esteri.
