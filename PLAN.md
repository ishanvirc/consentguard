# ConsentGuard — 4-Day Build Plan

Deadline: **Sun Jul 6, 11:59 PM PDT** (Kaggle). Treat Jul 5 as the real deadline; Jul 6 is buffer.

## Day 1 — Thu Jul 2: core green + agents wired

- [ ] `uv sync` · `cp .env.example .env` (add Gemini key)
- [ ] `uv run pytest` → all 9 gate tests green (pure stdlib, no API needed)
- [ ] `uv run python -m app.ledger seed` → DB created
- [ ] **Verify ADK v2 import paths** against installed version — especially `AgentTool` (`google.adk.tools.agent_tool`). `agents-cli playground` surfaces drift immediately; fix imports if the API moved.
- [ ] First end-to-end run in playground: "Review campaign_summer.json" → expect 3 PASS / 5 BLOCK
- [ ] Tune `check_message_requirements` regexes if template checks misfire
- [ ] Create GitHub repo (public by submission day; keep `.env` out — it's gitignored)

## Day 2 — Fri Jul 3: quality loop + MCP story

- [ ] Prompt-tune auditor/verifier until the run matches `eval/golden_scenarios.json` — especially c_004 (verifier must overturn the withdrawal flag via `lookup_consent_history`)
- [ ] `agents-cli eval` run: exact-match verdicts + LLM-as-judge on explanations; save output for writeup
- [ ] Attach `mcp_server/consent_ledger.py` to Claude Desktop or Gemini CLI; screenshot it answering "does c_003 have valid email consent?" — the interoperability shot
- [ ] Polish orchestrator's audit-report formatting (the demo centerpiece)
- [ ] Stretch: wire ADK to the ledger *via MCPToolset* instead of in-process tools (course-concept bonus; in-process fallback already works)

## Day 3 — Sat Jul 4: deploy + record everything

- [ ] `agents-cli scaffold enhance` → Terraform/CI → deploy to Cloud Run; screenshot console + a request against the deployed endpoint
- [ ] Record all footage: playground full run, c_004 adjudication close-up, eval results, MCP-in-Claude/Gemini-CLI, Cloud Run, Antigravity building a feature (e.g., add a GDPR rule pack live — great b-roll)
- [ ] Draft narration against `writeup/VIDEO_SCRIPT.md`; do a timed read (<4:45)

## Day 4 — Sun Jul 5: ship

- [ ] Edit video ≤5:00 → upload to YouTube (public)
- [ ] Finalize Kaggle Writeup (≤2,500 words — count it), pick **Agents for Business** track
- [ ] Cover image (architecture diagram or gate-verdict screenshot)
- [ ] Attach: video, cover image, public repo link
- [ ] Make repo public · final README pass · **SUBMIT** (not draft!)

## Mon Jul 6 — buffer only

Fix anything judges-facing; resubmit before 11:59 PM PDT.

## Risks

| Risk | Mitigation |
|---|---|
| ADK v2 API drift (AgentTool/MCPToolset paths) | Day-1 playground check; in-process tools already work without MCP wiring |
| Verifier agent too chatty / inconsistent | Bounded per-recipient output format in instruction; eval loop Day 2 |
| Cloud Run auth friction | Deployability can be *shown* via scaffold + console; live endpoint optional per rules |
| Video runs long | Script is timed; demo footage at 1.5× where needed |

## Boundaries (non-negotiable)

- **No API keys or secrets anywhere in the repo** (hackathon rule; `.env` only).
- All contacts, businesses, and campaigns stay **fictional**.
- The repo **stands alone**: no references to private business projects, client names, internal tooling, or other codebases. Public statutes (CASL/CAN-SPAM) and public design patterns only.
- Rule packs are engineering controls, not legal advice — keep the disclaimer.
