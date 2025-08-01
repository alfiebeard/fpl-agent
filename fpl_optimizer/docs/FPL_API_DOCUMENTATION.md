# FPL API Documentation

## Overview

The Fantasy Premier League (FPL) API provides access to real-time data about players, teams, fixtures, and gameweeks. This documentation covers all available endpoints, data structures, and field descriptions.

## Base URL

```
https://fantasy.premierleague.com/api/
```

## Authentication

The FPL API is **public** and does not require authentication for most endpoints. However, some endpoints require a valid FPL team ID for user-specific data.

## API Endpoints

### 1. Bootstrap Static Data

**Endpoint:** `bootstrap-static/`

**Description:** Returns comprehensive static data including all players, teams, events, and game settings.

**Method:** GET

**Response:** JSON object containing:
- `elements` - Array of all players
- `teams` - Array of all teams
- `events` - Array of all gameweeks
- `element_types` - Position definitions
- `game_settings` - Game configuration

**Example Response Structure:**
```json
{
  "elements": [...],      // Player data (see Player Fields below)
  "teams": [...],         // Team data (see Team Fields below)
  "events": [...],        // Gameweek data (see Gameweek Fields below)
  "element_types": [...], // Position types
  "game_settings": {...}  // Game configuration
}
```

### 2. Fixtures

**Endpoint:** `fixtures/`

**Description:** Returns all fixtures for the current season.

**Method:** GET

**Response:** Array of fixture objects (see Fixture Fields below)

### 3. Live Gameweek Data

**Endpoint:** `event/{gameweek}/live/`

**Description:** Returns live data for a specific gameweek.

**Method:** GET

**Parameters:**
- `gameweek` (int) - The gameweek number

**Response:** JSON object with live gameweek statistics

### 4. Team Data

**Endpoint:** `entry/{team_id}/`

**Description:** Returns data for a specific FPL team.

**Method:** GET

**Parameters:**
- `team_id` (int) - The FPL team ID

**Response:** JSON object with team information

### 5. Team History

**Endpoint:** `entry/{team_id}/history/`

**Description:** Returns historical data for a specific FPL team.

**Method:** GET

**Parameters:**
- `team_id` (int) - The FPL team ID

**Response:** JSON object with team history and chips usage

### 6. Team Transfers

**Endpoint:** `entry/{team_id}/transfers/`

**Description:** Returns transfer history for a specific FPL team.

**Method:** GET

**Parameters:**
- `team_id` (int) - The FPL team ID

**Response:** Array of transfer objects

### 7. User Team (Current Gameweek)

**Endpoint:** `entry/{team_id}/event/`

**Description:** Returns current team data for the latest gameweek.

**Method:** GET

**Parameters:**
- `team_id` (int) - The FPL team ID

**Response:** JSON object with current team picks and captain/vice-captain

### 8. User Team Picks (Specific Gameweek)

**Endpoint:** `entry/{team_id}/event/{gameweek}/picks/`

**Description:** Returns team picks for a specific gameweek.

**Method:** GET

**Parameters:**
- `team_id` (int) - The FPL team ID
- `gameweek` (int) - The gameweek number

**Response:** JSON object with team picks for that gameweek

## Data Structures

### Player Fields (`elements` array)

Each player object contains the following fields:

#### Basic Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | int | Unique player ID | `1` |
| `first_name` | string | Player first name | `"David"` |
| `second_name` | string | Player last name | `"Raya Martín"` |
| `web_name` | string | Web display name | `"Raya"` |
| `element_type` | int | Position type (1=GK, 2=DEF, 3=MID, 4=FWD) | `1` |
| `team` | int | Team ID | `1` |
| `code` | int | Player code | `154561` |
| `opta_code` | string | Opta player code | `"p154561"` |

#### Pricing Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `now_cost` | int | Current price (in tenths, e.g., 55 = £5.5m) | `55` |
| `cost_change_start` | int | Price change since start of season (in tenths) | `0` |
| `cost_change_event` | int | Price change this gameweek (in tenths) | `0` |
| `cost_change_event_fall` | int | Price fall this gameweek (in tenths) | `0` |
| `cost_change_start_fall` | int | Price fall since start of season (in tenths) | `0` |

#### Performance Statistics
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `total_points` | int | Total FPL points this season | `142` |
| `event_points` | int | Points in current gameweek | `0` |
| `points_per_game` | float | Average points per game | `3.7` |
| `form` | float | Form rating (last 30 days) | `0.0` |
| `minutes` | int | Total minutes played | `3420` |
| `starts` | int | Number of starts | `38` |
| `starts_per_90` | float | Starts per 90 minutes | `1.0` |

