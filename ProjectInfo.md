Dynamic CYOA Engine (Python), Auto-Generated Rules, Local/Remote LLMs

1) Goals (dynamic only)
	•	Engine accepts a free-text scenario description and has the model output a ScenarioSpec (structured rules).
	•	No hand-written rulepacks and no scenario nouns baked into code, prompts, or tests.
	•	The server enforces rules; the model can only propose outcomes via allowed operations.
	•	Works with local LLMs (Ollama / llama.cpp server / vLLM) and OpenAI-compatible endpoints through one provider interface.
	•	Prevent “thought leaks”: only POV entity’s private state is visible each turn.

Non-goals for v1: UI, persistent DB, multi-agent graphs. Keep a thin orchestrator.

⸻

2) Top-level flow
	1.	/scenarios/generate
Input: free-text.
Output: ScenarioSpec JSON (conforming to schema below).
	2.	/scenarios/{id}/compile
Validate (jsonschema + static checks) → compile into reducers + tools.
Run Monte-Carlo dry-runs with seeded RNG to satisfy a negativity budget (fail if too easy).
	3.	/sessions
Create session from compiled spec + seed.
	4.	/sessions/{id}/turns (SSE)
Orchestrator builds limited context → calls Narrator (single tool-enabled call) → validates Outcome JSON → applies reducers → streams narration + diff.

⸻

3) Contracts (generic only)

3.1 ScenarioSpec (LLM-generated, engine-validated)
	•	Versioned: spec_version: "1.0"
	•	Required fields:
	•	id: string, name: string, seed: integer, spec_version: string
	•	state: object (arbitrary; engine treats as opaque tree)
	•	entities: array<object> (type descriptors, optional)
	•	actions: array<object> (see below)
	•	random_events: array<object> (see below)
	•	loss_conditions: array<object> (≥ 2)
	•	negativity_budget: object (e.g., { min_fail_rate: 0.25, decay_per_turn: { <path>: number } })
	•	Action shape (generic):
	•	id: string
	•	params: object (schema for parameters; primitive types only)
	•	preconditions.jsonlogic: object
	•	derives.jsonlogic?: object (named derived values usable in effects)
	•	effects: array<EffectOp>
	•	Random event shape:
	•	id: string
	•	weight: number (bounded; see validator)
	•	when.jsonlogic: object
	•	effects: array<EffectOp>
	•	duration?: string (ISO-like “7d/12h”)
	•	EffectOp (the only write ops the engine will ever execute):
	•	set { path, value }
	•	inc { path, value }
	•	dec { path, value }
	•	mul { path, value }
	•	patch { path, valueObject } (shallow merge)
	•	push { path, value } / pop { path } (arrays)
	•	addlog { message } (append to a log list)
	•	schedule { id, at|after, effects[] } (optional v1.1)

Paths are JSON-Pointer-like (state.a.b[2].c). No code or expressions in value—only literals or previously defined derives keys.

3.2 Outcome (Narrator output per turn)
	•	Schema:
	•	narrative: string (visible narration only)
	•	visible_dialogue?: array<{ entity_id, utterance }>
	•	state_changes: array<{ op, path, value? }> (must map to EffectOp)
	•	roll_requests?: array<{ kind, target?, difficulty }>
	•	hidden_memory_updates?: array<{ scope, target_id, content, visibility }>
	•	additionalProperties: false — reject unknown keys.

⸻

4) Prompts (domain-agnostic)

4.1 Scenario generation — System

You produce a ScenarioSpec that matches a provided jsonschema and uses ONLY the allowed effect operations.
Include at least TWO loss_conditions and a non-zero negativity_budget.
Provide a random_events deck where each event’s weight is within allowed bounds.
Use JSONLogic only in preconditions and derives.
Do not include narrative prose or extra keys. Output ONLY the ScenarioSpec.

User: free-text description (no genre hinted by us; the user supplies it).

4.2 Narrator — System

ROLE: Narrator & Referee.
Use provided tools for all reads/writes.
Never reveal inner thoughts of non-POV entities.
Return valid Outcome JSON only. If uncertain, add a roll_requests entry.

⸻

5) Orchestrator (thin, generic)
	•	Build POV-only private + public slice of state, last N turn summaries, and no scenario nouns in prompts.
	•	Provide generic tools derived from the compiled spec:
	•	action:<id>(params) → validates preconditions/params, executes effects if allowed.
	•	query(path) → read-only snapshot of any public path.
	•	roll(kind, target?, difficulty) → deterministic RNG by (session_seed, turn, kind, target).
	•	Single model call per turn with tools enabled + Outcome schema.
	•	Validate JSON strictly; on failure run one repair attempt (ask the model to fix JSON to schema). If still invalid, fall back to server-resolved minimal response.

