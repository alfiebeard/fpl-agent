# RAG (Retrieval-Augmented Generation) — Technical Reference

This document describes how RAG is implemented in the FPL agent: retrieval (FPL data + enrichments), the enrichment pipeline (per-team and mixed-team agents), and the advanced path (embeddings, hybrid scoring, shortlist trimming). Use it as the technical source for a combined RAG blog post.

---

## 1. What “RAG” Means Here

In this project, **RAG** is not classic document retrieval over a vector database. It means:

- **Retrieve:** (a) Load FPL player and fixture data; (b) Attach LLM-generated **expert_insights** and **injury_news** to each player (enrichments); optionally (c) Score and trim players with embeddings + hybrid scoring so only a shortlist goes into the prompt.
- **Generate:** One team-building (or weekly-update) prompt that includes the retrieved context; the LLM returns team selection and reasons.

So “retrieval” = data load + enrichment pipeline + optional ranking/shortlist. “Augmentation” = that context is injected into the prompt. “Generation” = the same single prompt that produces the team or weekly update.

---

## 2. RAG Modes and Where They Are Used

Three modes are supported and map to `use_enrichments` and `use_ranking`:

| Mode | `rag_mode` | `use_enrichments` | `use_ranking` | Behavior |
|------|------------|-------------------|---------------|----------|
| None | `"none"` | False | False | Raw FPL data only; no enrichments; no embedding shortlist. |
| Basic RAG | `"enrichments"` | True | False | Prompt includes expert_insights and injury_news for all (filtered) players; no ranking/shortlist. |
| Advanced RAG | `"ranked_enrichments"` | True | True | Enrichments + embedding/hybrid scores; prompt shows only top-K per position (shortlist). |

**Code refs:** `fpl_agent/main.py` — `build_team()` and `gw_update()`: `rag_mode` is parsed into `use_enrichments` and `use_ranking` (lines ~368–378 for build_team, ~446–452 for gw_update). These flags are passed through to `fetch_fpl_data()`, `create_team()` / `update_team_weekly()`, and into prompt building.

---

## 3. Data Flow and Where Data Lives

### 3.1 Stored artifact: `player_data.json`

- **Path:** `team_data/shared/player_data.json` (via `DataStore.player_data_file`).
- **Produced by:** Fetch (FPL API → processor → save); then optionally `enrich()` (enrichments + optional embedding scores) and save again.

**Structure:**

- Top-level keys include:
  - `players`: dict keyed by **player full name** (e.g. `"Erling Haaland"`). Each value is one player object.
  - `cache_timestamp`, `total_players` (and optionally `enrichment_timestamp` after enrich).
