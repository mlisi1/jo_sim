# Contributing

- **Branches:** work on `dev` in every repository.
- **Commits:** few, grouped by topic, one per repository. Commit the submodule first, then
  jo_sim with the pointer bump.
- **Push order:** jo_description, jo_navigation, then jo_sim.
- **Docs in the same commit as the feature.** A new argument, topic, world feature or config
  difference updates its page here. `mkdocs build --strict` runs in CI.
- **Test in the sandbox** (domain 77, partition `jo_sim_test`). See [Testing](testing.md).

## Working on these docs

```bash
python3 -m venv .venv && .venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve          # http://127.0.0.1:8000, live reload
.venv/bin/mkdocs build --strict # what CI runs
```

- Pages are in `docs/`; the navigation is in `mkdocs.yml`.
- Media placeholders are `<div class="media-ph" data-kind="image|video|diagram">` blocks. Replace
  them with real media in `docs/assets/`. Keep videos short and compressed: Pages serves no Git LFS.
- Tooltips for abbreviations come from `docs/includes/abbreviations.md`.
