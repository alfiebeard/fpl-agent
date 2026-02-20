# FPL Agent Architecture — Technical Reference (Post 2)

This document captures the technical details of each pipeline component for the FPL agent architecture blog post. Use it as a reference when writing each subsection.

---

## Pipeline Overview

```
Data Fetcher → Processor → Data Store → Prompt Builder → LLM Inference → Validator → State Update → Output
```

**Scope:** This covers the core flow only. Enrichments, embeddings, injury news, and hints/tips are covered in Posts 3 & 4.

---

## 1. Data Fetcher

**Purpose:** Pulls raw player and fixture data from the official FPL API.

**Location:** `fpl_agent/data/fetch_fpl.py` — `FPLDataFetcher` class.

### How it works

- Base URL: `https://fantasy.premierleague.com/api/`
- Uses `requests.Session()` with a browser-like User-Agent to reduce blocking
- `_make_request(endpoint)` performs GET requests with a 30s timeout and returns JSON

### Endpoints

| Endpoint | Method | Returns |
|----------|--------|---------|
| `bootstrap-static/` | `get_fpl_static_data()` | All static data: elements (players), teams, events, element_types |
| `fixtures/` | `get_fixtures()` | All fixtures for the season |
| (via bootstrap) | `get_current_gameweek()` | Current gameweek number from events |

### Example usage

```python
from fpl_agent.data.fetch_fpl import FPLDataFetcher
from fpl_agent.core.config import Config

config = Config()
fetcher = FPLDataFetcher(config)

# Fetch all static data (players, teams, gameweeks)
bootstrap_data = fetcher.get_fpl_static_data()

# Fetch fixtures
fixtures = fetcher.get_fixtures()

# Get current gameweek
gw = fetcher.get_current_gameweek()
```

### Raw API data structure (bootstrap-static)

The `bootstrap-static/` response includes:

- **`elements`** — list of player objects with fields such as:
  - `id`, `first_name`, `second_name`, `element_type` (1=GK, 2=DEF, 3=MID, 4=FWD)
  - `team`, `now_cost` (in £0.1m, e.g. 85 = £8.5m)
  - `total_points`, `points_per_game`, `form`, `minutes`
  - `goals_scored`, `assists`, `clean_sheets`, `saves`, etc.
  - `chance_of_playing_this_round`, `chance_of_playing_next_round`
  - `status` (e.g. "a"=available, "i"=injured)
- **`teams`** — list of teams with `id`, `name`, `short_name`
- **`events`** — gameweeks with `id`, `is_current`, etc.

---

## 2. Processor

**Purpose:** Cleans and standardises raw FPL data into a consistent format for the rest of the pipeline.

**Location:** `fpl_agent/data/data_processor.py` — `DataProcessor` class.

### How it works

1. **Players (`process_fpl_data`):**
   - Builds `team_mapping` from `teams` (id → name/short_name)
   - For each entry in `elements`:
     - Maps `element_type` 1/2/3/4 → `GK`/`DEF`/`MID`/`FWD`
     - Maps team ID → `team_name`, `team_short_name`
     - Handles `chance_of_playing` (this round, next round, or 100%)
     - Converts `form` string to float
   - Returns a dict keyed by `"first_name second_name"`

2. **Fixtures (`process_fixtures_data`):**
   - Maps team IDs to team names
   - Produces fixtures with: `event`, `team_h`, `team_a`, `kickoff_time`, `finished`, `team_h_difficulty`, `team_a_difficulty`

### Raw → processed player transformation (excerpt)

**Raw FPL element:**
```json
{
  "id": "123",
  "first_name": "Erling",
  "second_name": "Haaland",
  "element_type": 4,
  "team": 13,
  "now_cost": 145,
  "total_points": 180,
  "form": "8.5",
  "chance_of_playing_this_round": "100",
  "status": "a"
}
```

**Processed output:**
```json
{
  "id": "123",
  "full_name": "Erling Haaland",
  "position": "FWD",
  "team_name": "Man City",
  "team_short_name": "MCI",
  "now_cost": 145,
  "total_points": 180,
  "form": 8.5,
  "chance_of_playing": 100.0,
  "status": "a"
}
```