- Each **player** object contains:
  - **FPL fields:** `id`, `full_name`, `team_name`, `position`, `now_cost`, `form`, `total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `saves`, `bps`, `ict_index`, `chance_of_playing`, etc.
  - **Enrichments (after enrich):** `expert_insights`, `injury_news` (strings).
  - **Ranking (after embedding step):** `embedding_score`, `keyword_bonus`, `hybrid_score`.

**Code refs:** `fpl_agent/data/data_store.py` — `load_player_data()`, `save_player_data()`. Save accepts either `{ 'players': {...} }` or raw player dict; both are normalized to the structure above.

### 3.2 Loading data for the pipeline

- **get_all_gameweek_data(gameweek, use_cached, filter_unavailable_players_mode)** returns `{ 'players': {...}, 'fixtures': [...] }`.
- **get_players(use_cached, filter_unavailable_players_mode)** loads from store (`load_player_data()` → `data['players']`), then optionally filters unavailable players.
- When **use_enrichments** is True and **use_cached** is False, `fetch_fpl_data()` calls `enrich(all_gameweek_data, gameweek)` after getting gameweek data, which writes enrichments (and optionally scores) back into the in-memory `players` dict and then saves to `player_data.json`.

**Code refs:** `fpl_agent/data/data_service.py` — `get_all_gameweek_data()`, `get_players()`; `fpl_agent/main.py` — `fetch_fpl_data()` (and `enrich()` call).

---

## 4. Retrieval Side — Basic: FPL Data + Enrichments

### 4.1 FPL data

- FPL data is fetched via `FPLDataFetcher`, processed by `DataProcessor`, and stored/loaded via `DataStore` (see architecture doc). For RAG we only need: **load** from `player_data.json` (and optionally fixtures). No embedding or vector search at this stage.

### 4.2 Enrichment pipeline (two “agents” per team)

Enrichments are produced by **TeamAnalysisStrategy** (separate LLM strategy from team building). Two kinds of enrichment per player:

1. **expert_insights** — hints/tips/recommendation: one of `Must-have`, `Recommended`, `Rotation risk`, `Avoid` plus a short sentence.
2. **injury_news** — availability: one of `Fit`, `Minor doubt`, `Major doubt`, `Out` plus a short sentence.

**Per-team flow:**

1. **Group players by team:** `group_players_by_team(players)` → `{ team_name: { player_name: player_data } }`.
2. For **each team**:
   - Get **fixture context:** `get_team_fixture_info(team_name, fixtures, gameweek)` → `fixture_str`, `is_double_gameweek`, `fixture_difficulty`.
   - **Expert insights:** `TeamAnalysisStrategy.get_team_hints_tips(team_name, team_players, gameweek, fixture_info)` → one LLM call per team; returns `Dict[player_name, str]`.
   - **Injury news:** `TeamAnalysisStrategy.get_team_injury_news(team_name, team_players, gameweek, fixture_info)` → one LLM call per team; returns `Dict[player_name, str]`.
   - **Merge into global player dict:** `_add_enrichments_to_players(all_gameweek_data['players'], team_players_list, expert_insights, injury_news)` (writes `expert_insights` and `injury_news` onto each player in place).

**Code refs:**

- `fpl_agent/main.py`: `enrich()` — loop over `group_players_by_team(all_gameweek_data['players'])`, call `get_team_hints_tips` and `get_team_injury_news`, then `_add_enrichments_to_players`; finally `_process_missing_enrichments_with_retries` and optionally embedding scoring and save.
- `fpl_agent/utils/team_utils.py`: `group_players_by_team()`, `get_team_fixture_info()`.
- `fpl_agent/strategies/team_analysis_strategy.py`: `get_team_hints_tips()`, `get_team_injury_news()`, `_create_hints_tips_prompt()`, `_create_injury_news_prompt()`.
- `fpl_agent/main.py`: `_add_enrichments_to_players()` — iterates over players and sets `players_data[name]['expert_insights']` and `players_data[name]['injury_news']` when provided.

### 4.3 Enrichment prompts (per team)

- **Hints/tips:** Prompt includes gameweek, team name, fixture string and difficulty, and a **squad list** (formatted without enrichments). Asks for JSON mapping each player name to one line: `"<Status> - <sentence>"` with status in `Must-have`, `Recommended`, `Avoid`, `Rotation risk`.
- **Injury news:** Same structure; status in `Fit`, `Minor doubt`, `Major doubt`, `Out`.
- Squad list is built with `PromptFormatter.format_player_list(..., use_enrichments=False, use_ranking=False)` so the enrichment prompts see only FPL stats, not prior enrichments.
- **Schema:** `create_player_schema(team_players.keys())` defines the expected JSON shape (player name → string). Response is parsed with `Validator.parse_llm_json_response(..., expected_type="hints/tips" | "injury news")`.

**Code refs:** `fpl_agent/strategies/team_analysis_strategy.py` — `_create_hints_tips_prompt()`, `_create_injury_news_prompt()`; `PromptFormatter.format_player_list()`, `format_team_analysis_output_prompt_structure()`.

### 4.3a Enrichment prompts explained (with examples)

Both prompts follow the same pattern: **gameweek context** (season, GW, team, fixture, difficulty) → **squad list** (FPL stats only, no enrichments) → **task** (return one line per player: `Status - sentence`) → **decision criteria** → **output**: valid JSON only, keys = exact player names from the list.

---

**Hints/tips prompt**

- **Goal:** One line per player: pick a status (**Must-have**, **Recommended**, **Rotation risk**, **Avoid**) and a short sentence (form, minutes, fixtures, set pieces, etc.). Model can use web search.
- **Squad in prompt:** `PromptFormatter.format_player_list(team_players, use_enrichments=False, use_ranking=False)` — so each line is e.g. `Player Name (Position, £X.Xm)` then `[STATS] PPG: ..., Form: ..., ...`.
- **Required output:** JSON object where each key is a player name (exactly as in the squad list) and each value is the single line string `"<Status> - <sentence>"`.

**Prompt skeleton (hints/tips):**

```
Your task is to collate the Fantasy Premier League (FPL) hints, tips, and recommendations for players in the {team_name} squad. ...

GAMEWEEK CONTEXT:
- Season: 2025/2026
- Gameweek: {current_gameweek}
- Team: {team_name}
- Fixture: {team_name} are {fixture_str}
- Fixture difficulty: {fixture_difficulty}

{team_name.upper()} SQUAD:
[formatted player list - name, position, price, [STATS] only]

YOUR TASK
For each player ... provide one short sentence in the format:
INSERT_PLAYER_TIP_STATUS - <short sentence>
- INSERT_PLAYER_TIP_STATUS must be one of: Must-have, Recommended, Avoid, Rotation risk.
...

JSON STRUCTURE:
{PromptFormatter.format_team_analysis_output_prompt_structure(team_players)}
→ e.g. {"Erling Haaland": "", "Phil Foden": "", ...}

