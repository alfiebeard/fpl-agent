# FPL Optimizer - Dual Approach Team Creator

A comprehensive Fantasy Premier League (FPL) optimizer featuring two distinct team creation methodologies:

1. **API-Based Statistical Analysis** - Data-driven approach using xPts calculations and mathematical optimization
2. **LLM-Based Expert Insights** - AI-powered approach using web-scraped expert opinions and large language model analysis

## 🚀 Features

### API-Based Approach
- Real-time FPL API data integration
- Expected points (xPts) calculations using form, xG/xA, and fixture analysis
- Integer Linear Programming (ILP) optimization
- Statistical player performance analysis
- Fixture difficulty assessment
- Mathematical captain and transfer selection

### LLM-Based Approach
- Web scraping of expert FPL insights from trusted sources
- Large Language Model analysis of expert opinions
- Human-like decision making based on community wisdom
- Contextual understanding of FPL meta and trends
- Expert-driven captain and transfer selections
- Wildcard timing based on expert consensus

### Core Capabilities
- **Team Creation**: Build optimal teams from scratch (start of season or wildcard)
- **Weekly Transfers**: Get transfer recommendations based on current form and fixtures
- **Captain Selection**: Choose optimal captain and vice-captain for each gameweek
- **Wildcard Analysis**: Determine optimal timing for wildcard usage
- **Approach Comparison**: Side-by-side analysis of both methodologies

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd fpl-optimizer
```

2. **Install dependencies**
```bash
pip install -r fpl_optimizer/requirements.txt
```

3. **Environment Configuration**
Create a `.env` file in the project root:
```env
# LLM API Keys (choose one)
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional FPL API credentials
FPL_TEAM_ID=your_team_id
```

4. **Configuration**
Edit `fpl_optimizer/config.yaml` to customize:
- LLM provider and model settings
- Web search parameters
- Optimization constraints
- Expert source preferences

## 🎯 Usage

### Command Line Interface

#### Team Creation

**Create team using API-based statistical approach:**
```bash
python -m fpl_optimizer create-api --budget 100.0 --sample-size 500
```

**Create team using LLM-based expert insights:**
```bash
python -m fpl_optimizer create-llm --budget 100.0 --gameweek 15
```

#### Weekly Recommendations

**Get weekly recommendations using statistical analysis:**
```bash
python -m fpl_optimizer weekly-api --free-transfers 1 --team-file my_team.json
```

**Get weekly recommendations using expert insights:**
```bash
python -m fpl_optimizer weekly-llm --free-transfers 1 --gameweek 15
```

#### Compare Approaches

**Compare team creation methods:**
```bash
python -m fpl_optimizer compare --budget 100.0 --gameweek 15
```

**Compare weekly recommendation methods:**
```bash
python -m fpl_optimizer compare --team-file my_team.json --gameweek 15
```

#### Other Commands

**Fetch and display player data:**
```bash
python -m fpl_optimizer fetch --sample-size 100
```

**Legacy optimization (uses API approach):**
```bash
python -m fpl_optimizer optimize --sample-size 50
```

### Python API

```python
from fpl_optimizer import FPLOptimizer
from fpl_optimizer.models import FPLTeam

# Initialize optimizer
optimizer = FPLOptimizer()

# Create team using API approach
api_result = optimizer.create_team_api(budget=100.0)

# Create team using LLM approach  
llm_result = optimizer.create_team_llm(budget=100.0, gameweek=15)

# Get weekly recommendations
current_team = load_your_team()  # Your implementation
api_weekly = optimizer.get_weekly_recommendations_api(current_team, free_transfers=1)
llm_weekly = optimizer.get_weekly_recommendations_llm(current_team, free_transfers=1, gameweek=15)

# Compare approaches
comparison = optimizer.compare_approaches(current_team, gameweek=15)
```

## 🔧 Configuration

### LLM Settings (`config.yaml`)

```yaml
llm:
  provider: "openai"  # or "anthropic"
  model: "gpt-4"
  max_tokens: 4000
  temperature: 0.7
  
  web_search:
    enabled: true
    max_results: 20
    search_terms:
      - "fantasy premier league tips"
      - "FPL expert picks"
      - "fantasy football captain picks"
    expert_sources:
      - "fantasyfootballscout.co.uk"
      - "fantasyfootballpundit.com"
      - "planetfpl.com"
      - "fplanalytics.com"
      - "reddit.com/r/FantasyPL"
```

### Statistical Analysis Settings

```yaml
xpts:
  weights:
    form: 0.3
    xg_xa: 0.4
    fixtures: 0.2
    minutes: 0.1
  fixture_difficulty_adjustment: true
  injury_adjustment: true

optimization:
  solver: "PULP_CBC_CMD"
  time_limit: 300
  gap_tolerance: 0.01
```

## 📊 Output Examples

### Team Creation Output
```
FPL TEAM CREATION COMPLETE - LLM-based Expert Insights
================================================================================

