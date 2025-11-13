# Vendor Submodules

This project expects two git submodules to provide the reference implementations described in `docs/PLAN.md` and `docs/PoC.md`:

| Path | Upstream | Purpose |
| ---- | -------- | ------- |
| `vendor/rlm` | https://github.com/vkhangpham/rlm | Minimal Recursive Language Model (RLM) REPL used by the teacher agent |
| `vendor/open-notebook` | https://github.com/vkhangpham/open-notebook | NotebookLM-style publishing surface |

Initialize or update them with:

```bash
git submodule update --init --recursive vendor/rlm vendor/open-notebook
```

These URLs now align with the canonical forks: `vendor/rlm` points at the RLM repo, and `vendor/open-notebook` points at the Open Notebook repo. Update the table above if either fork changes.