Important: You MUST respond with ONLY valid JSON.
```

**Example hints/tips output (JSON):**

```json
{
  "Erling Haaland": "Must-have - Haaland is starting every match, in excellent form, and has a favorable fixture.",
  "Phil Foden": "Recommended - Foden is on set pieces and in good form; minor rotation risk with Europe.",
  "Rico Lewis": "Rotation risk - Could start but faces competition; check lineups before deadline.",
  "Kalvin Phillips": "Avoid - Not starting and likely to leave in January."
}
```

These strings are stored as `player['expert_insights']` and later shown in the team-building prompt as `[EXPERT INSIGHTS] <value>`.

---

**Injury news prompt**

- **Goal:** One line per player: pick an availability status (**Fit**, **Minor doubt**, **Major doubt**, **Out**) and a short sentence (injury, suspension, international duty, return date, etc.). Model can use web search.
- **Squad in prompt:** Same as above — FPL stats only.
- **Required output:** JSON object, keys = player names, values = `"<Status> - <sentence>"`.

**Prompt skeleton (injury news):**

```
Your task is to collate the latest injury news on players in the {team_name} squad. ...

GAMEWEEK CONTEXT:
[same as hints/tips]

{team_name.upper()} SQUAD:
[same formatted list]

YOUR TASK
For each player ... provide one short sentence in the format:
INSERT_PLAYER_AVAILABILITY_STATUS - <short sentence>
- INSERT_PLAYER_AVAILABILITY_STATUS must be one of: Fit, Minor doubt, Major doubt, Out.
...

