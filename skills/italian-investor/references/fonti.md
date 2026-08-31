# Gerarchia delle fonti

## Quando una claim va verificata

Vanno verificate su fonte corrente, sempre:

- aliquote e basi imponibili;
- criterio di determinazione del costo/base fiscale e ordine dei lotti;
- qualificazione fiscale di uno strumento (reddito di capitale vs diverso);
- compensabilità delle minusvalenze;
- imposta di successione, esenzioni, costo fiscale dell'erede;
- obblighi dichiarativi (quadro W/RW, IVAFE, bollo);
- ritenute estere, convenzioni e credito per imposte estere;
- imposta sulle transazioni finanziarie, soglie ed esenzioni;
- caratteristiche di prodotto (quota titoli di Stato, valuta, holdings, TER).

Non vanno verificate: aritmetica, definizioni di metriche di rischio, dati
forniti dall'utente (che però vanno etichettati come "dichiarati dall'utente").

## Priorità

| Tier | Fonte | Uso |
| --- | --- | --- |
| 1 | Normattiva | testo vigente della legge |
| 1 | Agenzia delle Entrate (circolari, risoluzioni, istruzioni ai modelli) | prassi e interpretazione |
| 1 | MEF / Dipartimento delle Finanze | decreti, prassi archiviata, elenco White List |
| 1 | CONSOB | natura e rischi degli strumenti |
| 1 | EUR-Lex / ESMA | normativa UE |
| 2 | KID / prospetto dell'emittente | caratteristiche del singolo prodotto |
| 2 | Borsa Italiana (documenti di quotazione, materiale tecnico) | dati strumento |
| 3 | Morningstar, justETF | composizione, esposizioni, costi; pista da confermare per claim fiscali |
| 3 | documentazione del broker | meccanica operativa del rapporto, rendiconti e certificazioni; non può sostituire la norma |
| 4 | blog, forum, Reddit, video divulgativi | solo come pista di ricerca, mai come fonte fiscale finale |

**Regola:** per una conclusione fiscale rilevante non accettare una fonte
Tier 3/4 se esiste una Tier 1/2. Una fonte Tier 4 non può mai essere l'unica
citata.

La documentazione del broker è invece spesso necessaria per un fatto
**operativo** che la legge non descrive nel dettaglio: per esempio quando una
minus viene resa disponibile, come vengono riportate le certificazioni, quale
PMC fiscale espone l'interfaccia o come viene gestita una sequenza di eseguiti.
Etichetta questi fatti come `dato intermediario`, non come `legge`.

## Punti di ingresso ufficiali

Verificati raggiungibili al 31 agosto 2026. Se un link non risponde, risali al
dominio: sono i domini a essere autorevoli, non i singoli percorsi.

| Fonte | URL |
| --- | --- |
| Normattiva (testo vigente e multivigente) | https://www.normattiva.it/ |
| Agenzia delle Entrate | https://www.agenziaentrate.gov.it/portale/ |
| Dichiarazione precompilata / istruzioni quadri 2026 | https://infoprecompilata.agenziaentrate.gov.it/ |
| FiscoOggi (rivista dell'Agenzia delle Entrate) | https://www.fiscooggi.it/ |
| MEF – Dipartimento delle Finanze / Documentazione Economica e Finanziaria | https://def.finanze.it/ |
| MEF – Dipartimento del Tesoro, debito pubblico | https://www.dt.mef.gov.it/it/debito_pubblico/ |
| CONSOB | https://www.consob.it/ |
| EUR-Lex | https://eur-lex.europa.eu/homepage.html |
| ESMA | https://www.esma.europa.eu/ |
| Borsa Italiana | https://www.borsaitaliana.it/ |
| Gazzetta Ufficiale | https://www.gazzettaufficiale.it/ |

### Permalink Normattiva

Normattiva espone permalink stabili per URN. Schema:

```text
https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:<tipo.atto>:<AAAA-MM-GG>;<numero>
```

Atti che servono più spesso:

| Atto | Uso principale | Permalink / punto di ingresso |
| --- | --- | --- |
| TUIR – DPR 917/1986 (in vigore fino al 31/12/2026) | redditi di capitale/diversi, valuta, costo, LIFO | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917 |
| Nuovo Testo unico imposte sui redditi – D.Lgs. 117/2026 (applicabile dal 01/01/2027) | disciplina dal 2027 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2026-06-19;117 |
| D.Lgs. 461/1997 | dichiarativo/amministrato/gestito, costo medio, certificazioni minus | cercare il testo multivigente su Normattiva per `decreto legislativo 21 novembre 1997 n. 461` |
| DPR 600/1973 | ritenute e disciplina di diversi redditi finanziari/OICR | cercare il testo multivigente su Normattiva |
| DL 66/2014 art. 3 | aliquota ordinaria e titoli pubblici agevolati | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2014-04-24;66 |
| DL 201/2011 art. 19 | bollo/IVAFE e relative modifiche | cercare il testo multivigente su Normattiva |
| L. 228/2012 art. 1 c.491 e segg. | imposta sulle transazioni finanziarie | cercare il testo multivigente su Normattiva |
| Testo unico successioni e donazioni – D.Lgs. 346/1990 | successione/donazione | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1990-10-31;346 |

Su Normattiva usa sempre la funzione di **testo multivigente**: serve il testo
vigente alla data rilevante per il caso, non quello di oggi.

## Istruzioni dichiarative: usare l'anno giusto

Per broker esteri, redditi di fonte estera, monitoraggio e IVAFE, le istruzioni
dei modelli sono una fonte primaria operativa fondamentale. Non usare le
istruzioni 2026 per un diverso anno d'imposta senza verificare la
corrispondenza.

Per il 2026 sono punti d'ingresso utili:

- `Quadro W` del 730/2026 — investimenti e attività finanziarie estere,
  monitoraggio e IVAFE;
- `Quadro RW` di REDDITI PF 2026 — monitoraggio estero e IVAFE;
- `Quadro RM` di REDDITI PF 2026 — tra l'altro redditi di capitale di fonte
  estera percepiti direttamente;
- `Quadro T` / quadri finanziari applicabili — plusvalenze di natura
  finanziaria e fattispecie specifiche.

Le istruzioni indicano **dove e come dichiarare** una fattispecie; per dedurre
la regola sostanziale risali anche alla norma che esse citano.

## Fonti per il costo fiscale

Quando una vendita dipende dalla base fiscale, verifica almeno:

1. testo vigente dell'art. 67 c.1-bis TUIR per l'ordine dei lotti nelle
   fattispecie cui si applica;
2. D.Lgs. 461/1997 art. 6 per il risparmio amministrato;
3. circolari/risoluzioni dell'Agenzia che chiariscono costo medio,
   certificazioni e casi OICR;
4. rendiconto o documentazione del broker soltanto per verificare i dati
   concretamente applicati al rapporto.

Non dedurre il criterio dal semplice campo `PMC` mostrato nell'app del broker.

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

Per le strategie, cita separatamente:

- la **regola fiscale** che rende possibile/impossibile l'effetto;
- il **dato del prodotto/intermediario**;
- l'**inferenza strategica** del modello.

## Fonti in conflitto

Se due fonti si contraddicono (capita anche tra pagine divulgative dello stesso
sito), vince la fonte di tier più alto. Se sono dello stesso tier, riporta
entrambe, non scegliere in silenzio, e abbassa la confidenza a Media.
