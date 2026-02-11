# FPL Agent Blog Series – Outline

Five-post series building in complexity: **Why FPL is hard for AI** → **Single-prompt strategy** → **Architecture** → **RAG** → **Advanced RAG to reduce noise**. Each post covers purpose, advantages, example output (using `team_data/shared/player_data copy 2.json` where relevant), technical implementation, and challenges.

---

## Post 1: Why FPL is Hard for AI (and may not be in future)

**Tone:** Conceptual, light on code. Sets up the problem and why the later posts matter.

### Purpose
- Explain why Fantasy Premier League is a tough domain for AI: rules, constraints, noisy data, and the need for “expert” reasoning.
- Foreshadow how the series addresses this (single prompt → RAG → advanced RAG).

### Outline

1. **The FPL problem in one paragraph**
   - Budget (£100m), squad (15), formation, 3-per-club, price changes, chips, injuries, form, fixtures.
   - **Code ref:** FPL rules encoded in config and prompts: `fpl_agent/config.yaml` (team, formation_constraints, position_limits), `fpl_agent/strategies/team_building_strategy.py` (constraints in `_create_team_creation_prompt` ~lines 184–193, 274–278).

2. **Why it’s hard for AI**
   - **Structured constraints:** JSON output must satisfy budget, positions, formation; easy to hallucinate invalid teams.
   - **Data volume:** 600+ players; can’t fit all in one context; need selection/filtering.
   - **Noisy, changing data:** Injuries, form, fixtures, price changes; API is source of truth.
   - **Expert knowledge:** “Must-have”, “rotation risk”, fixture difficulty; LLM needs this as context, not only raw stats.
   - **Code ref:** Validator enforcing rules: `fpl_agent/utils/validator.py`; schema: `fpl_agent/utils/schemas.py` (team creation / weekly update).

3. **Why it may not be hard in future**
   - Better long-context models, tool use (e.g. FPL API calls), and RAG over expert text reduce context and hallucination issues.
   - This series implements a path: one prompt → RAG over enriched data → advanced RAG (ranking + filtering) to approximate that.

4. **Example “failure” without structure**
   - Short example: raw prompt with 600 players → over budget or invalid formation; contrast with “we need constrained JSON + filtered player list”.

5. **What we’ll build (series roadmap)**
   - Post 2: One prompt that works with a manageable player list.
   - Post 3: Architecture that separates data, enrichment, and LLM.
   - Post 4: RAG = retrieval (FPL + enrichments) + generation (team pick).
   - Post 5: Advanced RAG = embeddings + hybrid scoring to cut noise and rank players.

**Technical depth:** Low. No code snippets required; config and file names only.  
**Example data:** Optional: one invalid JSON team vs one valid team (can be synthetic).  
**Challenges to mention:** Getting the model to output only JSON; staying within token limits with 600+ players.

---

## Post 2: Single-Prompt Strategy

**Tone:** Medium. One flow: get data → build one prompt → call LLM → parse and validate.

### Purpose
- Show the minimal “single prompt” design: one LLM call for team creation (or weekly update) with FPL data and rules in the prompt.
- Explain prompts, response schema, and validation so Post 4–5 RAG builds on this.

### Outline

1. **What “single prompt” means**
   - One request: system + user content = rules + fixtures + player list (+ optional current team for gw-update).
   - One response: JSON team (starting 11, subs, captain, reasons).
   - **Code ref:** `TeamBuildingStrategy.create_team` and `update_team_weekly` in `fpl_agent/strategies/team_building_strategy.py`; prompts from `_create_team_creation_prompt` and `_create_weekly_update_prompt`.

2. **Where the data in the prompt comes from**
   - FPL API → bootstrap-static (players) and fixtures → processed and cached.
   - **Code ref:** `fpl_agent/data/fetch_fpl.py` (endpoints, `get_fpl_static_data`, `get_fixtures`); `fpl_agent/data/data_processor.py` (`process_fpl_data`, `_process_player`); `fpl_agent/data/data_service.py` (`get_all_gameweek_data`, `get_players`).
   - Optional: brief note that “enrichments” (expert_insights, injury_news) can be absent in this post; we’re showing the minimal pipeline.