JSON STRUCTURE:
[same player-name keys, empty strings]
```

**Example injury news output (JSON):**

```json
{
  "Erling Haaland": "Fit - Haaland is fit and available for selection.",
  "Phil Foden": "Fit - No injury concerns; available.",
  "Rico Lewis": "Minor doubt - Small knock; expected to be assessed before the game.",
  "Kalvin Phillips": "Out - Not in squad; expected to leave on loan in January."
}
```

These strings are stored as `player['injury_news']` and shown in the team-building prompt as `[INJURY NEWS] <value>`. The keyword **Out** is also used for optional filtering (e.g. drop from candidate list).

---

**How they’re used**

- Parser expects **only** valid JSON; keys must match the squad list exactly. Any missing or renamed player is handled later by the missing-enrichments (mixed-team) cleanup.
- The **first token** of `expert_insights` (before `" - "`) is used for hybrid scoring: Must-have → +0.5, Recommended → +0.3, Rotation risk → -0.2, Avoid → -0.5. The first token of `injury_news` is used for availability filtering (e.g. **Out** → exclude).

### 4.4 Missing enrichments (mixed-team fallback)

Some team-level LLM calls can omit players (e.g. parsing or model behaviour). Missing enrichments are filled with **mixed-team** prompts that take a **set of players from different teams** in one go.

- **Detection:** `get_missing_enrichments_from_data(players_data)` returns `{ 'expert_insights': [names], 'injury_news': [names] }` by checking each player for valid `expert_insights` / `injury_news` (non-empty and not sentinel values like `"No expert insights available"`).
- **Processing:** `_process_missing_enrichments_with_retries()` runs up to `max_passes` (config: `embeddings.missing_enrichment_retries.max_passes`). Each pass:
  - Calls `get_missing_enrichments_from_data(all_gameweek_data['players'])`.
  - If any missing: for expert_insights calls `get_mixed_team_expert_insights(missing_players_data, gameweek, fixtures)`; for injury_news calls `get_mixed_team_injury_news(...)`; then `_add_enrichments_to_players()` for the returned keys.
  - Stops when no missing remain or no progress (same or increased missing count).
- **Mixed prompts:** Same task as per-team (status + sentence per player), but the squad list is a single list of players from multiple teams; fixture block is the full gameweek fixtures. Same JSON schema and validator.

**Code refs:** `fpl_agent/utils/missing_enrichments.py` — `get_missing_enrichments_from_data()`, `_has_valid_expert_insights`, `_has_valid_injury_news`; `fpl_agent/main.py` — `_process_missing_enrichments_with_retries()`, `_process_missing_enrichments()`; `fpl_agent/strategies/team_analysis_strategy.py` — `get_mixed_team_expert_insights()`, `get_mixed_team_injury_news()`, `_create_mixed_hints_tips_prompt()`, `_create_mixed_team_injury_news_prompt()`.

**Config:** `config.yaml` → `embeddings.missing_enrichment_retries`: `max_passes`, `min_progress_threshold`.

---

## 5. Augmentation: How Enrichments Get Into the Prompt

When building the **team-creation** or **weekly-update** prompt, the player list is formatted with `PromptFormatter.format_player_list(players_data, use_enrichments=..., use_ranking=..., selection_counts=...)`.

- **Without ranking:** Players are grouped by **team**; within team, sorted by position then total points. Each player line is produced by `format_player(..., include_enrichments=use_enrichments)`.
- **With ranking:** Players are grouped by **position**; within position, sorted by `hybrid_score` descending; then **trimmed to top K per position** using `selection_counts` (see below). Each line again uses `format_player(..., include_enrichments=use_enrichments, include_rankings=use_ranking)`.

**Single player line (format_player):**

- First line: name, (team or position), price (and optionally sale/purchase prices).
- Second line: `[STATS]` — PPG, form, total points, minutes, position-specific stats (goals/assists or clean sheets/saves etc.), bonus, BPS, ICT, ownership, availability.
- If **include_rankings:** line like `[HYBRID EMBEDDING SCORE] <hybrid_score> (Embedding: <embedding_score>, Keyword Bonus: <keyword_bonus>)`.
- If **include_enrichments:**  
  - `[EXPERT INSIGHTS] <expert_insights>`  
  - `[INJURY NEWS] <injury_news>`  
  (only if present and not sentinel values.)

So the model sees explicit `[EXPERT INSIGHTS]` and `[INJURY NEWS]` lines and can cite them in reasons.

**Prompt intro when use_enrichments=True:** Text explains that the list includes “preliminary score, expert insights and injury news” and that ranking is “loose” and embedding-based, and to use it as a starting point, not the only source.

**Code refs:** `fpl_agent/utils/prompt_formatter.py` — `format_player_list()`, `format_player()` (especially stats line, score line, `[EXPERT INSIGHTS]` / `[INJURY NEWS]`); `fpl_agent/strategies/team_building_strategy.py` — `_create_team_creation_prompt()`, `_create_weekly_update_prompt()`, `_get_prompt_intro(use_enrichments=...)`; both prompts call `PromptFormatter.format_player_list(..., use_enrichments, use_ranking, selection_counts)`.

---

## 6. Why Simple RAG (Enrichments-Only) Runs Into Scale Issues

- **Token bloat:** With enrichments, every (filtered) player gets two extra lines. With 400+ players that can be tens of thousands of tokens, which is expensive and can exceed context/payload limits (e.g. OpenRouter).
- **Noise:** Many players are irrelevant for a given gameweek (low form, bad fixtures, rotation). Putting everyone in the prompt dilutes the signal.
- **Solution:** Restrict the prompt to a **shortlist** of candidates per position, chosen by **embedding + keyword hybrid score** (advanced RAG).

---

## 7. Advanced RAG: Embeddings, Hybrid Scoring, Shortlist

### 7.1 Overview

After all enrichments are in place, the pipeline can compute **embedding scores** and **hybrid scores**, attach them to each player, then when building the prompt **sort by position by hybrid_score** and **take top K per position** so the model only sees a shortlist (e.g. 10 GK, 40 DEF, 50 MID, 20 FWD).

### 7.2 Embedding pipeline

**Class:** `EmbeddingFilter` (`fpl_agent/data/embedding_filter.py`). Config: `config.yaml` → `embeddings`.

**Input text per player (for encoding):** Concatenation of: `full_name`, `team_name`, `element_type`, and if present `expert_insights` and `injury_news`, joined by `" | "`. So the embedding represents “who they are + what the experts say + injury/availability”.

**Model:** Sentence-transformers model from config (`embeddings.model`, default `BAAI/bge-base-en-v1.5`). Device from `embeddings.device` (e.g. `"auto"` → cuda/mps/cpu).

**Encoding:**

- **Players:** `_encode_players(players_data)` builds the text per player, then `model.encode(player_texts, show_progress_bar=True, batch_size=batch_size)`. Only players with “meaningful” enrichments are included (`_has_enrichments`: expert_insights and injury_news non-empty and not sentinel).
- **Queries:** `_encode_queries()` encodes the four **position_queries** (one string per position from config). Used as the target vectors for similarity.

**Caching:**

- **Path:** `team_data/shared/player_embeddings.json`.
- **Contents:** `cache_timestamp`, `embeddings` (dict: player_name → embedding), `total_players`. Embeddings are serialized (e.g. list of floats) for JSON.
- **Expiry:** `embeddings.cache_enabled`, `cache_expiry_hours`; if cache is used and older than expiry, a warning is logged but data is still used.
- **When:** On first run with `rank_players=True`, embeddings are computed and cached; later runs can use `use_cached=True` to load from file (caller passes this into `calculate_player_embeddings(..., use_cached)`).

**Code refs:** `embedding_filter.py` — `_load_embeddings_model()`, `_encode_players()`, `_encode_queries()`, `_get_embeddings_cache_path()`, `_load_cached_embeddings()`, `_save_embeddings_cache()`, `calculate_player_embeddings()`; config `embeddings.model`, `batch_size`, `device`, `cache_enabled`, `cache_expiry_hours`.

### 7.2a Step-by-step explanation (with code snippets)

This subsection explains the embedding → similarity → hybrid → shortlist pipeline in plain language with the actual code.

---

**Step 1: What we embed (one text blob per player)**

Each player is turned into a single string by concatenating identity + enrichments with `" | "`. That string is then passed to the sentence-transformers model. Only players who already have both `expert_insights` and `injury_news` are embedded (enrichments must exist first).

From `embedding_filter.py` — `_encode_players()`:

```python
for player_name, player_data in players_data.items():
    text_parts = []

    # Add basic player info
    if isinstance(player_data.get('full_name'), str):
        text_parts.append(player_data['full_name'])
    if isinstance(player_data.get('team_name'), str):
        text_parts.append(player_data['team_name'])
    if isinstance(player_data.get('element_type'), str):
        text_parts.append(player_data['element_type'])

    # Add enriched data if available
    if isinstance(player_data.get('expert_insights'), str):
        text_parts.append(player_data['expert_insights'])
    if isinstance(player_data.get('injury_news'), str):
        text_parts.append(player_data['injury_news'])

    if text_parts:
        combined_text = " | ".join(text_parts)   # e.g. "Erling Haaland | Manchester City | FWD | Must-have - ... | Fit - ..."
        player_texts.append(combined_text)
