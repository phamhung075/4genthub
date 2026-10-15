# Update .env.sample Templates & Documentation

1. **agenthub_client Updates:**
   - Updated `agenthub_client/.env.sample` removing deprecated 4genteam variables (`AGENTHUB_URL`, `AGENTHUB_PORT`, `AGENTHUB_STATE_ROOT`, `AGENTHUB_SKILLS_ROOT`, `AGENTHUB_CLIENT_SKILLS`) and adding TypeSafe AI / Jev gate variables (`TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`) and `DEEPSEEK_API_KEY`.
   - Updated `agenthub_client/README.md` Configuration table with active variables and accurate compaction ceiling defaults.
   - Updated `agenthub_client/docs/AGENT-SETUP.md` and `agenthub_client/skills/client/install/SKILL.md` to reflect the clean configuration template.
   - Pinned submodule commit `94fa49e`.

2. **Root Repository Updates:**
   - Updated root `.env.sample` adding the `VALIDATION GATE & AI SERVICES` section for `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, and `VALIDATION_GATE_ENFORCEMENT`.