⸻

6) Validator & Auto-balance (generic)
	•	Schema: enforce presence/types; forbid code in values; bounds for weight (e.g., 0.05–0.30).
	•	Negativity guards:
	•	Require ≥ 2 loss_conditions.
	•	Require non-zero negativity_budget.
	•	Monte-Carlo dry-run (no LLM): simulate K turns using
	•	Random events by weight/conditions,
	•	A baseline “idle” action policy (or a minimal stochastic policy calling permitted actions with random legal params).
	•	Enforce fail_rate ≥ min_fail_rate and cap positive drift per turn.
	•	Auto-repair: If checks fail, adjust event weights/effects conservatively and re-validate (one retry).

⸻

7) Memory & visibility (generic)
	•	Public vs Private memory collections keyed by entity_id.
	•	Context builder includes POV private + all public; never includes others’ private.
	•	hidden_memory_updates can write to private memory (server-side), but are never returned to the player.

⸻

8) Providers (local/remote, same interface)
	•	OpenAI-style chat(messages, tools=?, json_schema=?, stream=?).
	•	Env config only:
	•	MODEL_PROVIDER=openai|ollama|generic
	•	OPENAI_API_BASE (OpenAI or local server URL)
	•	OPENAI_API_KEY (dummy ok for local)
	•	MODEL_NAME (e.g., any installed local model)
	•	Local-Lite profile: single call per turn; no multi-agent graph. Keep latency low.

⸻

9) Testing (proves dynamic behavior)
	•	No-nouns test: scan repository for disallowed tokens list (maintain an empty list by default; add any genre words you accidentally introduce). Build fails if found.
	•	Schema tests: any ScenarioSpec from generator must pass jsonschema & static checks.
	•	Monte-Carlo property test: for randomly sampled specs (within resource bounds), dry-run and assert negativity constraints hold (or spec rejected).
	•	Outcome schema test: mock provider returns malformed payloads; ensure repair path catches/fails safely.
	•	Determinism: same seed + same inputs ⇒ same state diffs.
	•	Visibility: enforce that non-POV private memory never appears in context/messages.

⸻

10) Cursor task list (strictly generic)
	1.	Scaffold FastAPI: routes /scenarios/generate, /scenarios/{id}/compile, /sessions, /sessions/{id}/turns (SSE). No scenario words in code/comments.
	2.	Provider interface: one OpenAI-style class; adapters for OpenAI/Azure, Ollama, and generic URL using httpx. Env-driven selection.
	3.	Schemas:
	•	SCENARIO_SPEC_SCHEMA (fields above, spec_version: "1.0").
	•	OUTCOME_SCHEMA (fields above, additionalProperties: false).
	4.	Scenario generator:
	•	System prompt from §4.1.
	•	Return raw JSON (reject YAML for v1 to simplify).
	5.	Validator:
	•	jsonschema; static bounds; forbid code in values; negativity budget rules.
	•	Monte-Carlo dry-run (configurable K, default small for dev).
	•	One auto-repair pass that only adjusts numeric weights/mults by small factors.
	6.	Compiler:
	•	Translate actions → callable tools: action:<id>(params).
	•	JSONLogic evaluator for preconditions/derives.
	•	Map effects to reducers (set/inc/dec/mul/patch/push/pop/addlog).
	7.	Orchestrator:
	•	Context builder (POV/private + public).
	•	Single model call with tools + OUTCOME_SCHEMA.
	•	Validate/repair outcome; apply reducers; emit SSE chunks for narrative_chunk then final diff.
	8.	Memory:
	•	In-memory public/private stores keyed by entity/session.
	•	hidden_memory_updates write path only on server.
	9.	Tests: implement §9 set, plus a regex-based no-nouns test (configure list; keep empty by default).
	10.	Docs:

	•	Document env variables and the invariant: “no scenario nouns in code”.

⸻

11) Acceptance criteria (engine-level)
	•	✅ Engine runs end-to-end with any user description; code contains no baked-in scenario nouns.
	•	✅ Specs failing negativity or schema rules are rejected or auto-repaired with clear messages.
	•	✅ Turns produce valid Outcome JSON and deterministic state diffs.
	•	✅ Works with OpenAI and Ollama by switching env only.
	•	✅ Private thoughts appear only for the POV entity; never for others.

⸻