```

So the blob is effectively: **full_name | team_name | position | expert_insights | injury_news**. The model encodes all these strings in one batched call (`model.encode(player_texts, batch_size=...)`), producing one vector per player.

---

**Step 2: We do not “group” players by similarity to each other**

We never cluster players by how similar they are to one another. Instead we define **one query per position** that describes “what a selectable player looks like” for that role. Those queries come from config:

From `config.yaml`:

```yaml
position_queries:
  GK: "Must-have OR recommended, fit, high points, clean sheet, saves, consistent starter, good fixtures. NOT out of form, injured, suspended."
  DEF: "Must-have OR recommended, fit, high points, clean sheet, attacking potential, consistent starter, good fixtures. NOT out of form, injured, suspended."
  MID: "Must-have OR recommended, fit, high points, goals, assists, consistent starter, set pieces, penalties, good fixtures. NOT out of form, injured, suspended."
  FWD: "Must-have OR recommended, fit, high points, goals, assists, consistent starter, set pieces, penalties, good fixtures. NOT out of form, injured, suspended."
```

We embed these four query strings with the **same** model, so we get four query vectors (one per position).

---

**Step 3: Similarity is “player vs their position’s query” only**

For each position (GK, DEF, MID, FWD), we take **only the players who play that position**, and we score each of them against **that position’s query embedding** using cosine similarity. So a midfielder is only compared to the MID query, not to the GK query or to other players.

From `embedding_filter.py` — `_calculate_similarities()`:

```python
for position, query_embedding in query_embeddings.items():
    position_players = []
    position_player_embeddings = []

    # Get all players for this position only
    for player_name, player_embedding in player_embeddings.items():
        if player_positions.get(player_name) == position:
            position_players.append(player_name)
            position_player_embeddings.append(player_embedding)

    # Cosine similarity: one query vector vs all players in this position
    position_embeddings_array = np.array(position_player_embeddings)
    query_embedding_array = query_embedding.reshape(1, -1)
    similarities_array = cosine_similarity(query_embedding_array, position_embeddings_array)[0]

    # (player_name, embedding_score) sorted high to low
    position_similarities = list(zip(position_players, similarities_array))
    position_similarities.sort(key=lambda x: x[1], reverse=True)
    similarities[position] = position_similarities
```

So each player gets exactly **one** embedding score: the similarity to their own position’s query. Output is, per position, a list of `(player_name, embedding_score)` sorted by score descending.

---

**Step 4: Hybrid score = embedding score + keyword bonus from expert_insights**

We don’t use the raw embedding score alone. We add a **keyword bonus** by reading the **first token** of `expert_insights` (the part before `" - "`). That token is one of: Must-have, Recommended, Rotation risk, Avoid. We map them to numbers and combine with the embedding score using configurable weights.

From `keyword_extractor.py` — `extract_expert_bonus()`:

```python
keyword_map = {
    "must-have": 0.5,
    "recommended": 0.3,
    "rotation risk": -0.2,
    "avoid": -0.5
}
# First part of expert_insights before " - " is matched (e.g. "Must-have - Haaland is ..." → 0.5)
result = extract_keyword_status(player_name, structured_data, 'expert_insights', keyword_map)
return result if result is not None else 0.0
```

From `embedding_filter.py` — `_calculate_hybrid_scores()`:

```python
for player_name, embedding_score in player_scores:
    keyword_bonus = extract_expert_bonus(player_name, structured_data)

    embedding_weight = hybrid_config.get('embedding_weight', 0.6)
    keyword_weight = hybrid_config.get('keyword_weight', 0.4)

    final_score = embedding_weight * embedding_score + keyword_weight * keyword_bonus
    hybrid_position_scores.append((player_name, final_score, embedding_score, keyword_bonus))