3. **Prompt design**
   - Role, task, rules (budget, formation, 3 per club), fixture list, player list.
   - **Code ref:** `_create_team_creation_prompt` (lines ~182–281); `PromptFormatter.format_fixtures`, `format_player_list`, `format_team_constraints` in `fpl_agent/utils/prompt_formatter.py`.
   - How we avoid markdown/extra text: “CRITICAL INSTRUCTION: You MUST respond with ONLY valid JSON” and schema in the prompt.

4. **Response schema and parsing**
   - JSON schema for team (captain, vice_captain, starting, substitutes, reasons).
   - **Code ref:** `fpl_agent/utils/schemas.py` (`create_team_creation_schema`, `create_weekly_update_schema`); `Validator.parse_llm_json_response` and `validate_team_data` in `fpl_agent/utils/validator.py`.

5. **LLM API usage**
   - Two providers: Gemini (direct) and OpenRouter (multi-model, optional web search).
   - **Code ref:** `fpl_agent/strategies/llm_factory.py` (provider selection); `fpl_agent/strategies/llm_engine.py` (Gemini), `fpl_agent/strategies/openrouter_engine.py` (OpenRouter); `fpl_agent/config.yaml` (llm.main, llm.main_openrouter, etc.).
   - How model is chosen per strategy: `TeamBuildingStrategy(model_name="main_openrouter")` in base and main.

6. **End-to-end flow (single prompt)**
   - Fetch gameweek data → build prompt (players + fixtures) → LLM → parse JSON → validate budget/formation → output.
   - **Code ref:** `fpl_agent/main.py` `build_team` with `rag_mode="none"` (use_enrichments=False, use_ranking=False) to illustrate “single prompt only”.

7. **Example output using `player_data copy 2.json`**
   - Describe structure of `team_data/shared/player_data copy 2.json`: `players` dict, each player has `full_name`, `position`, `team_name`, `now_cost`, `form`, `total_points`, etc. (and later: `expert_insights`, `injury_news`, `hybrid_score`).
   - For “single prompt” (rag_mode=none): prompt contains only FPL stats (no enrichments, no ranking). Show a **snippet of the kind of prompt** (e.g. fixture block + one position block of players from the file) and a **sample JSON team output** (e.g. captain, 2–3 starting players with reasons).
   - Advantage: Simple, reproducible, no extra services. Disadvantage: No expert nuance, no prioritisation of players; full list can be long.

8. **Challenges**
   - Token limit with 600+ players: need to either truncate or filter (leads to Post 4–5).
   - JSON-only compliance: schema + retries + validation.
   - Price vs sale price in weekly update: **Code ref** `data_service.get_current_team_player_data` and `fpl_calculations.calculate_fpl_sale_price`; prompt explains “use Sale Price from squad list”.

**Technical depth:** Medium. Key code paths and 1–2 short snippets (prompt fragment, schema).  
**Example data:** `player_data copy 2.json` structure; one prompt snippet; one example team JSON.

---

## Post 3: Designing the Architecture (with Diagram)

**Tone:** Architectural; diagram is the centrepiece.

### Purpose
- Present the high-level architecture: data layer (FPL API, store, processor), enrichment layer (LLM per team), strategy layer (team building / analysis), and CLI.
- Show how “single prompt” fits into a pipeline that will later add RAG and advanced RAG.

### Outline

1. **High-level diagram**
   - **Diagram:** One architecture figure showing:
     - **Data:** FPL API → Fetcher → Processor → DataStore (player_data.json, fixtures.json); DataService as facade.
     - **Enrichment:** DataService (players by team) → TeamAnalysisStrategy (hints/tips, injury news) → enrichments written back to player records (then saved to player_data).
     - **Embeddings (optional):** Enriched players → EmbeddingFilter → player_embeddings.json + scores.
     - **Team building / GW update:** DataService (gameweek data) + optional TeamManager (current team) → TeamBuildingStrategy → LLM → Validator → team JSON (and optional save via TeamManager).
     - **CLI:** main.py / __main__.py calling FPLAgent (fetch, enrich, build_team, gw_update).
   - **Code ref:** Module map: `fpl_agent/data/` (fetch_fpl, data_store, data_processor, data_service, embedding_filter), `fpl_agent/strategies/` (base_strategy, team_analysis_strategy, team_building_strategy, llm_engine, openrouter_engine, llm_factory), `fpl_agent/core/` (config, team_manager), `fpl_agent/main.py`.

