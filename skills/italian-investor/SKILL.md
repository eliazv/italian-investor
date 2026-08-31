---
name: italian-investor
description: Analisi di portafoglio tax-aware per residenti fiscali italiani. Da usare quando si analizza un portafoglio (ETF, azioni, BTP, obbligazioni, certificates), si simula una vendita o un ribilanciamento, si ragiona su minusvalenze/zainetto fiscale, successione o imposte su strumenti finanziari italiani. Impone verifica su fonti primarie invece che memoria del modello.
---

# Italian Investor

Analisi di portafoglio per un residente fiscale italiano, con la fiscalità
trattata come **dato da verificare**, non come conoscenza del modello.

La skill contiene una procedura anti-allucinazione e piccoli motori Python
deterministici. Il modello interpreta e spiega; non deve inventare norme,
classificazioni di strumenti o aritmetica fiscale.

## Regola zero

Non usare mai la memoria interna del modello per:

- aliquote vigenti e basi imponibili;
- trattamento fiscale di uno strumento o di uno specifico evento;
- compensabilità e scadenza delle minusvalenze;
- criterio di determinazione della base fiscale/ordine dei lotti;
- imposta di successione e costo fiscale dell'erede;
- obblighi dichiarativi, monitoraggio, bollo, IVAFE o imposte di transazione;
- caratteristiche di prodotto (TER, duration, holdings, valuta, ISIN,
  percentuale di titoli pubblici agevolati).

Se non trovi una fonte autorevole: **non dedurre la regola**. Scrivi
`NON VERIFICATO` e blocca la conclusione che ne dipende.

## Procedura

1. **Qualità dati.** Prima di interpretare un CSV portfolio esegui
   `scripts/portfolio_validator.py`. Non correggere silenziosamente quantità,
   prezzi, unità obbligazionarie, duplicati o ISIN incoerenti. Un duplicato
   dello stesso ISIN/broker va consolidato nel portfolio e mantenuto a lotti in
   un dataset separato.
2. **Profilo.** Verifica residenza fiscale, regime (amministrato / dichiarativo
   / gestito), broker, orizzonte, target e minusvalenze con anno di realizzo.
3. **Strumenti.** Parti sempre da `ISIN → natura giuridica`. Il campo `tipo` del
   CSV è una dichiarazione dell'utente, non una prova. Usa
   `scripts/instrument_resolver.py` o il registry ISIN verificato. Non dedurre
   il tipo dal prefisso ISIN o dal nome commerciale. Per ETC/ETN consulta la
   sezione `Taxation in Italy` del prospetto specifico.
4. **Evento fiscale.** Dopo lo strumento identifica l'evento: vendita, rimborso,
   cedola, interesse, dividendo, distribuzione, successione. **Non esiste una
   sola categoria fiscale per strumento**: una obbligazione può generare reddito
   diverso con la cessione e reddito di capitale con la cedola. Usa
   `scripts/event_tax.py` per i proventi periodici coperti e
   `scripts/tax_engine.py` per le vendite.
5. **Base fiscale.** Prima di usare `pmc` determina quale criterio si applica a
   regime, strumento ed evento. In amministrato, per i redditi diversi coperti,
   verifica il costo medio ponderato della categoria omogenea; in dichiarativo
   verifica se la vendita parziale richiede i lotti/LIFO. Per ETF/OICR non
   estendere una regola di costo alla componente di reddito di capitale senza
   verificarne la disciplina specifica. Usa `scripts/lot_sale.py` nei casi
   lot-aware coperti.
6. **Zainetto.** Preferisci il CSV strutturato a un saldo unico. Ogni lotto deve
   avere `broker, regime, anno_realizzo, importo`. In amministrato una vendita
   usa solo le minus disponibili presso lo stesso intermediario e non scadute;
   in dichiarativo il simulatore può aggregare i lotti marcati dichiarativo.
7. **Valuta e flussi esteri.** Se acquisto, vendita o provento non sono in euro,
   verifica date e cambi fiscalmente rilevanti; `valuta_esposizione` non è la
   valuta fiscale dell'operazione. Con broker o redditi esteri verifica anche
   monitoraggio, IVAFE e trattamento delle ritenute estere prima del calcolo.
8. **Calcoli.** Esegui i numeri con gli script, non a mente. Gli script non
   sanano una classificazione o una base fiscale non verificata:
   input sbagliato → output sbagliato.
9. **Norma.** Per ogni conclusione fiscale rilevante recupera una fonte corrente
   secondo [references/fonti.md](references/fonti.md), verificane la vigenza
   alla data rilevante e cita norma/articolo/circolare.
10. **Tax drag.** Prima di consigliare una vendita confronta imposta immediata,
    eventuali bollo/IVAFE, ritenute estere non recuperabili, imposte di
    transazione, commissioni, spread e cambio. Se un componente non è
    verificabile, dichiaralo invece di ometterlo.
