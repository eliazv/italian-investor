# Gerarchia delle fonti

## Quando una claim va verificata

Vanno verificate su fonte corrente, sempre:

- aliquote e basi imponibili;
- qualificazione fiscale di uno strumento (reddito di capitale vs diverso);
- compensabilità delle minusvalenze;
- imposta di successione, esenzioni, costo fiscale dell'erede;
- obblighi dichiarativi (quadro RW, IVAFE, bollo);
- caratteristiche di prodotto (quota titoli di Stato, valuta, holdings, TER).

Non vanno verificate: aritmetica, definizioni di metriche di rischio, dati
forniti dall'utente (che però vanno etichettati come "dichiarati dall'utente").

## Priorità

| Tier | Fonte | Uso |
| --- | --- | --- |
| 1 | Normattiva | testo vigente della legge |
| 1 | Agenzia delle Entrate (circolari, risoluzioni, istruzioni ai modelli) | prassi e interpretazione |
| 1 | MEF / Dipartimento delle Finanze | decreti, elenco White List |
| 1 | CONSOB | natura e rischi degli strumenti |
| 1 | EUR-Lex / ESMA | normativa UE |
| 2 | KID / prospetto dell'emittente | caratteristiche del singolo prodotto |
| 2 | Borsa Italiana (documenti di quotazione, materiale tecnico) | dati strumento |
| 3 | Morningstar, justETF | composizione, esposizioni, costi |
| 3 | documentazione del broker | fiscalità applicata in pratica |
| 4 | blog, forum, Reddit | solo come pista di ricerca, mai come fonte |

**Regola:** per una conclusione fiscale rilevante non accettare una fonte
Tier 3/4 se esiste una Tier 1/2. Una fonte Tier 4 non può mai essere l'unica
citata.

## Punti di ingresso ufficiali

Verificati raggiungibili al 24 agosto 2026. Se un link non risponde, risali al
dominio: sono i domini a essere autorevoli, non i singoli percorsi.

| Fonte | URL |
| --- | --- |
| Normattiva (testo vigente e multivigente) | https://www.normattiva.it/ |
| Agenzia delle Entrate | https://www.agenziaentrate.gov.it/portale/ |
| FiscoOggi (rivista dell'Agenzia delle Entrate) | https://www.fiscooggi.it/ |
| MEF – Dipartimento delle Finanze | https://www.finanze.gov.it/ |
| MEF – Dipartimento del Tesoro, debito pubblico | https://www.dt.mef.gov.it/it/debito_pubblico/ |
| CONSOB | https://www.consob.it/ |
| EUR-Lex | https://eur-lex.europa.eu/homepage.html |
| ESMA | https://www.esma.europa.eu/ |
| Borsa Italiana | https://www.borsaitaliana.it/ |
| Gazzetta Ufficiale | https://www.gazzettaufficiale.it/ |

### Permalink Normattiva

Normattiva espone permalink stabili per URN. Schema:

```
https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:<tipo.atto>:<AAAA-MM-GG>;<numero>
```

Atti che servono più spesso:

| Atto | Permalink |
| --- | --- |
| TUIR – DPR 917/1986 (in vigore fino al 31/12/2026) | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917 |
| Nuovo Testo unico imposte sui redditi – D.Lgs. 117/2026 (applicabile dal 01/01/2027) | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2026-06-19;117 |
| Testo unico successioni e donazioni – D.Lgs. 346/1990 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1990-10-31;346 |

Su Normattiva usa sempre la funzione di **testo multivigente**: serve il testo
vigente alla data rilevante per il caso, non quello di oggi.

## Attenzione: cambio di numerazione dal 2027

Il D.Lgs. 19 giugno 2026 n. 117 ha riordinato la disciplina delle imposte sui
redditi in un nuovo testo unico, pubblicato in Gazzetta Ufficiale il 3 luglio
2026 ed **applicabile dal 1° gennaio 2027**.

Conseguenza pratica per questa skill: i riferimenti "art. 44 TUIR" e
"art. 67-68 TUIR" restano corretti per i periodi d'imposta fino al 2026, ma
dal 2027 va citato l'articolo corrispondente del nuovo testo unico. Prima di
citare un articolo, **verifica quale testo si applica al periodo d'imposta del
caso** e riporta entrambi i riferimenti nel periodo di transizione.

## Cosa citare

Per ogni claim fiscale: `norma o documento + articolo/paragrafo + data`.
"Secondo la normativa italiana" non è una citazione.

Verifica sempre che la fonte sia **vigente alla data dell'analisi**: le pagine
divulgative restano online anche dopo una riforma.

## Fonti in conflitto

Se due fonti si contraddicono (capita anche tra pagine divulgative dello stesso
sito), vince la fonte di tier più alto. Se sono dello stesso tier, riporta
entrambe, non scegliere in silenzio, e abbassa la confidenza a Media.