2. **Data layer**
   - FPL API: endpoints, rate limits, User-Agent. **Code ref:** `fetch_fpl.py` (base_url, _make_request, get_fpl_static_data, get_fixtures).
   - Processing: bootstrap-static → per-player dict (position, team_name, cost, form, etc.). **Code ref:** `data_processor.py` (`process_fpl_data`, `_process_player`, `process_fixtures_data`).
   - Storage: shared vs per-team. **Code ref:** `data_store.py` (shared_dir, player_data_file, load/save_player_data, fixtures); `team_manager.py` for team-specific gw files.

3. **Enrichment layer**
   - Goal: add expert_insights and injury_news per player for use in prompts.
   - Flow: group players by team → for each team, call TeamAnalysisStrategy (hints/tips + injury news) → merge back. **Code ref:** `main.py` `enrich()` (group_players_by_team, TeamAnalysisStrategy.get_team_hints_tips / get_team_injury_news, _add_enrichments_to_players); `team_analysis_strategy.py` (prompts, create_player_schema).
   - Missing enrichments: **Code ref:** `missing_enrichments.py`, `_process_missing_enrichments_with_retries` in main (mixed-team prompts for missing players).

4. **Strategy layer**
   - Base: config, LLM engine (factory), data service. **Code ref:** `base_strategy.py`.
   - Team building: create_team, update_team_weekly; prompts and schema. **Code ref:** `team_building_strategy.py`.
   - Team analysis: get_team_hints_tips, get_team_injury_news, get_mixed_team_* for gaps. **Code ref:** `team_analysis_strategy.py`.

5. **Configuration and environment**
   - **Code ref:** `config.yaml` (fpl, llm, team, embeddings); `core/config.py` (get_llm_model_config, get_embeddings_config, env overrides for API keys).

6. **Example in terms of `player_data copy 2.json`**
   - After fetch + enrich + (optional) embeddings, the stored file looks like `player_data copy 2.json`: each player has FPL fields plus `expert_insights`, `injury_news`, and optionally `embedding_score`, `keyword_bonus`, `hybrid_score`.
   - Diagram should show where this file is produced: DataStore after enrich (and after embedding scores are merged in main).

7. **Challenges**
   - Keeping bootstrap and fixtures in sync; cache invalidation.
   - Enrichment cost (one LLM call per team + mixed-team fallback); batching and retries in `missing_enrichment_retries` in config.

**Technical depth:** Medium. Diagram + short code references.  
**Example data:** Reference `player_data copy 2.json` as the “enriched + optionally ranked” artifact of this architecture.

---

## Post 4: RAG (Retrieval-Augmented Generation)

**Tone:** Technical; RAG = what we retrieve (data + enrichments) and how we generate (same single prompt, but with richer context).

### Purpose
- Define RAG in this project: “retrieve” = FPL data + LLM-generated expert insights and injury news; “generate” = team selection / weekly update from one prompt that includes that retrieved context.
- Show how enrichments are produced, stored, and injected into the prompt.

### Outline

1. **What we mean by RAG here**
   - Not classic doc retrieval: we don’t search a vector DB. We “retrieve” by (a) loading FPL data and (b) generating and attaching enrichments (expert_insights, injury_news) to each player, then passing that into the same team-building prompt.
   - **Code ref:** `main.py` build_team with `rag_mode="enrichments"` (use_enrichments=True, use_ranking=False): prompt includes enrichments; no embedding filter.

2. **Retrieval side**
   - **Structured data:** FPL API → processed players and fixtures (see Post 2–3).
   - **Enrichments:** Per-team LLM calls produce expert_insights and injury_news; merged into player dict and saved. **Code ref:** `main.py` `enrich()`; `team_analysis_strategy.py` (`_create_hints_tips_prompt`, `_create_injury_news_prompt`, `_create_mixed_*` for missing); `data_service.store.save_player_data(enriched_data)`; `_add_enrichments_to_players`.
   - Where it lives: same `player_data.json` (or copy) structure as `player_data copy 2.json`: `players` with `expert_insights` and `injury_news` per player.