#### Goals and Assists
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `goals_scored` | int | Goals scored | `0` |
| `assists` | int | Assists | `0` |
| `clean_sheets` | int | Clean sheets | `13` |
| `goals_conceded` | int | Goals conceded | `34` |
| `own_goals` | int | Own goals | `0` |
| `penalties_saved` | int | Penalties saved | `0` |
| `penalties_missed` | int | Penalties missed | `0` |
| `saves` | int | Saves (for goalkeepers) | `86` |

#### Expected Statistics (xG/xA)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `expected_goals` | float | Expected goals (xG) | `0.00` |
| `expected_goals_per_90` | float | Expected goals per 90 minutes | `0.0` |
| `expected_assists` | float | Expected assists (xA) | `0.03` |
| `expected_assists_per_90` | float | Expected assists per 90 minutes | `0.0` |
| `expected_goal_involvements` | float | Expected goal involvements | `0.03` |
| `expected_goal_involvements_per_90` | float | Expected goal involvements per 90 minutes | `0.0` |
| `expected_goals_conceded` | float | Expected goals conceded | `35.03` |
| `expected_goals_conceded_per_90` | float | Expected goals conceded per 90 minutes | `0.92` |

#### Expected Points
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ep_next` | float | Expected points next gameweek | `4.5` |
| `ep_this` | float | Expected points this gameweek | `null` |

#### Advanced Metrics (ICT Index)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ict_index` | float | ICT (Influence, Creativity, Threat) index | `76.7` |
| `influence` | float | Influence rating | `755.4` |
| `creativity` | float | Creativity rating | `10.7` |
| `threat` | float | Threat rating | `0.0` |

#### Bonus Points System (BPS)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `bonus` | int | Bonus points | `10` |
| `bps` | int | BPS (Bonus Points System) | `555` |
| `bonus_per_90` | float | Bonus points per 90 minutes | `0.26` |
| `bps_per_90` | float | BPS per 90 minutes | `14.6` |

#### Per-90 Statistics
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `clean_sheets_per_90` | float | Clean sheets per 90 minutes | `0.34` |
| `saves_per_90` | float | Saves per 90 minutes | `2.26` |
| `goals_conceded_per_90` | float | Goals conceded per 90 minutes | `0.89` |

#### Disciplinary
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `yellow_cards` | int | Yellow cards | `3` |
| `red_cards` | int | Red cards | `0` |

#### Ownership and Transfers
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `selected_by_percent` | float | Percentage of teams that own this player | `18.4` |
| `transfers_in` | int | Transfers in this gameweek | `0` |
| `transfers_out` | int | Transfers out this gameweek | `0` |
| `transfers_in_event` | int | Transfers in this gameweek | `0` |
| `transfers_out_event` | int | Transfers out this gameweek | `0` |

#### Value Metrics
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `value_form` | float | Value for money based on form | `0.0` |
| `value_season` | float | Value for money based on season total | `25.8` |

#### Status and Availability
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `status` | string | Player status (a=available, i=injured, n=not available) | `"a"` |
| `news` | string | Injury/news information | `""` |
| `news_added` | string | When news was last updated | `null` |
| `chance_of_playing_next_round` | int | Chance of playing next gameweek (%) | `null` |
| `chance_of_playing_this_round` | int | Chance of playing this gameweek (%) | `null` |

#### Set Pieces
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `corners_and_indirect_freekicks_order` | int | Set piece order for corners/indirect free kicks | `null` |
| `corners_and_indirect_freekicks_text` | string | Set piece text for corners/indirect free kicks | `""` |
| `direct_freekicks_order` | int | Set piece order for direct free kicks | `null` |
| `direct_freekicks_text` | string | Set piece text for direct free kicks | `""` |
| `penalties_order` | int | Penalty taker order | `null` |
| `penalties_text` | string | Penalty taker text | `""` |

#### Dream Team
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `dreamteam_count` | int | Times in dream team | `0` |
| `in_dreamteam` | boolean | Currently in dream team | `false` |

#### Ranks
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `now_cost_rank` | int | Price rank | `126` |
| `now_cost_rank_type` | int | Price rank type | `4` |
| `form_rank` | int | Form rank | `476` |
| `form_rank_type` | int | Form rank type | `77` |
| `points_per_game_rank` | int | Points per game rank | `68` |
| `points_per_game_rank_type` | int | Points per game rank type | `11` |
| `selected_rank` | int | Selection percentage rank | `20` |
| `selected_rank_type` | int | Selection percentage rank type | `2` |
| `ict_index_rank` | int | ICT index rank | `178` |
| `ict_index_rank_type` | int | ICT index rank type | `8` |
| `influence_rank` | int | Influence rank | `37` |
| `influence_rank_type` | int | Influence rank type | `8` |
| `creativity_rank` | int | Creativity rank | `342` |
| `creativity_rank_type` | int | Creativity rank type | `11` |
| `threat_rank` | int | Threat rank | `635` |
| `threat_rank_type` | int | Threat rank type | `77` |