### Example usage

```python
bootstrap_data = fetcher.get_fpl_static_data()
processed_players = processor.process_fpl_data(bootstrap_data)
# Returns: Dict[str, Dict] keyed by "First Last"
```

---

## 3. Data Store

**Purpose:** Persists processed player and fixture data so it can be reused without repeated API calls.

**Location:** `fpl_agent/data/data_store.py` — `DataStore` class.

### Storage layout

| File | Path | Contents |
|------|------|----------|
| Player data | `team_data/shared/player_data.json` | Players + metadata |
| Fixtures | `team_data/shared/fixtures.json` | Fixtures + metadata |

### Player data format

```json
{
  "cache_timestamp": "2025-02-13T10:30:00.000000",
  "players": {
    "Erling Haaland": { /* processed player object */ },
    "Bukayo Saka": { /* ... */ }
  },
  "total_players": 600
}
```

### Behaviour

- **Save:** Accepts either `{ players: {...} }` or raw player dict; adds `cache_timestamp` and `total_players`
- **Load:** Returns full structure or `None` if file missing
- **Age checks:** Warns if data is >24h (stale) or >7 days (very outdated)

### Example usage

```python
store = DataStore()
store.save_player_data(processed_players)
data = store.load_player_data()
players = data['players']
```

---

## 4. Prompt Builder

**Purpose:** Assembles constraints, fixtures, and player lists into a structured prompt for team creation or weekly updates.

**Location:** `fpl_agent/utils/prompt_formatter.py` — `PromptFormatter`; prompts built in `fpl_agent/strategies/team_building_strategy.py`.

### Components

1. **`format_team_constraints(config)`** — squad size, position limits, formation:
   ```
   * The squad must include exactly 15 players:
     * 2 goalkeepers, 5 defenders, 5 midfielders, 3 forwards
   * The starting 11 must follow valid FPL formations:
     * 1 goalkeeper, 3-5 defenders, 2-5 midfielders, 1-3 forwards
   ```

2. **`format_fixtures(fixtures_data, gameweek)`** — fixtures grouped by date:
   ```
   GAMEWEEK 25 FIXTURES:
   Saturday 15th February 2025:
   • Arsenal vs Sunderland
   • Newcastle vs Brentford
   ```

3. **`format_player_list(players_data, ...)`** — players grouped by position or team, with stats, enrichments, and rankings (when used).

4. **`format_player(player_data, ...)`** — per-player line, e.g.:
   ```
   Erling Haaland (Man City, £14.5m)
   [STATS] PPG: 8.5, Form: 8.5, Total Points: 180, Minutes: 2100, Goals: 24, Assists: 5...
   [EXPERT INSIGHTS] Must-have - fixture proof striker
   [INJURY NEWS] Fully fit
   ```

5. **`format_team(current_team, team_player_data)`** — current squad with sale prices for weekly updates.

6. **`format_chips(chips_data)`** — list of available chips.

### Team creation prompt structure (simplified)

```
You are an FPL team building expert...
Budget: £100m
Constraints: [format_team_constraints]
Fixtures: [format_fixtures]
Players: [format_player_list]
...
Return ONLY valid JSON: { "team": { "captain", "vice_captain", "starting", "substitutes", "total_cost", "bank", ... } }
```

### Example output (prompt snippet)

```
The fixtures this gameweek are:

GAMEWEEK 25 FIXTURES:
======================

Saturday 15th February 2025:
• Arsenal vs Sunderland
• Newcastle vs Brentford

FWD
 1. Erling Haaland (Man City, £14.5m)
[STATS] PPG: 8.5, Form: 8.5, Total Points: 180...
```

---

## 5. LLM Inference

**Purpose:** Sends the prompt to the model and returns structured JSON.

**Location:** `fpl_agent/strategies/openrouter_engine.py` (OpenRouter) and `llm_engine.py` (Gemini).

### Flow

