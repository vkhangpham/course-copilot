# Vendor Submodules

This project expects two git submodules to provide the reference implementations described in `docs/PLAN.md` and `docs/PoC.md`:

| Path | Upstream | Purpose |
| ---- | -------- | ------- |
| `vendor/rlm` | https://github.com/vkhangpham/open-notebook | Minimal Recursive Language Model (RLM) REPL used by the teacher agent |
| `vendor/open-notebook` | https://github.com/vkhangpham/rlm | NotebookLM-style publishing surface |

Initialize or update them with:

```bash
git submodule update --init --recursive vendor/rlm vendor/open-notebook
```

The unusual mapping (RLM code hosted in `open-notebook`, Open Notebook code hosted in `rlm`) mirrors the user-provided forks. Update the table above if those forks change.