11. **Separazione.** Distingui sempre `dato → legge → calcolo → opinione`.
12. **Claim audit.** Chiudi ogni analisi con la tabella di audit.
13. **Revisione avversariale.** Cerca attivamente errori su evento fiscale,
    classificazione strumento, base fiscale, valuta, concentrazione, assunzioni
    sui rendimenti, costi e ordine delle operazioni.
14. **Stop.** Se manca un dato che può cambiare la conclusione (regime, broker,
    evento, base fiscale/lotti, quota agevolata, scadenza minus, valuta/cambio,
    KID/prospetto), fermati. Non stimarlo.

## Riferimenti

- [references/fonti.md](references/fonti.md) — gerarchia delle fonti e vigenza.
- [references/fiscalita.md](references/fiscalita.md) — redditi di capitale vs
  diversi, titoli pubblici, OICR, zainetto, successione.
- [references/eventi-fiscali.md](references/eventi-fiscali.md) — routing per
  vendita, dividendo, cedola, interesse e distribuzione OICR.
- [references/strategie-fiscali.md](references/strategie-fiscali.md) — base
  fiscale, accumulazione/distribuzione, multi-ISIN, ordine operazioni,
  trasferimenti broker, valuta, redditi esteri, Tobin tax e tax drag.
- [references/regole-correnti.md](references/regole-correnti.md) — valori
  variabili nel tempo, con data di verifica.

## Script

Tutti gli script sono stdlib-only e stampano JSON.

```bash
# Validazione strutturale prima dell'analisi
python scripts/portfolio_validator.py valida portafoglio.csv

# Analisi base
python scripts/portfolio.py analizza portafoglio.csv

# Zainetto strutturato per broker e scadenza
python scripts/zainetto.py stato zainetto.csv --anno-fiscale 2026
python scripts/zainetto.py compensa zainetto.csv --importo 700 \
  --broker Directa --regime amministrato --anno-fiscale 2026

# Ribilanciamento tax-aware
python scripts/portfolio.py ribilancia portafoglio.csv \
  --target azionario=70,obbligazionario=25,liquidita=5 \
  --zainetto-csv zainetto.csv --anno-fiscale 2026 --regime amministrato

# Base fiscale aritmetica da lotti
python scripts/cost_basis.py calcola lotti.csv --metodo cmp --quantita 25
python scripts/cost_basis.py calcola lotti.csv --metodo lifo --quantita 25

# Vendita lot-aware nei casi coperti
python scripts/lot_sale.py vendita --tipo azione --regime dichiarativo \
  --lotti lotti.csv --prezzo 140 --quantita 15

# Evento periodico: cedola/dividendo/distribuzione
python scripts/event_tax.py classifica --tipo obbligazione --evento cedola
python scripts/event_tax.py provento --tipo azione --evento dividendo --lordo 100
python scripts/event_tax.py provento --tipo etf --evento distribuzione \
  --lordo 100 --quota-stato 0.30

# Verifica ISIN/tipo contro un registry costruito da KID/prospetti verificati
python scripts/instrument_resolver.py resolve \
  --isin US0378331005 --tipo azione --registry strumenti.csv

# Blocca il portfolio se anche uno strumento non e' verificato
python scripts/portfolio.py analizza portafoglio.csv \
  --registry strumenti.csv --strict-instruments

# Successione: solo casi coperti esplicitamente dal motore
python scripts/successione.py costo --tipo azione --valore-dichiarato 10000
python scripts/successione.py costo --tipo titolo_stato \
  --esente-successione --valore-normale 10250

# Test
python tests/run_tests.py
python tests/run_support_tests.py
python tests/run_extended_tests.py
```

Esempi:

- [examples/portafoglio-esempio.csv](examples/portafoglio-esempio.csv)
- [examples/lotti-esempio.csv](examples/lotti-esempio.csv)
- [examples/zainetto-esempio.csv](examples/zainetto-esempio.csv)
- [examples/strumenti-registry-esempio.csv](examples/strumenti-registry-esempio.csv)

## Evento fiscale prima della categoria

Non usare la classificazione della vendita per classificare automaticamente un
flusso periodico.

Esempi:

```text
azione + vendita      -> reddito diverso nei casi coperti
azione + dividendo    -> reddito di capitale
obbligazione + vendita -> reddito diverso nei casi coperti
obbligazione + cedola  -> reddito di capitale
ETF/OICR + distribuzione -> reddito di capitale
```

Per dividendi esteri con ritenuta alla fonte `event_tax.py` fa hard-stop:
servono Paese, convenzione, modalità di incasso e trattamento della doppia
imposizione. Vedi [references/eventi-fiscali.md](references/eventi-fiscali.md).

## Instrument resolver

Il resolver **non cerca di indovinare** che cosa sia un ISIN. Valida il check
digit ISO 6166/Luhn e, se gli viene fornito un registry, confronta il tipo del
portfolio con una classificazione verificata su KID/prospetto.

Una riga di registry è azionabile solo con:

```text
isin,tipo,fonte,verificato_il
```

Se l'ISIN non è nel registry, il tipo è incoerente o mancano fonte/data, la
conclusione fiscale va bloccata in modalità `--strict-instruments`.