hybrid_position_scores.sort(key=lambda x: x[1], reverse=True)
```

So: **hybrid = 0.6 × embedding_score + 0.4 × keyword_bonus** (default). We then sort by `hybrid_score` descending within each position.

---

**Step 5: Shortlist = top-K per position**

We attach `embedding_score`, `keyword_bonus`, and `hybrid_score` to each player in the main player dict. When building the team-building prompt with ranking enabled, we **group by position**, sort by `hybrid_score` descending, and **take only the top K per position**. Those K players (with their stats, enrichments, and score line) are the only ones sent to the LLM.

From `config.yaml`:

```yaml
selection_counts:
  GK: 10
  DEF: 40
  MID: 50
  FWD: 20
```

From `prompt_formatter.py` — `format_player_list()` (when `use_ranking=True` and `selection_counts` is set):

```python
# Group by position; sort by hybrid_score descending
valid_players = [p for p in players if p.get('hybrid_score', -1) > -1]
sorted_players = sorted(valid_players, key=lambda p: p.get('hybrid_score', -1), reverse=True)

# Take top K per position
if use_ranking and selection_counts:
    count = selection_counts.get(position, 0)
    sorted_players = sorted_players[:count]

for i, player in enumerate(sorted_players):
    player['_display_rank'] = i + 1
    # ... format line with [STATS], [EXPERT INSIGHTS], [INJURY NEWS], [HYBRID EMBEDDING SCORE]
```

So the model sees at most 10 + 40 + 50 + 20 = 120 players (with enrichments and hybrid score), not 600+.

---

**Summary**

| Step | What happens |
|------|----------------|
| 1 | Build text blob `full_name \| team_name \| position \| expert_insights \| injury_news`; encode with sentence-transformers (e.g. BAAI/bge-base-en-v1.5). |
| 2 | Encode four position queries from config; no grouping of players by similarity to each other. |
| 3 | Per position: cosine similarity between that position’s query and each player in that position only → one embedding score per player. |
| 4 | Keyword bonus from first token of expert_insights (Must-have / Recommended / Rotation risk / Avoid); hybrid = 0.6×embedding + 0.4×keyword; sort by hybrid per position. |
| 5 | Top-K per position (10/40/50/20) go into the prompt; everyone else is dropped from the list the model sees. |

---

**Example output (embedding → shortlist)**

**1. Text blob for one player (input to encoder):**

```
Erling Haaland | Manchester City | FWD | Must-have - Haaland is starting every match, in excellent form, and has a favorable fixture. | Fit - Haaland is fit and available for selection.
```

The model turns this into a single vector (e.g. 768 floats for BGE). We do the same for every enriched player and for the four position-query strings.

**2. Per-position similarity (after Step 3; illustrative numbers):**

For **FWD**, we have one query embedding and compare it to every forward’s embedding. Result is a sorted list of (name, embedding_score), e.g.:

| Player           | embedding_score |
|------------------|-----------------|
| Erling Haaland   | 0.82            |
| Mohamed Salah    | 0.79            |
| Ollie Watkins    | 0.74            |
| ...              | ...             |

**3. Hybrid score (after Step 4):**

Keyword bonus from `expert_insights`: "Must-have" → +0.5, "Recommended" → +0.3, etc. Then:

| Player           | embedding_score | keyword_bonus | hybrid (0.6×emb + 0.4×kw) |
|------------------|-----------------|--------------|---------------------------|
| Erling Haaland   | 0.82            | 0.5          | 0.692                     |
| Mohamed Salah    | 0.79            | 0.5          | 0.674                     |
| Ollie Watkins    | 0.74            | 0.3          | 0.564                     |

We sort by `hybrid` descending and take top 20 for FWD (per `selection_counts`).

**4. What the model sees in the team-building prompt (shortlist):**

Only the top-K per position appear, each with stats, enrichments, and the score line. Example for one forward in the shortlist:

```
 1. Erling Haaland (Manchester City, £14.0m)