#### Additional Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `birth_date` | string | Player birth date | `"1995-09-15"` |
| `photo` | string | Player photo URL | `"154561.jpg"` |
| `photo_id` | int | Player photo ID | `154561` |
| `squad_number` | int | Squad number | `null` |
| `special` | boolean | Special status (e.g., loan player) | `false` |
| `region` | int | Region code | `200` |
| `team_code` | int | Team code | `3` |
| `team_join_date` | string | Date joined team | `"2024-07-04"` |
| `can_select` | boolean | Can be selected | `true` |
| `can_transact` | boolean | Can be transferred | `true` |
| `has_temporary_code` | boolean | Has temporary code | `false` |
| `removed` | boolean | Removed from game | `false` |
| `defensive_contribution` | int | Defensive contribution | `0` |

### Team Fields (`teams` array)

Each team object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | int | Team ID | `1` |
| `name` | string | Team name | `"Arsenal"` |
| `short_name` | string | Short team name | `"ARS"` |
| `strength` | int | Team strength rating | `4` |
| `form` | float | Team form rating | `3.5` |

### Fixture Fields

Each fixture object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | int | Fixture ID | `1` |
| `event` | int | Gameweek number | `1` |
| `team_h` | int | Home team ID | `1` |
| `team_a` | int | Away team ID | `2` |
| `team_h_difficulty` | int | Home team difficulty (1-5) | `3` |
| `team_a_difficulty` | int | Away team difficulty (1-5) | `3` |
| `difficulty` | int | Overall difficulty | `3` |
| `kickoff_time` | string | Kickoff time (ISO format) | `"2024-08-16T19:30:00Z"` |
| `finished` | boolean | Whether fixture is finished | `false` |
| `team_h_score` | int | Home team score | `null` |
| `team_a_score` | int | Away team score | `null` |

### Gameweek Fields (`events` array)

Each gameweek object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | int | Gameweek ID | `1` |
| `name` | string | Gameweek name | `"Gameweek 1"` |
| `deadline_time` | string | Deadline time (ISO format) | `"2024-08-16T11:00:00Z"` |
| `average_entry_score` | int | Average entry score | `45` |
| `finished` | boolean | Whether gameweek is finished | `false` |
| `data_checked` | boolean | Whether data is checked | `false` |
| `highest_scoring_entry` | int | Highest scoring entry | `123456` |
| `is_previous` | boolean | Whether this is previous gameweek | `false` |
| `is_current` | boolean | Whether this is current gameweek | `true` |
| `is_next` | boolean | Whether this is next gameweek | `false` |

## Data Types

### Position Types (`element_type`)
- `1` - Goalkeeper (GK)
- `2` - Defender (DEF)
- `3` - Midfielder (MID)
- `4` - Forward (FWD)

### Player Status (`status`)
- `"a"` - Available
- `"i"` - Injured
- `"n"` - Not available
- `"s"` - Suspended
- `"u"` - Unavailable

### Difficulty Ratings
- `1` - Very Easy
- `2` - Easy
- `3` - Medium
- `4` - Hard
- `5` - Very Hard

## Rate Limiting

The FPL API has rate limiting in place. It's recommended to:
- Cache data when possible
- Avoid making excessive requests
- Use the bootstrap-static endpoint for bulk data

## Error Handling

Common HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `429` - Rate limit exceeded
- `500` - Server error

## Example Usage

### Fetching All Players
```python
import requests

url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()

players = data['elements']
teams = data['teams']

print(f"Total players: {len(players)}")
print(f"Total teams: {len(teams)}")
```

### Finding Top Scorers
```python
# Sort players by total points
top_scorers = sorted(players, key=lambda p: p['total_points'], reverse=True)[:10]

for player in top_scorers:
    print(f"{player['first_name']} {player['second_name']}: {player['total_points']} points")
```

### Finding Players by Position
```python
# Get all midfielders
midfielders = [p for p in players if p['element_type'] == 3]

# Get all forwards
forwards = [p for p in players if p['element_type'] == 4]
```

## Notes

1. **Price Format**: All prices are stored in tenths (e.g., 55 = £5.5m)
2. **Timestamps**: All timestamps are in ISO format with UTC timezone
3. **Null Values**: Some fields may be `null` if data is not available
4. **Season Data**: The API provides current season data only
5. **Updates**: Data is updated regularly throughout the season

## Related Documentation

- [FPL Official Website](https://fantasy.premierleague.com/)
- [FPL Statistics](https://www.fplstatistics.co.uk/)
- [FPL Scout](https://www.fantasyfootballscout.co.uk/) 