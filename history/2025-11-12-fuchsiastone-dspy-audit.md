# DSPy/OpenAI Stack Audit — 2025-11-12 (FuchsiaStone)

## Scope
Inventory the current DSPy runtime + configuration touchpoints, reconcile docs/config samples with the latest implementation, and flag the remaining integration gaps called out in PLAN §2 / §4.

## Findings
1. **Configuration shape drift** – Runtime now expects role objects (`teacher/ta/student`) but several docs still showed the legacy `models:` block. Updated:
   - `docs/ARCHITECTURE.md` §2.2 now mirrors the actual schema + notes the per-role env fallback order.
   - `docs/PLAN.md` environment/model bullets explain the new resolution order (role-specific env → `OPENAI_API_KEY`).
   - `README.md` already documented the change; no further edits required.
2. **Sample configs** – Replaced `config/model_config.yaml` with the nested format so newcomers have a working reference (including optional per-role env overrides). The old file also carried unused `codeact` knobs; left them under a comment until those hooks exist.
3. **Agent instructions** – Added a short reminder in `AGENTS.md` (“Operational expectations”) so folks know DSPy consumes role-specific env vars when present.
4. **Runtime audit**
   - `configure_dspy_models` now resolves API keys/bases per role and forwards extra kwargs (`ccopilot/core/dspy_runtime.py`), and tests cover the env precedence (`tests/test_dspy_runtime.py`).
   - `bootstrap_pipeline` still stores handles on `PipelineContext` and logs the selected models.
   - **Gap:** `build_default_registry` ignores `dspy_handles` entirely, and `TeacherOrchestrator` never reads the handles. CodeAct runs therefore execute with default DSPy settings (whatever `dspy.settings.configure` last set) and we cannot yet swap per-role providers.
   - **Gap:** The RLM/TA loop still uses the placeholder simulator (ccopilot-ggk); no depth-1 DSPy calls yet, so provenance lacks LLM trace IDs.

## Suggested follow-ups
1. Reduce `build_default_registry(... dspy_handles=...)` to actually wire the handles into DSPy `CodeAct` factories (e.g., pass `lm=handles.ta` or configure per-program settings) so ablations can swap models.
2. When ccopilot-ggk lands the teacher loop, thread the `ctx.dspy_handles` into role prompts (teacher vs TA vs student graders) instead of relying on global `dspy.settings`.
3. Once per-role providers are active, add provenance logs capturing the resolved provider/model + API base per stage for easier ops triage.

_No new issues opened yet; happy to spin beads for the above gaps once priorities are aligned._
