# Documentation Contributing Guide

> Rules for maintaining the AI assistant documentation. Follow these when adding, updating, or restructuring any `.md` files in this system. These rules apply to both human developers and AI sessions.

## Why This Architecture Exists

Claude reads `CLAUDE.md` on every conversation start. If it's bloated with detail, it wastes context window on content that may not be relevant to the task. The architecture solves this:

- **`CLAUDE.md`** is loaded every time -- must stay concise (index + critical one-liners)
- **`docs/tech/*.md`** are technical documentation files loaded on demand -- only when a task touches that topic. README.md in that folder contains an index.
- **`docs/domain/*.md`** are domain documentation files loaded on demand -- only when a task touches that topic. README.md in that folder contains an index.
- **Directory-specific `CLAUDE.md`** files are loaded when working in that directory

This means the AI gets the right information at the right time without burning context on irrelevant detail.

## File Locations and Scope

| Location | Purpose | Loaded when |
|----------|---------|-------------|
| `/CLAUDE.md` | Concise index: tech stack, critical warnings (one-liners), links to detailed docs, quick reference | Every conversation |
| `/docs/tech/README.md` | Index file for technical topic guides | AI reads the file when the task is related to a technical topic to find the correct file |
| `/docs/tech/*.md` | Detailed technical topic guides (one topic per file) | AI reads the file when the task is related to the technical topic |
| `/docs/domain/README.md` | Index file for domain topic guides | AI reads the file when the task is related to a domain topic to find the correct file |
| `/docs/domain/*.md` | Detailed domain topic guides (one topic per file) | AI reads the file when the task is related to the domain |
| `src/**/CLAUDE.md` | Conventions and documentation for a specific directory within the source code | Working in a specific folder of the source code |

### What goes where

- **Rule in `CLAUDE.md`**: one-liner that fits in a bullet point (with a link to detail)
- **Detail in `docs/tech`**: anything technical that needs explanation, examples, tables, checklists, or code blocks
- **Detail in `docs/domain`**: anything domain specific that needs explanation, examples, tables, checklists, or code blocks
- **Directory-specific `CLAUDE.md`**: conventions that only apply when working in that specific directory

## Naming Conventions

- `/docs` files: `UPPERCASE-KEBAB-CASE.md` (e.g., `PACKAGE-GUIDELINES.md`, `STATE-MANAGEMENT.md`)
- Directory-specific files: always named `CLAUDE.md`
- Keep names descriptive and short (2-3 words max)

## File Size Guidelines

- **`/CLAUDE.md`**: aim for <150 lines -- if it grows beyond this, content is leaking in that should be in `docs/`
- **`/docs/**/*.md`**: aim for <300 lines per file -- if a doc grows beyond this, consider splitting into two focused files
- **Directory-specific `CLAUDE.md`**: aim for <100 lines -- these should be tightly scoped

## Checklist: Adding a New Doc

1. Create the file in `/docs/tech` for technology focused docs and `/docs/domain` for domain focused docs, both following the naming convention
2. Add a new entry to the `README.md` file of the corresponding folder.
3. If there's a critical rule, add a one-liner to the `ALWAYS` or `DO NOT USE` block in `/CLAUDE.md` with a link to the new doc
4. Add cross-references from related docs (e.g., a new payment doc should link from `README.md`)
5. Use relative links between `/docs/` files (e.g., `[INTEGRATIONS.md](INTEGRATIONS.md)`)
6. Use relative links from `/CLAUDE.md` (e.g., `[PACKAGE-GUIDELINES.md](/docs/tech/PACKAGE-GUIDELINES.md)`)

## Checklist: Updating an Existing Doc

1. Keep changes within the doc's defined scope -- don't let a doc grow to cover unrelated topics
2. If new content doesn't fit the existing doc's scope, create a new doc instead
3. **Never move detailed content into `/CLAUDE.md`** -- add a one-liner + link instead
4. Update cross-references if you rename sections or files
5. Check that the Documentation Index entry in `/CLAUDE.md` still accurately describes the doc's purpose

## Common Mistakes to Avoid

| Mistake | What to do instead |
|---------|-------------------|
| Inlining detailed content in `/CLAUDE.md` | Create/update a doc in `docs/`, add a one-liner + link |
| Creating a doc without indexing it | Always add to the Documentation Index table in `/CLAUDE.md` |
| Putting directory-specific rules in `/docs/` | Use the directory's `CLAUDE.md` file instead |
| Using absolute paths in links | Use relative paths so links work regardless of where the repo is cloned |
| Duplicating content across multiple docs | Put it in one place, cross-reference from others |
| Letting a doc grow unbounded | Split into focused files when it exceeds ~300 lines |