1. `TeamBuildingStrategy.create_team()` or `update_team_weekly()` builds the prompt.
2. Response schema is chosen (`create_team_creation_schema()` or `create_weekly_update_schema()`).
3. `llm_engine.query(prompt, response_schema)` is called.
4. Engine POSTs to the provider API and extracts the text from the response.
5. Response is passed to the Validator for parsing.

### OpenRouter example

```python
payload = {
    "model": "openai/gpt-4.1:online",
    "input": prompt,
    "max_tokens": 100000,
    "temperature": 0.3,
}
response = requests.post("https://openrouter.ai/api/alpha/responses", json=payload)
text = extract_text_from_response(response.json())
```

### Response schema (team creation)

```python
{
  "type": "object",
  "properties": {
    "team": {
      "properties": {
        "captain": {"type": "string"},
        "vice_captain": {"type": "string"},
        "total_cost": {"type": "number"},
        "bank": {"type": "number"},
        "starting": [{"name", "position", "price", "team", "reason"}],
        "substitutes": [{"name", "position", "price", "team", "sub_order", "reason"}]
      }
    }
  }
}
```

### Example LLM output (parsed JSON)

```json
{
  "team": {
    "captain": "Bukayo Saka",
    "vice_captain": "Bruno Guimarães Rodriguez Moura",
    "chip": null,
    "transfers": [
      {
        "player_in": "Pascal Struijk",
        "player_in_price": 4.3,
        "player_out": "Lisandro Martínez",
        "player_out_price": 4.8,
        "reason": "Martínez has difficult fixture; Struijk offers better value..."
      }
    ],
    "total_cost": 97.6,
    "bank": 2.1,
    "starting": [...],
    "substitutes": [...]
  }
}
```

---

## 6. Validator

**Purpose:** Checks that the LLM output respects FPL rules before it is used.

**Location:** `fpl_agent/utils/validator.py` — `Validator` class.

### Validation steps

1. **Basic structure** — presence of `team`, `starting`, `substitutes`, `captain`, `vice_captain`, etc.
2. **Squad size** — exactly 15 players.
3. **Position limits** — 2 GK, 5 DEF, 5 MID, 3 FWD.
4. **Club limits** — max 3 players per team (`max_players_per_team` from config).
5. **Budget** — `total_cost ≤ budget`, `bank ≥ 0`.
6. **Formation** — starting 11 has 1 GK and allowed ranges for DEF/MID/FWD.
7. **Captain/vice-captain** — both present, different, and in the squad.
8. **Substitutes** — 4 subs, 1 GK, sub_order 1/2/3 for outfield players.

### Example validation errors

```
- Must have exactly 11 starting players, got 10
- Maximum 3 players allowed from Man City, got 4
- Total cost £101m exceeds budget of £100m
- Captain and vice-captain must be different players
```

### JSON parsing (`parse_llm_json_response`)

