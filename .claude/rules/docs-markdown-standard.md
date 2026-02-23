---
paths:
  - "docs/**/*.md"
---

Use only standard CommonMark/GFM syntax in Markdown files under `docs/`. Jekyll (just-the-docs) and Kramdown-specific syntax is prohibited.

Prohibited syntax:
- YAML front matter (`---\ntitle: Foo\n---`) — use a `# Heading` at the top of the file instead
- Kramdown attribute blocks (`{: .no_toc }`, `{: .text-delta }`, `{: .note }`, etc.)
- TOC directives (`{:toc}`)

For callouts, use blockquotes:
- `{: .note }` → `> **Note:** text`
- `{: .important }` → `> **Important:** text`
- `{: .warning }` → `> **Warning:** text`