## Base fiscale e lotti

Il campo `pmc` è un input operativo, **non una prova della base fiscale**.
Prima di simulare una vendita verifica che corrisponda al criterio applicabile.
La distinzione è particolarmente importante nelle vendite parziali:

- nel risparmio amministrato, per i redditi diversi coperti dall'art. 6 del
  D.Lgs. 461/1997, il riferimento è il costo/valore medio ponderato della
  categoria omogenea;
- nel dichiarativo, per le fattispecie dell'art. 67 c.1-bis TUIR fino al 2026,
  l'ordine dei lotti è LIFO;
- per ETF/OICR la componente positiva e quella negativa possono seguire regole
  reddituali differenti: non usare un solo criterio per analogia.

`scripts/cost_basis.py` esegue soltanto l'aritmetica CMP/LIFO.
`scripts/lot_sale.py` collega quella base alla simulazione della vendita, ma
deduce automaticamente CMP/LIFO solo per azioni, obbligazioni, titoli pubblici
e certificates nei casi coperti. ETF/OICR fanno hard-stop invece di essere
assimilati.

Se la conclusione dipende dai lotti e non sono disponibili, restituisci
`BASE_FISCALE_NON_VERIFICATA`.

## Validazione portfolio

`portfolio_validator.py` è obbligatorio prima di usare metriche o fiscalità di
un CSV non già validato. Blocca, tra l'altro:

- quantità non positive o numeri non finiti;
- ISIN formalmente invalidi;
- stesso ISIN con tipi incoerenti;
- duplicati dello stesso `ISIN + broker` che falserebbero pesi/HHI;
- `quota_stato` fuori da 0..1.

Segnala inoltre unità obbligazionarie sospette, broker/valute mancanti e ricorda
che `pmc` non equivale automaticamente a base fiscale.

## Zainetto strutturato

Formato:

```text
broker,regime,anno_realizzo,importo
Directa,amministrato,2022,500
Directa,amministrato,2024,1200
IBKR,dichiarativo,2023,800
```

La scadenza viene calcolata come quarto periodo d'imposta successivo all'anno
di realizzo. Il simulatore consuma prima i lotti con scadenza più vicina per
minimizzare il rischio di perderli: **questa è una strategia del simulatore, non
una regola contabile imposta al broker**.

`--minus 2000` resta disponibile solo come modalità legacy semplificata.

## Successione

Non usare mai la parola "affrancamento" come scorciatoia. Separa almeno:

1. inclusione/esclusione dall'attivo ereditario;
2. eventuale imposta di successione;
3. costo fiscalmente riconosciuto all'erede;
4. futura tassazione del rendimento/cessione, che dipende dalla natura dello
   strumento.

`scripts/successione.py` implementa soltanto i casi direttamente coperti dalla
regola dell'art. 68 c.6 per azioni/titoli/obbligazioni: valore definito o, in
mancanza, dichiarato; per titoli esenti, valore normale alla data di apertura;
oneri inerenti documentabili aggiunti al costo. Per ETF/OICR e strumenti
ibridi il modulo fa hard-stop invece di estendere la regola per analogia.

## Output incompleto

Quando un dato necessario manca, il motore non produce falsa precisione. Può
restituire `imposta_stimata: null`, `dato_mancante` e uno scenario min/max. Lo
stesso vale per la minusvalenza fiscalmente rilevante di un OICR quando manca
la percentuale agevolata.

## Claim audit (obbligatoria)

| Affermazione | Tipo | Fonte | Data fonte | Confidenza |
| --- | --- | --- | --- | --- |
| ... | dato / legge / calcolo / opinione | ... | ... | Alta/Media/Bassa |

Una riga per ogni affermazione che può influenzare una decisione. Se fonte o
confidenza non sono adeguate, marca la conclusione come non azionabile.

## Limiti

Questa skill produce **analisi e simulazioni**, non consulenza finanziaria né
fiscale. Le imposte effettive in amministrato restano quelle determinate
dall'intermediario. Non suggerire operazioni motivate soltanto dal recupero di
minusvalenze.

## Convenzioni portfolio CSV

Colonne richieste: `isin,nome,tipo,quantita,pmc,prezzo,asset_class`.
Consigliate: `valuta_esposizione,valuta_quotazione,area,settore,broker,quota_stato`.

Per il dichiarativo o quando una vendita parziale dipende dalla base fiscale,
usa un dataset a lotti separato con almeno
`isin,data_acquisto,quantita,costo_unitario,valuta,costi` invece di inventare un
PMC equivalente.

Obbligazioni: `quantita` = valore nominale, `pmc` e `prezzo` in frazione
(corso 101,30 → `1.0130`). `valuta_esposizione` è la valuta economica dei
sottostanti, non quella di quotazione. `valuta_quotazione` serve a identificare
i flussi da convertire secondo la regola fiscale applicabile. `quota_stato` è
compresa tra 0 e 1 e deve provenire dall'emittente/intermediario; se manca non
assumere 0.