3. **Augmentation: how enrichments get into the prompt**
   - When building the player list for the team-building prompt we pass `use_enrichments=True` so each line can include [EXPERT INSIGHTS] and [INJURY NEWS]. **Code ref:** `prompt_formatter.py` `format_player` (include_enrichments); `format_player_list` (use_enrichments); `team_building_strategy.py` `_get_prompt_intro(use_enrichments=True)`.
   - Intro text that explains the list (“expert insights and injury news are below…”). **Code ref:** `_get_prompt_intro` in team_building_strategy.py (lines ~510–528).

4. **Generation side**
   - Unchanged from Post 2: same TeamBuildingStrategy prompt + schema + validator; only the content of the player list is richer.
   - **Code ref:** `create_team` / `update_team_weekly` with use_enrichments=True; schema and validation as before.

5. **End-to-end RAG flow**
   - fetch (optional) → enrich (if not cached) → load gameweek data (with enrichments) → build prompt (with [EXPERT INSIGHTS] / [INJURY NEWS]) → LLM → parse/validate → output.
   - **Code ref:** `main.py` build_team when rag_mode="enrichments".

6. **Example output with `player_data copy 2.json`**
   - Use the file as the “retrieved” context: pick 2–3 players (e.g. David Raya Martín, one MID, one FWD) and show their lines in the prompt including `expert_insights` and `injury_news` (as in the JSON).
   - Show the same players’ entries in a **sample prompt fragment** (formatted via `format_player` with include_enrichments=True).
   - Show a **short example team output** (e.g. captain + 2 starters with reasons that reference “expert insights” or “injury news”).

7. **Advantages**
   - Better decisions from expert/injury context; model can cite “recommended” or “fit” in reasons.
   - Same pipeline as single prompt; only the data passed in is richer.

8. **Challenges**
   - Token growth: every player still in the prompt; need filtering/ranking next (Post 5).
   - Enrichment quality and consistency (Must-have / Avoid / Rotation risk); keyword extraction used later for hybrid score.

**Technical depth:** Medium–high. Code paths for retrieval (enrich) and augmentation (format_player, prompt intro).  
**Example data:** Snippets from `player_data copy 2.json` (expert_insights, injury_news) and corresponding prompt fragment + example team JSON.

---

## Post 5: Advanced RAG to Reduce Noise

**Tone:** Most technical; embeddings, hybrid scoring, and prompt trimming.

### Purpose
- Reduce noise and token usage by (a) ranking players with embeddings + keyword bonus (hybrid score), and (b) trimming the list per position before putting it in the prompt.
- Full RAG mode: enrichments + ranking = “advanced RAG”.

### Outline

1. **The noise problem**
   - With 600+ players and enrichments, the prompt is huge and expensive; many players are irrelevant. We want “top N per position” that match “must-have / recommended / fit” style.

2. **Embeddings**
   - Encode each player’s text: name, team, position, expert_insights, injury_news. **Code ref:** `embedding_filter.py` `_encode_players` (text_parts, model.encode, batch_size from config).
   - Model and cache: **Code ref:** config `embeddings.model` (e.g. BAAI/bge-base-en-v1.5), `_load_embeddings_model`, `_load_cached_embeddings`, `_save_embeddings_cache`, `calculate_player_embeddings(use_cached=...)`.
   - Only enriched players get embeddings. **Code ref:** `_has_enrichments`; filter before `_encode_players`.

3. **Position queries and similarity**
   - Per-position query strings (e.g. “Must-have OR recommended, fit, high points…”). **Code ref:** config `embeddings.position_queries`; `_encode_queries`; `_calculate_similarities` (cosine_similarity per position).
   - **Code ref:** `_get_player_positions` from player data; similarities dict: position → list of (player_name, score).

4. **Hybrid scoring**
   - Combine embedding similarity with keyword bonus from expert_insights (must-have, recommended, rotation risk, avoid). **Code ref:** `keyword_extractor.py` `extract_expert_bonus`; `embedding_filter.py` `_calculate_hybrid_scores` (embedding_weight, keyword_weight from config `embeddings.hybrid_scoring`).
   - Result: per-player `embedding_score`, `keyword_bonus`, `hybrid_score`; add to player dict. **Code ref:** `calculate_player_embedding_scores`; `main.py` `_add_embedding_scores_to_players`.

