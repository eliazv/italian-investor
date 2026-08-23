# CLAUDE.md

Repo della Agent Skill `italian-investor`, distribuita come plugin Claude Code.
I file della skill stanno in `skills/italian-investor/`; il packaging in
`.claude-plugin/`.

## Regole per modificare questo repo

**Bumpa `version` a ogni release.** Sta in due file, `.claude-plugin/plugin.json`
e `.claude-plugin/marketplace.json`, e i due valori devono restare allineati.
Chi ha installato il plugin riceve gli aggiornamenti **solo** se questo campo
cambia: senza bump, la modifica non arriva a nessuno.

**Esegui i test prima di committare.**

```bash
python skills/italian-investor/tests/run_tests.py
```

Se cambi il motore fiscale in `scripts/tax_engine.py`, aggiungi il caso
corrispondente a `tests/casi_fiscali.json` nello stesso commit.

**Non scrivere regole fiscali senza fonte.** Aliquote, qualificazioni e termini
vanno in `references/regole-correnti.md` con data di verifica e link alla fonte
primaria. Una regola senza fonte contraddice il punto stesso della skill. Se un
caso di test si rivela sbagliato, si corregge prima il caso (citando la fonte nel
campo `perche`), poi il codice.

**Ricorda la vigenza.** Dal 1° gennaio 2027 si applica il nuovo testo unico
imposte sui redditi (D.Lgs. 117/2026): la numerazione degli articoli cambia
rispetto al DPR 917/1986.

**Niente dati personali.** `analisi.md` e i portafogli reali sono esclusi via
`.gitignore`: non forzarne l'aggiunta.

## Scelte già prese

Una skill sola, due script, tre file di reference. La divisione in più skill era
stata valutata e scartata: duplicherebbe il layer di verifica delle fonti, che è
il contenuto vero del progetto. MCP e adapter esterni sono rimandati a quando
esisterà un consumatore diverso da Claude Code.
