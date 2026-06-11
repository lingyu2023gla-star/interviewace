# GBrain Markdown Export

InterviewAce can export local `knowledge_chunks` into GBrain-friendly Markdown files for long-term memory, project pitch reuse, and cross-agent knowledge sharing.

The exporter does not call GBrain CLI, does not call LLM, and does not modify the database.

## Run

```bash
.venv/bin/python -m integrations.gbrain.cli --db data/interviews.db --out exports/gbrain
```

## Output

```text
exports/gbrain/
├── index.md
├── interviews/
├── topics/
└── chunks/
```

`index.md` is the entrypoint. Per-chunk files preserve metadata and raw metadata JSON for traceability.
