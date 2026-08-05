# Vendored third-party JS

Both files in this directory are bundled directly in the repository —
no manual download step, no CDN, no network access required at runtime
or at first launch. A freshly extracted copy of this project runs fully
offline immediately.

| File | Library | Version bundled |
|---|---|---|
| `htmx.min.js` | [htmx](https://htmx.org) | 1.9.10 |
| `alpinejs.min.js` | [Alpine.js](https://alpinejs.dev) | 3.10.5 |

**Version note:** earlier drafts of this project pinned htmx 1.9.12 and
Alpine 3.13.5 (the versions originally loaded from CDN). The bundled
files here are 1.9.10 and 3.10.5 — the closest versions that could
actually be retrieved and verified in this build environment. Both are
minor/patch versions within the same major release line and use the
same public API (`hx-*` attributes; `x-data`, `x-show`, `x-model`,
`x-for`, `x-init`, `@click`/`x-on`, `.prevent`/`.outside` modifiers,
etc.) — nothing in this codebase depends on behavior specific to
1.9.12/3.13.5 versus 1.9.10/3.10.5. If a future release standardizes on
the exact originally-pinned versions, simply replace these two files;
no template or Python code changes are needed either way.

**Tailwind CSS did not need vendoring here** — it's compiled ahead of
time into `static/css/tailwind.css` (a build artifact, not a runtime
dependency); see `templates/layout/partials/_tailwind.html`.