[STATS] PPG: 7.2, Form: 7.2, Total Points: 144, Minutes: 1200, Goals: 18, Assists: 6, ...
[EXPERT INSIGHTS] Must-have - Haaland is starting every match, in excellent form, and has a favorable fixture.
[INJURY NEWS] Fit - Haaland is fit and available for selection.
[HYBRID EMBEDDING SCORE] 0.692 (Embedding: 0.820, Keyword Bonus: +0.500)
```

So the model gets at most 120 such blocks (10 GK + 40 DEF + 50 MID + 20 FWD) instead of 600+ players.

### 7.3 Position queries and similarity

- **Position queries** are four strings in config under `embeddings.position_queries` (GK, DEF, MID, FWD). Example: “Must-have OR recommended, fit, high points, clean sheet, saves, consistent starter, good fixtures. NOT out of form, injured, suspended.”
- **Similarity:** For each position, take all players with that `position`; compute **cosine similarity** between the position’s **query embedding** and each player’s embedding. Result: per position a list of `(player_name, embedding_score)` sorted by score descending.
- **Positions** come from `player_data[name]['position']` (GK/DEF/MID/FWD).

**Code refs:** `embedding_filter.py` — `_encode_queries()`, `_get_player_positions()`, `_calculate_similarities()` (uses `sklearn.metrics.pairwise.cosine_similarity`); config `embeddings.position_queries`.

### 7.4 Hybrid scoring formula

For each player (per position), **keyword_bonus** is derived from the **expert_insights** string:

- **Keyword extraction:** `extract_expert_bonus(player_name, structured_data)` in `fpl_agent/utils/keyword_extractor.py`. It takes the part of `expert_insights` **before** the first `" - "` and maps it to a number:
  - `"must-have"` → 0.5  
  - `"recommended"` → 0.3  
  - `"rotation risk"` → -0.2  
  - `"avoid"` → -0.5  
  (config can override in `embeddings.hybrid_scoring.keyword_bonuses`; the code uses a fixed map in `keyword_extractor`.)
- **Hybrid score:**  
  `hybrid_score = embedding_weight * embedding_score + keyword_weight * keyword_bonus`  
  with `embedding_weight` and `keyword_weight` from config (e.g. 0.6 and 0.4). Scores are then sorted by `hybrid_score` descending per position.

**Code refs:** `embedding_filter.py` — `_calculate_hybrid_scores()` (calls `extract_expert_bonus()`); `keyword_extractor.py` — `extract_expert_bonus()`, `extract_keyword_status()`; config `embeddings.hybrid_scoring`.

### 7.5 Attaching scores to players and shortlist (selection_counts)

- **Attachment:** `calculate_player_embedding_scores()` returns a dict `player_name → { 'embedding_score', 'keyword_bonus', 'hybrid_score' }`. In `main.py`, `_add_embedding_scores_to_players(players_data, player_embedding_scores)` updates each player dict in place. Only players that were in the embedding/scoring run get these keys (enriched players only).
- **Shortlist:** In `format_player_list()`, when `use_ranking=True` and `selection_counts` is set:
  - Group by position; filter to players with `hybrid_score > -1`; sort by `hybrid_score` descending.
  - For each position, take **top K** where `K = selection_counts.get(position, 0)` (e.g. GK: 10, DEF: 40, MID: 50, FWD: 20).
  - Only these players are rendered in the prompt; each gets a `_display_rank` (1..K) and the `[HYBRID EMBEDDING SCORE]` line.

**Code refs:** `embedding_filter.py` — `calculate_player_embedding_scores()`; `main.py` — `_add_embedding_scores_to_players()`; `prompt_formatter.py` — `format_player_list()` (grouped_by_position, sort by hybrid_score, slice by `selection_counts`); `team_building_strategy.py` — when `use_ranking` it reads `selection_counts` from `config.get_embeddings_config()['selection_counts']` and passes to `format_player_list()`.

### 7.6 Full advanced RAG flow (code path)

1. **fetch_fpl_data(..., use_enrichments=True)**  
   → get_all_gameweek_data (load or fetch players + fixtures)  
   → enrich(all_gameweek_data, gameweek)  
   → per-team hints/tips + injury news, merge, missing-enrichments passes  
   → EmbeddingFilter.calculate_player_embeddings(players, use_cached=False)  
   → EmbeddingFilter.calculate_player_embedding_scores(embeddings, players)  
   → _add_embedding_scores_to_players(players, scores)  
   → save_player_data({ 'players': players, ... })
2. **build_team(..., rag_mode="ranked_enrichments")**  
   → use_enrichments=True, use_ranking=True  
   → fetch_fpl_data (may use cached data that already has enrichments + scores)  
   → create_team(..., use_enrichments=True, use_ranking=True)  
   → prompt uses selection_counts, format_player_list(..., use_ranking=True, selection_counts=...)  
   → only top K per position in prompt, each with [EXPERT INSIGHTS], [INJURY NEWS], [HYBRID EMBEDDING SCORE].

**Code refs:** `main.py` — `enrich()`, `fetch_fpl_data()`, `build_team()`, `gw_update()`; `team_building_strategy.py` — `create_team()`, `update_team_weekly()`, `_create_team_creation_prompt()`, `_create_weekly_update_prompt()`.

---

## 8. Filtering Unavailable Players (Optional)

Availability filtering can use FPL data only or FPL + enrichments:

- **filter_unavailable_players_mode:**
  - `"no_filter"`: no removal.
  - `"fpl_data_only"`: drop players with `chance_of_playing` < 25 (from FPL).
  - `"fpl_data_and_enrichments"`: apply the above, then drop players whose **injury_news** is parsed as **“Out”** (via `extract_injury_status()` which looks at the part before `" - "` in `injury_news`).

**Code refs:** `data_service.py` — `_filter_out_unavailable_players()`, `_filter_available_players_by_chance_of_playing()`, `_filter_by_injury_news()`; `keyword_extractor.py` — `extract_injury_status()`. Used when `filter_unavailable_players=True` in fetch (e.g. for build_team / gw_update).

---

## 9. Configuration Summary (RAG-Relevant)

| Config path | Purpose |
|-------------|---------|
| `embeddings.use_embeddings` | Master switch for embedding path |
| `embeddings.model` | Sentence-transformers model name |
| `embeddings.batch_size` | Batch size for encoding players |
| `embeddings.device` | Device for model (auto/cpu/cuda/mps) |
| `embeddings.cache_enabled` / `cache_expiry_hours` | Embedding cache |
| `embeddings.position_queries` | Per-position query strings for similarity |
| `embeddings.selection_counts` | Top K per position (GK, DEF, MID, FWD) for shortlist |
| `embeddings.hybrid_scoring.embedding_weight` / `keyword_weight` | Hybrid formula weights |
| `embeddings.hybrid_scoring.keyword_bonuses` | Optional keyword → bonus map |
| `embeddings.missing_enrichment_retries.max_passes` | Max passes for missing enrichments |

---

## 10. Practical Considerations for the Blog

- **Cost:** Enrichments = 2 LLM calls per team (hints/tips + injury) plus up to several mixed-team calls for missing players. With 20 teams that’s 40+ calls per full enrich; caching and `use_cached` reduce repeat cost.
- **Latency:** Enrichment is sequential per team; embedding computation is batched; cache makes subsequent runs faster.
- **Caching:** Enrichments and scores are stored in `player_data.json`; embeddings in `player_embeddings.json`. Age checks and expiry are applied; refreshing is done by re-running fetch with `use_enrichments=True` and not `cached_only`.
- **Token impact:** Basic RAG (enrichments, no ranking) increases prompt size significantly; advanced RAG (ranking + selection_counts) cuts it back to a fixed shortlist size, trading coverage for focus and cost.
- **Fallback:** Missing enrichments are filled by mixed-team prompts so the model still sees [EXPERT INSIGHTS] and [INJURY NEWS] for as many players as possible.
- **Pitfalls:** Stale enrichments if data is old; payload limits if shortlist is too large; over-trimming (selection_counts too small) can drop good picks — tuning selection_counts and query phrasing matters.

---

## 11. File and Symbol Reference

| Topic | File | Symbols |
|-------|------|---------|
| RAG mode parsing, enrich orchestration | `main.py` | `fetch_fpl_data`, `enrich`, `_add_enrichments_to_players`, `_add_embedding_scores_to_players`, `_process_missing_enrichments_with_retries`, `_process_missing_enrichments`, `build_team`, `gw_update` |
| Per-team / mixed enrichments | `team_analysis_strategy.py` | `get_team_hints_tips`, `get_team_injury_news`, `get_mixed_team_expert_insights`, `get_mixed_team_injury_news`, `_create_hints_tips_prompt`, `_create_injury_news_prompt`, `_create_mixed_*` |
| Missing enrichment detection | `missing_enrichments.py` | `get_missing_enrichments_from_data` |
| Prompt text and player lines | `prompt_formatter.py` | `format_player_list`, `format_player`, `format_team_analysis_output_prompt_structure` |
| Team building prompts | `team_building_strategy.py` | `create_team`, `update_team_weekly`, `_create_team_creation_prompt`, `_create_weekly_update_prompt`, `_get_prompt_intro` |
| Embeddings and hybrid scoring | `embedding_filter.py` | `EmbeddingFilter`, `calculate_player_embeddings`, `calculate_player_embedding_scores`, `_encode_players`, `_encode_queries`, `_calculate_similarities`, `_calculate_hybrid_scores` |
| Keyword bonus from expert_insights | `keyword_extractor.py` | `extract_expert_bonus`, `extract_injury_status`, `extract_keyword_status` |
| Data load/save and filtering | `data_store.py`, `data_service.py` | `load_player_data`, `save_player_data`, `get_all_gameweek_data`, `get_players`, `_filter_out_unavailable_players` |
| Team grouping and fixture info | `team_utils.py` | `group_players_by_team`, `get_team_fixture_info` |
| Config | `config.yaml` | `embeddings` (model, cache, position_queries, selection_counts, hybrid_scoring, missing_enrichment_retries) |

This document covers everything needed to describe basic RAG (data + enrichments, prompt injection), the enrichment pipeline (per-team and mixed agents), and advanced RAG (embeddings, hybrid scoring, shortlist) in a single combined blog post.