5. **Selection counts (trimming the list)**
   - Top K per position (e.g. GK 10, DEF 40, MID 50, FWD 20) so the prompt only gets a shortlist. **Code ref:** config `embeddings.selection_counts`; `prompt_formatter.py` `format_player_list` when use_ranking=True and selection_counts is set (sorted by hybrid_score, then slice per position).
   - **Code ref:** `team_building_strategy.py` _create_team_creation_prompt passes selection_counts when use_ranking=True (from config).

6. **Full flow: advanced RAG**
   - fetch → enrich → compute embeddings (or load cache) → compute hybrid scores → merge scores into players → get_gameweek_data (filter unavailable if desired) → build prompt with use_enrichments=True, use_ranking=True → only top N per position in prompt → LLM → parse/validate.
   - **Code ref:** `main.py` build_team with rag_mode="ranked_enrichments" (use_enrichments=True, use_ranking=True); enrich() calling EmbeddingFilter and _add_embedding_scores_to_players; format_player_list(..., use_ranking=True, selection_counts=...).

7. **Filtering unavailable players**
   - Optional: drop players with chance_of_playing < 25 or injury_news “Out”. **Code ref:** `data_service._filter_available_players_by_chance_of_playing`, `_filter_by_injury_news` (uses `keyword_extractor.extract_injury_status`); `get_players(filter_unavailable_players_mode=...)`.

8. **Example output with `player_data copy 2.json`**
   - Point to fields: `embedding_score`, `keyword_bonus`, `hybrid_score` (e.g. David Raya Martín in the file).
   - Show **prompt fragment**: one position (e.g. GK) with top 5–10 players, each with rank number, stats, [EXPERT INSIGHTS], [INJURY NEWS], and hybrid/embedding scores if shown in format_player.
   - Show **example team output** (2–3 picks) and briefly note that reasoning can reference “ranked list” or “expert insights”.

9. **Advantages**
   - Smaller, focused prompt; lower cost and fewer irrelevant options.
   - Ranking reflects both semantic fit (embeddings) and explicit keywords (Must-have / Avoid).

10. **Challenges**
    - Embedding model and position queries are tunable; bad queries = bad shortlist.
    - Cache invalidation when new players or new enrichments; selection_counts trade-off (too small = miss good options, too large = token growth).
    - OpenRouter payload size limit (~1MB): **Code ref** openrouter_engine.py (payload size log/warning); trimming via selection_counts directly addresses this.

**Technical depth:** High. Embedding pipeline, hybrid formula, and prompt_formatter logic.  
**Example data:** `player_data copy 2.json` (embedding_score, keyword_bonus, hybrid_score); one position’s ranked prompt fragment; one small team output snippet.

---

## Cross-Post Technical Checklist

Use this to ensure the series collectively covers:

| Topic | Post(s) | Code / Config |
|-------|--------|----------------|
| FPL API (endpoints, usage) | 2, 3 | `fetch_fpl.py`, `data_service.get_players` / `get_fixtures` |
| LLM APIs (Gemini, OpenRouter) | 2, 3 | `llm_engine.py`, `openrouter_engine.py`, `llm_factory.py`, `config.yaml` llm.* |
| Prompts (team creation, weekly update, hints/tips, injury) | 2, 4, 5 | `team_building_strategy.py` (_create_*_prompt, _get_prompt_intro), `team_analysis_strategy.py` (_create_*_prompt), `prompt_formatter.py` |
| Enriching player data (expert_insights, injury_news) | 3, 4 | `main.py` enrich(), `team_analysis_strategy.py`, `missing_enrichments.py`, `_add_enrichments_to_players` |
| Embeddings (encode, cache, position queries) | 5 | `embedding_filter.py`, config embeddings.* |
| Hybrid scoring (embedding + keyword) | 5 | `embedding_filter.py` _calculate_hybrid_scores, `keyword_extractor.py` extract_expert_bonus |
| RAG modes (none / enrichments / ranked_enrichments) | 2, 4, 5 | `main.py` build_team / gw_update rag_mode, use_enrichments, use_ranking |
| Schemas and validation | 2 | `schemas.py`, `validator.py` |
| Data store and player_data structure | 3, 4, 5 | `data_store.py`, `player_data copy 2.json` structure |