- Strips markdown code blocks (`` ```json ``).
- Extracts JSON between `{` and `}` if needed.
- Converts `Error:` strings into failures.
- Uses configurable `raise_on_error`.

---

## 7. State Update

**Purpose:** Applies the LLM’s team and transfers to the stored state (meta and team files).

**Location:** `fpl_agent/core/team_manager.py` — `TeamManager`.

### Pre-LLM (weekly updates): budget calculation

`calculate_team_budget(current_team, current_players)` computes available money using FPL sale rules:

```python
# FPL sale price formula (fpl_calculations.py)
def calculate_fpl_sale_price(current_price, purchase_price):
    if current_price > purchase_price:
        price_diff = current_price - purchase_price
        sale_price = purchase_price + (price_diff / 2)  # Half of profit
        sale_price = floor(sale_price * 10) / 10       # Round down to 0.1m
    else:
        sale_price = current_price  # Full loss
    return sale_price
```

Total budget = sum of sale prices + bank.

### Post-LLM: meta update

`update_meta_from_response(gameweek, team_data)` updates:

- **bank** — from LLM’s `team.bank`
- **free_transfers_carried_over**:
  - No transfers: carry over 1 (capped at 2)
  - With transfers: `available - transfers_made`
  - Wildcard/Free Hit: transfers unchanged
- **chips_used** — marks chip as used
- **current_gw**, **last_team_file**

### Persistence

| Action | Method | Files updated |
|--------|--------|---------------|
| New team | `save_new_team()` | `gw{N}.json`, `meta.json` |
| Weekly update | `save_weekly_update()` | `gw{N}.json`, `meta.json` |

### Example meta.json

```json
{
  "current_gw": 25,
  "last_team_file": "gw25.json",
  "bank": 2.1,
  "free_transfers_carried_over": 0,
  "chips_used": {
    "wildcard": false,
    "bench_boost": false,
    "free_hit": false,
    "triple_captain": false
  }
}
```

---

## 8. Output

**Purpose:** Stores the final team and shows it in the terminal.

**Location:** `fpl_agent/utils/display.py`; team files in `team_data/{team_name}/`.

### Storage format (gw25.json)

```json
{
  "gameweek": 25,
  "saved_at": "2025-02-13T14:30:00.000000",
  "team": {
    "captain": "Bukayo Saka",
    "vice_captain": "Bruno Guimarães Rodriguez Moura",
    "total_cost": 97.6,
    "bank": 2.1,
    "transfers": [...],
    "starting": [
      {"name": "Martin Dúbravka", "position": "GK", "price": 4.0, "team": "Burnley", "reason": "..."}
    ],
    "substitutes": [...]
  }
}
```

### Display (`display_comprehensive_team_result`)

- Captain, vice-captain, reasons
- Total cost, bank, expected points
- Chip used (if any)
- Transfers table: Player Out → Player In (prices)
- Starting 11 with (C) and (VC)
- Substitutes with sub order

### Example terminal output

```
✅ Team building complete!

================================================================================
FPL COMPREHENSIVE TEAM RESULT
================================================================================

Captain: Bukayo Saka
Captain Reason: Best fixture at home vs Sunderland...
Total Cost: £97.6m
Bank: £2.1m

================================================================================
TRANSFERS
================================================================================
Player Out                  Player In                   Out Price   In Price
--------------------------------------------------------------------------------
Lisandro Martínez           Pascal Struijk              £4.8        £4.3
  └─ Reason: Difficult fixture; Struijk offers better value...

================================================================================
STARTING 11
================================================================================
Martin Dúbravka (C)         Burnley      GK    £4.0
Bukayo Saka                 Arsenal      MID   £9.9
  └─ Captain choice; best fixture...
```

---

## Flow Check: Have We Missed Anything?

For the **core flow** (no enrichments/embeddings/news):

- **Data Fetcher** — yes
- **Processor** — yes
- **Data Store** — yes
- **Prompt Builder** — yes
- **LLM Inference** — yes
- **Validator** — yes
- **State Update** — yes
- **Output** — yes

The `DataService` orchestrates fetch → process → store. It also supports optional filtering of unavailable players (`chance_of_playing < 25%`) before data reaches the Prompt Builder, but that is a small filter rather than a separate pipeline stage.

**Orchestration:** `FPLAgent` in `main.py` wires these components together for `fetch_fpl_data()`, `build_team()`, and `gw_update()`.

---

## File Reference Summary

| Component | Primary file(s) |
|-----------|-----------------|
| Data Fetcher | `fpl_agent/data/fetch_fpl.py` |
| Processor | `fpl_agent/data/data_processor.py` |
| Data Store | `fpl_agent/data/data_store.py` |
| Data orchestration | `fpl_agent/data/data_service.py` |
| Prompt Builder | `fpl_agent/utils/prompt_formatter.py`, `strategies/team_building_strategy.py` |
| LLM Inference | `fpl_agent/strategies/openrouter_engine.py`, `llm_engine.py` |
| Validator | `fpl_agent/utils/validator.py` |
| Schemas | `fpl_agent/utils/schemas.py` |
| State Update | `fpl_agent/core/team_manager.py` |
| FPL calculations | `fpl_agent/utils/fpl_calculations.py` |
| Output/Display | `fpl_agent/utils/display.py` |
