# Portable Agent Skill distribution

The provider-neutral source of truth is:

```text
skills/italian-investor/
```

It follows the Agent Skills folder model: `SKILL.md` plus referenced scripts, resources, examples, and tests. Keep provider-specific packaging outside this directory.

## Build a portable skill ZIP

```bash
bash ./tools/build-skill-archive.sh
```

This creates:

```text
dist/italian-investor-skill.zip
└── italian-investor/
    ├── SKILL.md
    ├── scripts/
    ├── references/
    ├── examples/
    └── tests/
```

`dist/` is ignored by Git.

## Claude.ai / Claude Desktop

Custom skills can be uploaded from **Customize > Skills**. Use the `+` button, choose **Create skill**, then **Upload a skill**, and upload `dist/italian-investor-skill.zip`.

For an individual account, a custom uploaded skill is private to that account. Team and Enterprise organizations can additionally share/provision skills according to their organization settings.

Official documentation:

- https://support.claude.com/en/articles/12512180-use-skills-in-claude
- https://support.claude.com/en/articles/12512198-how-to-create-custom-skills

## Claude Code

The repository also ships as a Claude Code plugin:

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
```

Install directly from the repository marketplace:

```text
/plugin marketplace add eliazv/italian-investor
/plugin install italian-investor@italian-investor
```

## OpenAI

The same core skill is packaged for ChatGPT/Codex and can also be uploaded through the OpenAI Skills API. See [OPENAI.md](OPENAI.md).

## Maintenance rule

Do not maintain separate copies of `SKILL.md` for Claude and OpenAI unless a behavior is genuinely provider-specific. Fix instructions, references, scripts, and tests in `skills/italian-investor/` first, then update only the thin platform-specific manifests or release metadata around it.