---

## Example Data Reference: `player_data copy 2.json`

**Location:** `team_data/shared/player_data copy 2.json`

**Structure:**
- Top-level: `"players"`: object keyed by player full name.
- Each player has:
  - FPL fields: `id`, `full_name`, `team_name`, `position`, `now_cost`, `form`, `total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `saves`, `bps`, `ict_index`, `chance_of_playing`, etc.
  - Enrichments: `expert_insights`, `injury_news`.
  - Ranking (advanced RAG): `embedding_score`, `keyword_bonus`, `hybrid_score`.

**Use in posts:**
- Post 2: Use FPL fields only (or a subset) to show “single prompt” player line.
- Post 4: Use `expert_insights` and `injury_news` to show RAG prompt lines and example team reasons.
- Post 5: Use `embedding_score`, `keyword_bonus`, `hybrid_score` and selection_counts to show ranked prompt fragment and smaller payload.

---

*Outline complete. You can now draft each post from these sections and code references.*


Post A — Architecture, pipeline & validation (the big, meaty foundation)
Purpose: show the end-to-end system, where data comes from, where enrichment and ranking fit, and how validity is enforced.
Must include:
One clear diagram (data → processor → datastore → enricher → team builder → validator). Annotate where files like player_data.json and embeddings live.
The single-prompt baseline (prompt fragment, synthetic model output, validator failure). This is the motivating experiment.
Data layer details: FPL API endpoints (bootstrap-static, fixtures), caching, rate limits.
Validation: schema, checks, and how failures are handled (retry, correction loop).
Short practical notes on infra (caching, cron/enqueue, cost considerations).
Code references / module map so readers can find the functions you later reference.
Avoid: deep RAG mechanics (embeddings, hybrid scoring) — only point to them as later steps in the diagram.
Length: medium–long. This is the “how it all fits” post.


Post B — Basic RAG: retrieve FPL data + LLM enrichments (the practical middle)
Purpose: show the simple retrieval + generation loop that materially improves reasoning: enrich each player with expert_insights + injury_news and pass those into the same prompt.
Must include:
Recap of the baseline failure (1–2 lines) — link to Post A, don’t repeat the example.
How “R” is implemented here: loading player_data.json, generating expert_insights and injury_news via LLM per team, merging enrichments.
Prompt fragment showing a few player lines with [EXPERT_INSIGHTS] and [INJURY_NEWS].
Example output where the model cites enrichments in reasons (concrete sample).
Practical considerations: cost (enriching many teams), latency, caching enrichments, fallback (mixed-team prompts for missing players).
Token impact analysis and the observation that token bloat pushes you to Post C.
Avoid: low-level infra or embedding math. Focus: “this makes the model smarter in context, but it creates scale problems.”
Length: focused; practical with examples.


Post C — Advanced RAG: embeddings, hybrid scoring, shortlist & trim (the production step)
Purpose: solve token bloat and noise: select the right candidate subset for the model to consider.
Must include:
Why simple RAG still fails at scale (quantitative token counts and example of irrelevant players).
Embedding pipeline: input text parts, model, cache, batch sizing.
Position queries and per-position similarity + hybrid scoring formula (embedding_score × w + keyword_bonus × (1−w) or similar).
Selection policy: top-K per position, rules for trimming, and optional availability filters (chance_of_playing).
Example: show GK top-N shortlist with scores, the prompt fragment after trimming, and final team JSON.
Tuning notes: selection_counts trade-offs, query phrasing, cache invalidation strategies, eval metrics (validator pass rate, token costs, hit-rate for “must-have” picks).
Practical pitfalls: poor queries, stale enrichments, payload limits (OpenRouter etc.), and how you monitor for missed players.
Avoid: re-explaining the data fetcher or the single-prompt baseline in full — assume knowledge from Posts A/B.
Length: deep and technical; this is the “how to make it production ready” post.