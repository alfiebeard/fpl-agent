# 🧐 FPL Optimizer — Fully Automated Fantasy Premier League Manager

This project is a fully automated, AI-assisted Fantasy Premier League (FPL) team manager. It uses expected points models, fixture forecasting, optimization, and natural language analysis to build and maintain the optimal team across the season. The goal is to remove human bias from weekly decisions and use real-time data and predictive models to maintain the best-performing team across all 38 gameweeks.

## 🌟 Goals

- Select optimal 15-man squad based on expected points (`xPts`) across future gameweeks
- Automate weekly decisions: transfers, captain, chip use, bench order
- Integrate human insights from tips, forums, and news via LLM for qualitative signals
- Optimize over a rolling N-week window using hard constraints (budget, formations)
- Create a fully autonomous loop that ingests data, runs optimization, and produces actionable output
- Handle unexpected scenarios like injuries, blanks, doubles, price changes
- Learn from prior decisions by tracking xPts vs actual results for ongoing refinement

## 📇 Architecture Overview

```
+--------------------+      +------------------+
|  Data Ingestion    | <--> |   Data Pipeline  |
+--------------------+      +------------------+
         ↓                         ↓
+--------------------+      +----------------------+
|  xPts Projection   | ---> | Optimization Engine |
+--------------------+      +----------------------+
                                     ↓
                            +------------------+
                            |  Decision Logic  |
                            +------------------+
                                     ↓
                            +------------------+
                            | LLM Integration  |
                            +------------------+
                                     ↓
                            +------------------+
                            | Weekly Output/API |
                            +------------------+
```

## 📁 Project Structure

```
fpl_optimizer/
├── data/
│   ├── raw/
│   └── processed/
├── ingestion/
│   ├── fetch_fpl.py
│   ├── fetch_understat.py
│   ├── fetch_odds.py
│   └── fetch_fbref.py
├── processing/
│   ├── normalize.py
│   ├── join_data.py
│   └── compute_form.py
├── projection/
│   ├── xpts.py
│   ├── predict_minutes.py
│   └── fixture_difficulty.py
├── optimizer/
│   ├── ilp_solver.py
│   ├── transfer_optimizer.py
│   └── chip_strategy.py
├── llm_layer/
│   ├── summarize_tips.py
│   └── extract_insights.py
├── output/
│   ├── generate_report.py
│   └── visualize.py
├── main.py
├── config.yaml
├── requirements.txt
└── README.md
```

## ⚖️ Technologies

- Python (3.10+)
- `requests`, `pandas`, `numpy`, `scikit-learn` — data handling + modeling
- `PuLP` or `Google OR-Tools` — integer linear programming for selection/transfer
- `bs4`, `selenium`, `playwright` — scraping for odds and tips
- `LangChain`, `transformers`, or OpenAI API — for summarization and reasoning
- `matplotlib`, `plotly`, `streamlit` — visual insights and optional dashboard
- `schedule`, `APScheduler` — weekly automation & cron scheduling
- `sqlite` or `DuckDB` — local cache for quick data retrieval

## 📅 Data Sources

| Type           | Source                                                                                             | Notes                                                                                                              |                        |
| -------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| FPL Data       |                                                                                                    | [https://fantasy.premierleague.com/api/bootstrap-static/](https://fantasy.premierleague.com/api/bootstrap-static/) | Players, teams, events |
| Fixtures & FDR | [https://fantasy.premierleague.com/api/fixtures/](https://fantasy.premierleague.com/api/fixtures/) | Fixture difficulty and rotation                                                                                    |                        |
| xG/xA          | [https://understat.com](https://understat.com)                                                     | Historical, player-level                                                                                           |                        |
| Team Stats     | [https://fbref.com/en/](https://fbref.com/en/)                                                     | Supplementary, more granular                                                                                       |                        |
| Odds           | OddsAPI, Betfair, etc.                                                                             | CS, goalscorer, anytime scorer                                                                                     |                        |
| Tips/Insight   | Reddit, FFS, Twitter, Scout                                                                        | Used via LLM for adjustment                                                                                        |                        |

## 📊 xPts Formula (Expected Points)

Calculated per fixture, adjusted by opponent, team, and recent form. Now enhanced with positional weightings and contextual factors:

```
xPts = (
    (xG_pred * GoalPts[player_position]) +
    (xA_pred * AssistPts[player_position]) +
    (xCS_prob * CS_pts[player_position]) +
    (Bonus_prob * 1.5) -
    (YC_prob * 1) -
    (RC_prob * 3)
) * xMins_pct
```

### 🧮 Positional Points Weights

| Position | GoalPts | AssistPts | CS\_pts |
| -------- | ------- | --------- | ------- |
| GK       | 6       | 3         | 4       |
| DEF      | 6       | 3         | 4       |
| MID      | 5       | 3         | 1       |
| FWD      | 4       | 3         | 0       |

- `xG_pred`, `xA_pred`: based on team and player attacking strength vs opponent defensive weakness
- `xCS_prob`: estimated from xGA differential and bookmaker clean sheet odds
- `xMins_pct`: probability of playing 60+ mins, based on recent rotation/form/injury news
- `Bonus_prob`: derived from attacking contribution, passing metrics, and recent bonus trends
- Run this over a rolling window of N future fixtures (default = 5 weeks)
- Factor in team assist potential, e.g. high xA team vs low xGC defense → higher xG\_pred

## 🤓 Optimization Logic

- Solver: `PuLP` or `OR-Tools`
- Objective: maximize cumulative `xPts` over N gameweeks
- Constraints:
  - Budget ≤ 100M
  - Valid formation (e.g., 3-4-3)
  - Max 3 players per club
  - Chip logic, captaincy rules, and transfer hit limits
- Bonus scoring for high-confidence LLM picks or injury alerts
- Transfer cost logic: execute only if marginal xPts gain > point cost

## ♻️ Weekly Loop

1. Ingest fresh player/team stats, odds, xG/xA from APIs
2. Recalculate per-fixture and aggregated xPts for all players
3. Rank players by xPts per £ and per position
4. Optimize selection or transfer plan for that week
5. Compare against LLM tip layer (Reddit, Scout, X/Twitter)
6. Make smart changes or hold chips depending on projected gains
7. Output reports or push changes via browser automation (if enabled)

## 🧠 Chip Strategy Logic

| Chip           | Strategy Example                                         |
| -------------- | -------------------------------------------------------- |
| Triple Captain | xPts\_captain > 10, confirmed starter, low YC/RC risk    |
| Bench Boost    | Bench total xPts ≥ 20 or all starters in strong fixtures |
| Free Hit       | Use in blank/double weeks or injury-heavy situations     |
| Wildcard       | If ≥ 4 optimal players not in team, or fixture swing     |

Simulated runs evaluate impact of chip now vs later.

## 🤖 LLM Assistance

- Crawl expert insights and trends using natural language processing
- Summarize human picks, injury rumors, hidden form insights
- Tag and score players using confidence signals from tips
- Boost or penalize xPts based on non-numeric insight
- LLM-suggested overrides can trigger minor rebalancing in optimizer

```python
if llm_player_recommendation not in top_11 and confidence > 0.85:
    xPts[player] += 0.5  # Adjust marginally for team inclusion test
```

## ✅ Setup

```bash
pip install -r requirements.txt
python main.py
```

## 🚀 Philosophy

This optimizer merges predictive analytics with logical structure and expert insight. It applies quantitative reasoning, cross-referenced by qualitative intelligence (via LLMs), to ensure your team is always in top shape — while requiring no manual input. Built for those who want to win FPL using science, not gut feel.

