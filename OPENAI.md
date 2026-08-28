# OpenAI distribution — Italian Investor

Italian Investor keeps `skills/italian-investor/` as the provider-neutral source of truth. The same Agent Skill can be distributed in two different OpenAI channels:

1. **Public Plugin Directory (ChatGPT + Codex)** — publish the skill as a skills-only plugin through the OpenAI Plugin Submission Portal.
2. **OpenAI Skills API** — upload/version the skill inside an OpenAI API project so applications can reference it programmatically.

These are separate distribution mechanisms. Uploading a skill with the Skills API does **not** publish it in the public Plugin Directory.

## Repository layout

OpenAI-native packaging lives alongside the existing Claude packaging:

```text
.codex-plugin/plugin.json              # OpenAI plugin manifest
.agents/plugins/marketplace.json        # repo-scoped marketplace for local testing
.claude-plugin/plugin.json              # Claude Code manifest; accepted by OpenAI's direct importer
skills/italian-investor/                # provider-neutral Agent Skill (source of truth)
openai/submission-tests.md              # review fixtures / expected behavior
tools/openai/build-plugin-archive.sh    # builds the documented submission archive
tools/openai/upload-skill.sh            # optional Skills API upload helper
PRIVACY.md
SUPPORT.md
TERMS.md
```

## A. Publish to the public Plugin Directory

Official docs:

- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/guides/submit-claude-plugin
- https://developers.openai.com/plugins/build/plugins

### Prerequisites

The OpenAI Platform organization used for publishing must have:

- a verified individual or business developer identity;
- `Apps Management` permission set to `Write` for the submitter (organization owners already have the required access);
- public website, support, privacy-policy, and terms URLs that match the publisher identity.

For this repository:

- Website: `https://github.com/eliazv/italian-investor` (or a dedicated public landing page if available)
- Support: `https://github.com/eliazv/italian-investor/blob/main/SUPPORT.md`
- Privacy: `https://github.com/eliazv/italian-investor/blob/main/PRIVACY.md`
- Terms: `https://github.com/eliazv/italian-investor/blob/main/TERMS.md`

A production-ready logo still needs to be uploaded in the portal.

### Build the archive

OpenAI explicitly supports direct submission of an existing skills-only Claude Code plugin and converts `.claude-plugin/plugin.json` into the OpenAI manifest during import. The repository therefore includes a helper that builds that documented direct-import format:

```bash
bash ./tools/openai/build-plugin-archive.sh
```

It creates:

```text
dist/italian-investor-openai-submission.zip
```

The ZIP has one top-level `italian-investor/` directory containing `.claude-plugin/plugin.json`, `skills/`, and the public license/policy/support files. The OpenAI portal converts the Claude manifest to `.codex-plugin/plugin.json`; review the generated manifest before submission. `dist/` is local build output and is ignored by Git.

The repository also keeps a native `.codex-plugin/plugin.json` for OpenAI-native local/repo packaging and testing.

### Submission path

Italian Investor is currently **skills-only**: it does not need an MCP server or authentication.

1. Open the OpenAI Plugin Submission Portal.
2. Select **Create plugin**.
3. Select **Skills only**.
4. Upload `dist/italian-investor-openai-submission.zip`.
5. Review the generated `.codex-plugin/plugin.json` and resolve any scanner findings.
6. Complete listing metadata, starter prompts, countries/regions, release notes, and policy attestations.
7. Enter at least **5 positive** and **3 negative** reviewer test cases. Ready-to-copy cases are in `openai/submission-tests.md`.
8. Test the imported skill in a clean environment and submit it for review.
9. After approval, choose when to publish it. Publication makes it available in the universal Plugins Directory shared by ChatGPT and Codex.

## B. Test the OpenAI plugin from the repository

The native OpenAI entry point is `.codex-plugin/plugin.json`.

The repository also contains `.agents/plugins/marketplace.json`, which ChatGPT desktop can use as a repo-scoped marketplace during development. Open the repository as the current project/repo, restart ChatGPT desktop after marketplace or plugin changes, and verify that **Italian Investor** appears as an available plugin source/installable plugin on surfaces where repo marketplaces are enabled.

Repo/local marketplaces are for development, testing, or private/team distribution. They are separate from the public Plugins Directory.

## C. Upload the Agent Skill with the OpenAI Skills API

Official API reference:

- https://developers.openai.com/api/reference/python/resources/skills/methods/create
- https://developers.openai.com/api/reference/go/resources/skills

The API accepts either a directory upload or a ZIP. When using a ZIP, package a single top-level `italian-investor/` directory containing `SKILL.md`, `scripts/`, `references/`, examples, and tests.

### Helper included in this repository

Create a new API skill:

```bash
export OPENAI_API_KEY="..."
bash ./tools/openai/upload-skill.sh
```

The command prints the API response, including the generated skill ID.

Create a new immutable version of an existing API skill and make it the default:

```bash
export OPENAI_API_KEY="..."
bash ./tools/openai/upload-skill.sh skill_XXXXXXXX
```

The helper only packages `skills/italian-investor/`; it does not upload Claude/OpenAI marketplace manifests because those belong to plugin distribution rather than the Agent Skill itself.

### Equivalent raw API call

After creating `italian-investor.zip` with one top-level `italian-investor/` folder:

```bash
curl --fail-with-body -X POST "https://api.openai.com/v1/skills" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "files=@italian-investor.zip;type=application/zip"
```

To create a new version:

```bash
curl --fail-with-body -X POST \
  "https://api.openai.com/v1/skills/skill_XXXXXXXX/versions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "default=true" \
  -F "files=@italian-investor.zip;type=application/zip"
```

## Release discipline

Keep the provider-neutral behavior in `skills/italian-investor/`. When changing the public behavior:

- update and test the skill first;
- run the repository CI/tests;
- update versions in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `.codex-plugin/plugin.json` together when cutting a release;
- create a new Skills API version if the API-distributed skill must change;
- submit a new Plugin Directory version when the published plugin bundle or listing changes materially.

Do not fork the skill instructions into separate Claude and OpenAI copies unless a genuinely provider-specific behavior is required.
