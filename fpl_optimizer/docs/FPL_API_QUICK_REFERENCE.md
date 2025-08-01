# FPL API Quick Reference

## Base URL
```
https://fantasy.premierleague.com/api/
```

## Most Common Endpoints

| Endpoint | Description | Method |
|----------|-------------|--------|
| `bootstrap-static/` | All players, teams, gameweeks | GET |
| `fixtures/` | All fixtures | GET |
| `event/{gw}/live/` | Live gameweek data | GET |
| `entry/{team_id}/` | User team data | GET |

## Player Fields Quick Reference

### Essential Fields (Always Available)
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Player ID |
| `first_name` | string | First name |
| `second_name` | string | Last name |
| `element_type` | int | Position (1=GK, 2=DEF, 3=MID, 4=FWD) |
| `team` | int | Team ID |
| `now_cost` | int | Price (in tenths, 55 = £5.5m) |
| `total_points` | int | Season points |
| `form` | float | Form rating |
| `points_per_game` | float | PPG |
| `selected_by_percent` | float | Ownership % |

### Performance Stats
| Field | Type | Description |
|-------|------|-------------|
| `goals_scored` | int | Goals |
| `assists` | int | Assists |
| `clean_sheets` | int | Clean sheets |
| `saves` | int | Saves (GK) |
| `bonus` | int | Bonus points |
| `yellow_cards` | int | Yellow cards |
| `red_cards` | int | Red cards |

### Expected Stats (xG/xA)
| Field | Type | Description |
|-------|------|-------------|
| `expected_goals` | float | xG |
| `expected_assists` | float | xA |
| `expected_goal_involvements` | float | xGI |
| `ep_next` | float | Expected points next GW |
| `ep_this` | float | Expected points this GW |

### Advanced Metrics
| Field | Type | Description |
|-------|------|-------------|
| `ict_index` | float | ICT index |
| `influence` | float | Influence rating |
| `creativity` | float | Creativity rating |
| `threat` | float | Threat rating |
| `value_form` | float | Value for money (form) |
| `value_season` | float | Value for money (season) |

### Status & Availability
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | a=available, i=injured, n=not available |
| `news` | string | Injury/news |
| `chance_of_playing_next_round` | int | Chance % next GW |
| `chance_of_playing_this_round` | int | Chance % this GW |

### Transfer Data
| Field | Type | Description |
|-------|------|-------------|
| `transfers_in` | int | Transfers in this GW |
| `transfers_out` | int | Transfers out this GW |
| `transfers_in_event` | int | Transfers in this GW |
| `transfers_out_event` | int | Transfers out this GW |

## Position Types
- `1` - Goalkeeper (GK)
- `2` - Defender (DEF)  
- `3` - Midfielder (MID)
- `4` - Forward (FWD)

## Player Status
- `"a"` - Available
- `"i"` - Injured
- `"n"` - Not available
- `"s"` - Suspended
- `"u"` - Unavailable

## Common Queries

### Get All Players
```python
import requests
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
data = requests.get(url).json()
players = data['elements']
```

### Top Scorers
```python
top_scorers = sorted(players, key=lambda p: p['total_points'], reverse=True)[:10]
```

### Players by Position
```python
midfielders = [p for p in players if p['element_type'] == 3]
forwards = [p for p in players if p['element_type'] == 4]
```

### Players by Team
```python
arsenal_players = [p for p in players if p['team'] == 1]  # Arsenal team_id = 1
```

### Injured Players
```python
injured = [p for p in players if p['status'] == 'i']
```

### High Ownership Players
```python
high_ownership = [p for p in players if p['selected_by_percent'] > 20]
```

### Price Changes
```python
price_risers = [p for p in players if p['cost_change_event'] > 0]
price_fallers = [p for p in players if p['cost_change_event'] < 0]
```

### Best Value Players
```python
best_value = sorted(players, key=lambda p: p['value_season'], reverse=True)[:20]
```

### Expected Points Leaders
```python
ep_leaders = sorted(players, key=lambda p: p.get('ep_next', 0), reverse=True)[:20]
```

## Team Data
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Team ID |
| `name` | string | Team name |
| `short_name` | string | Short name (ARS, CHE, etc.) |
| `strength` | int | Team strength (1-5) |
| `form` | float | Team form |

## Fixture Data
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Fixture ID |
| `event` | int | Gameweek |
| `team_h` | int | Home team ID |
| `team_a` | int | Away team ID |
| `team_h_difficulty` | int | Home difficulty (1-5) |
| `team_a_difficulty` | int | Away difficulty (1-5) |
| `kickoff_time` | string | Kickoff time |
| `finished` | boolean | Is finished |

## Difficulty Ratings
- `1` - Very Easy
- `2` - Easy  
- `3` - Medium
- `4` - Hard
- `5` - Very Hard

## Notes
- Prices in tenths (55 = £5.5m)
- Timestamps in ISO format (UTC)
- Some fields may be `null`
- Data updates regularly during season 