SELECTED TEAM
====================================================================================================
Name                     Team           Pos  Price  Form   Total Pts  Captain 
----------------------------------------------------------------------------------------------------
Haaland                  Man City       FWD  £12.1  8.2    156        C       
Salah                    Liverpool      MID  £13.2  7.8    142        VC      
...

Team Cost: £99.8m
Expected Points: 67.3
Confidence: 0.82

REASONING
================================================================================
LLM Analysis: Team selection based on expert consensus from Fantasy Football Scout,
Reddit r/FantasyPL, and FPL Analytics. Key factors: Haaland's home fixtures,
Salah's penalty duties, and defensive coverage from Liverpool assets...

EXPERT INSIGHTS USED
================================================================================
Expert insights from 15 sources:
Fantasy Football Scout (4 insights):
  - Haaland essential for upcoming fixtures
  - Liverpool defense offers great value
...
```

### Weekly Recommendations Output
```
WEEKLY FPL RECOMMENDATIONS - LLM-based Expert Insights
================================================================================

RECOMMENDED TRANSFERS
================================================================================
1. Sterling → Foden
   Reason: Expert consensus on Foden's superior form and fixture advantage

Transfer Confidence: 0.76

CAPTAINCY RECOMMENDATIONS
================================================================================
Captain: Haaland
Vice Captain: Salah

WILDCARD ANALYSIS
================================================================================
Use Wildcard: NO
Confidence: 0.68
Reasoning: Experts suggest waiting for GW18 fixture swing...

EXPERT INSIGHTS SUMMARY
================================================================================
Total Insights: 23
Sources: Fantasy Football Scout, Reddit r/FantasyPL, FPL Analytics
Key Topics: Transfer, Captain, Form, Fixtures

Overall Confidence: 0.74
```

## 🏗️ Architecture

### Project Structure
```
fpl_optimizer/
├── team_creators/
│   ├── api_team_creator.py      # Statistical approach
│   ├── llm_team_creator.py      # LLM-based approach
│   ├── web_search.py            # Expert insights scraping
│   └── llm_analyzer.py          # LLM analysis engine
├── models.py                    # Data models
├── config.py                    # Configuration management
├── optimizer/                   # Mathematical optimization
├── ingestion/                   # Data ingestion
└── main.py                      # CLI interface
```

### Data Flow

#### API-Based Approach
```
FPL API → Player Data → xPts Calculation → ILP Optimization → Team Selection
```

#### LLM-Based Approach
```
Web Search → Expert Insights → LLM Analysis → Team Recommendations
```

## 🤝 Expert Sources

The LLM approach gathers insights from trusted FPL sources:

- **Fantasy Football Scout** - Premium FPL analysis and tips
- **FPL Analytics** - Data-driven insights and projections  
- **Planet FPL** - Community-driven analysis
- **Reddit r/FantasyPL** - Community discussions and tips
- **Twitter/X FPL Community** - Real-time expert opinions

## 🔍 Comparison Analysis

The system can compare both approaches across multiple dimensions:

- **Team Selection Overlap** - How many players both methods select
- **Captain Agreement** - Whether both approaches choose the same captain
- **Transfer Recommendations** - Comparison of suggested moves
- **Confidence Levels** - Relative certainty of each approach
- **Expected Points** - Projected performance differences

## 🚨 Limitations & Considerations

### API-Based Approach
- Relies on historical data and statistical patterns
- May miss contextual factors (injuries, rotation, etc.)
- Limited by available data quality
- Mathematical optimization may not account for human factors

### LLM-Based Approach
- Dependent on quality and recency of expert insights
- Requires LLM API access (costs involved)
- Web scraping may be affected by site changes
- Subject to expert opinion biases and groupthink

### General
- Both approaches are tools to aid decision-making, not guarantees
- FPL involves inherent unpredictability
- Always consider your own analysis and gut feelings
- Past performance doesn't guarantee future results

## 📈 Performance Tips

1. **Combine Both Approaches**: Use comparison mode to get best of both worlds
2. **Regular Updates**: Run weekly recommendations before each deadline
3. **Context Matters**: Consider gameweek context (doubles, blanks, etc.)
4. **Monitor Confidence**: Higher confidence scores generally indicate better decisions
5. **Expert Source Quality**: Ensure web search captures high-quality sources

## 🛠️ Development

### Adding New Expert Sources
1. Update `expert_sources` in `config.yaml`
2. Modify `_is_trusted_source()` in `web_search.py`
3. Add source mapping in `_extract_source_name()`

### Customizing LLM Prompts
Edit prompt templates in `llm_analyzer.py`:
- `_create_team_creation_prompt()`
- `_create_transfer_prompt()`
- `_create_captaincy_prompt()`

### Extending Statistical Analysis
Modify calculation methods in `api_team_creator.py`:
- `_calculate_comprehensive_xpts()`
- `_calculate_fixture_difficulty_xpts()`

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤖 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review configuration options in `config.yaml`

---

**Disclaimer**: This tool is for educational and research purposes. Fantasy Premier League involves financial risk, and past performance doesn't guarantee future results. Always gamble responsibly. 