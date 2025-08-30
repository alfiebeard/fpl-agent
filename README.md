# FPL Agent - AI-Powered Fantasy Premier League Manager

A sophisticated Fantasy Premier League (FPL) team management system that uses Large Language Models (LLMs) to provide intelligent team building, weekly updates, and strategic recommendations.

## 🎯 What This Project Does

FPL Agent is an AI-powered assistant that helps you manage your Fantasy Premier League team throughout the season. It combines real-time FPL data with LLM analysis to provide:

- **Intelligent Team Building**: Create optimal teams from scratch using AI analysis
- **Weekly Updates**: Get transfer recommendations, captain choices, and chip usage advice
- **Expert Insights**: Leverage AI to analyze player form, injuries, and fixture difficulty
- **Multi-Team Management**: Manage multiple FPL teams simultaneously
- **Data Enrichment**: Enhance player data with expert insights and injury news

## 🚀 Key Features

### Core Functionality
- **Team Creation**: Build new teams with AI-powered player selection
- **Weekly Updates**: Get comprehensive gameweek recommendations
- **Chip Management**: Intelligent wildcard, free hit, and other chip usage
- **Multi-Team Support**: Manage multiple teams with different strategies
- **Data Caching**: Smart caching to minimize API calls and costs

### AI-Powered Analysis
- **LLM Integration**: Uses Google's Gemini models for intelligent decision making
- **Expert Insights**: AI-generated analysis of player form and potential
- **Injury Monitoring**: Real-time injury status and availability tracking
- **Embedding Filtering**: Advanced player filtering using semantic similarity
- **RAG (Retrieval-Augmented Generation)**: Combines data retrieval with AI analysis

### Data Management
- **Real-time FPL API**: Live data from the official FPL API
- **Smart Caching**: Efficient data storage and retrieval
- **Player Enrichment**: Enhanced player data with expert insights
- **Fixture Analysis**: Comprehensive fixture difficulty assessment

## 📦 Installation

### Prerequisites
- Python 3.11+
- pip package manager

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd fpl-agent
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
Create a `.env` file in the project root:
```env
# Google AI API Key (required for LLM functionality)
GOOGLE_API_KEY=your_google_api_key_here
```

**Note**: The Google API key is required for LLM functionality.

5. **Configuration**
Edit `fpl_agent/config.yaml` to customize:
- LLM model settings
- Team composition rules
- Embedding configuration
- Display preferences

## 🎮 Usage

### Command Line Interface

The FPL Agent provides a comprehensive CLI with the following main commands:

#### Data Management
```bash
# Fetch fresh FPL data
fpl-agent fetch

# Fetch with enrichments (expert insights + injury news)
fpl-agent fetch --use-enrichments

# Use cached data only
fpl-agent fetch --cached-only

# Enrich existing data with AI insights
fpl-agent enrich

# Show data status
fpl-agent show-data

# Show available players breakdown
fpl-agent show-players
```

#### Team Management
```bash
# Create a new team
fpl-agent build-team --team "My Team" --budget 100.0

# Create team with specific gameweek
fpl-agent build-team --team "My Team" --budget 100.0 --gameweek 15

# Create team using different RAG modes
fpl-agent build-team --team "My Team" --rag-mode none  # No LLM player enrichments
fpl-agent build-team --team "My Team" --rag-mode enrichments  # Basic LLM player enrichments
fpl-agent build-team --team "My Team" --rag-mode ranked_enrichments  # Full LLM player enrichments

# Save team to file
fpl-agent build-team --team "My Team" --save-team
```

#### Weekly Updates
```bash
# Get weekly recommendations for a team
fpl-agent gw-update --team "My Team"

# Update for specific gameweek
fpl-agent gw-update --team "My Team" --gameweek 15

# Update using cached data only
fpl-agent gw-update --team "My Team" --cached-only

# Save weekly update
fpl-agent gw-update --team "My Team" --save-team
```

#### Multi-Team Operations
```bash
# List all teams
fpl-agent list-teams

# Show specific team
fpl-agent show-team --team "My Team"

# Show all teams
fpl-agent show-team --all-teams

# Delete a team
fpl-agent delete-team --team "My Team"

# Run operations on all teams
fpl-agent build-team --all-teams --budget 100.0
fpl-agent gw-update --all-teams
```

#### Debug and Development
```bash
# Show debug information
fpl-agent fetch --debug

# Show verbose logging
fpl-agent fetch --verbose

# Show LLM prompts (for debugging)
fpl-agent build-team --team "My Team" --show-prompt
fpl-agent gw-update --team "My Team" --show-prompt
```

### Python API

```python
from fpl_agent import FPLAgent

# Initialize agent
agent = FPLAgent()

# Fetch FPL data
data = agent.fetch_fpl_data(use_cached=False, use_enrichments=True)

# Enrich player data with AI insights
agent.enrich(data, gameweek=15)

# Build a new team
agent.build_team(
    team_name="My Team",
    budget=100.0,
    gameweek=15,
    rag_mode="ranked_enrichments",
    save_team=True
)

# Get weekly update
agent.gw_update(
    team_name="My Team",
    gameweek=15,
    rag_mode="ranked_enrichments",
    save_team=True
)

# Show data status
agent.show_data()

# Show team information
agent.show_team("My Team")
```

## 🔧 Configuration

### LLM Settings (`config.yaml`)

```yaml
llm:
  main:
    model: "gemini-2.5-pro"  # Primary model for complex tasks
    max_output_tokens: 65536
    temperature: 0.3
    max_retries: 1
  
  lightweight:
    model: "gemini-2.5-flash-lite"  # Cost-effective for analysis
    max_output_tokens: 16384
    temperature: 0.2
    max_retries: 3
```

### Team Configuration

```yaml
team:
  squad_size: 15
  position_limits:
    GK: 2
    DEF: 5
    MID: 5
    FWD: 3
  budget: 100.0
  max_players_per_team: 3
```

### Embedding Configuration

```yaml
embeddings:
  use_embeddings: true
  model: "BAAI/bge-base-en-v1.5"
  cache_enabled: true
  cache_expiry_hours: 24
  batch_size: 100
```

## 📊 Output Examples

### Team Creation Output
```
⚽ Building new FPL team...
🔄 Using RAG mode: ranked_enrichments
✅ Gameweek data loaded

⚽ Building team with £100.0m budget...

FPL TEAM CREATION COMPLETE
================================================================================

SELECTED TEAM
====================================================================================================
Name                     Team           Pos  Price  Form   Total Pts  Captain 
----------------------------------------------------------------------------------------------------
Haaland                  Man City       FWD  £12.1  8.2    156        C       
Salah                    Liverpool      MID  £13.2  7.8    142        VC      
Alexander-Arnold         Liverpool      DEF  £8.5   6.5    89         -       
...

Team Cost: £99.8m
Expected Points: 67.3
Confidence: 0.82

REASONING
================================================================================
AI Analysis: Team selection based on current form, fixture difficulty, and expert insights.
Key factors include Haaland's home fixtures, Salah's penalty duties, and defensive coverage...
```

### Weekly Update Output
```
🔄 Starting weekly FPL update...
🔄 Using RAG mode: ranked_enrichments
✅ Team context loaded for gameweek 15
✅ Gameweek data loaded
✅ Current team player data loaded

⚽ Updating team for gameweek 15...

WEEKLY FPL UPDATE COMPLETE
================================================================================

RECOMMENDED TRANSFERS
================================================================================
1. Sterling → Foden
   Reason: Foden's superior form and upcoming fixture advantage
   Transfer Confidence: 0.76

CAPTAINCY RECOMMENDATIONS
================================================================================
Captain: Haaland
Vice Captain: Salah
Reasoning: Haaland's home fixture against weak defense

CHIP USAGE
================================================================================
Use Wildcard: NO
Confidence: 0.68
Reasoning: Current team structure is optimal for upcoming fixtures
```

## 🏗️ Architecture

### Project Structure
```
fpl_agent/
├── core/
│   ├── config.py              # Configuration management
│   └── team_manager.py        # Team persistence and management
├── data/
│   ├── data_service.py        # Main data orchestration
│   ├── fetch_fpl.py           # FPL API integration
│   ├── data_store.py          # Data persistence
│   ├── data_processor.py      # Data processing and transformation
│   └── embedding_filter.py    # AI-powered player filtering
├── strategies/
│   ├── base_strategy.py       # Base LLM strategy class
│   ├── team_building_strategy.py  # Team creation and updates
│   ├── team_analysis_strategy.py # Player analysis and insights
│   └── llm_engine.py          # LLM integration
├── utils/
│   ├── display.py             # Output formatting
│   ├── validator.py           # Data validation
│   ├── prompt_formatter.py    # LLM prompt generation
│   └── schemas.py             # JSON schemas for LLM responses
├── main.py                    # CLI interface
└── config.yaml               # Configuration file
```

### Data Flow

1. **Data Fetching**: FPL API → Data Processing → Storage
2. **Enrichment**: Player Data → LLM Analysis → Expert Insights
3. **Team Building**: Enriched Data → LLM Strategy → Team Selection
4. **Weekly Updates**: Current Team → LLM Analysis → Recommendations

## 🤖 AI Integration

### LLM Models Used
- **Gemini 2.5 Pro**: Primary model for complex team optimization
- **Gemini 2.5 Flash Lite**: Cost-effective model for player analysis

### AI Features
- **Expert Insights**: AI-generated analysis of player potential
- **Injury Monitoring**: Real-time injury status tracking
- **Embedding Filtering**: Semantic similarity-based player selection
- **RAG System**: Combines data retrieval with AI generation

## 📈 Performance Tips

1. **Use Caching**: Enable `--cached-only` for faster operations
2. **RAG Modes**: Choose appropriate RAG mode based on your needs:
   - `none`: Fastest, no player LLM enrichments
   - `enrichments`: Basic player LLM enrichments
   - `ranked_enrichments`: Full player LLM enrichments (recommended)
3. **Regular Updates**: Run weekly updates before each deadline
4. **Multi-Team Management**: Use `--all-teams` for bulk operations

## 🛠️ Development

### Customizing LLM Prompts
Edit prompt templates in the strategy classes:
- `TeamBuildingStrategy._create_team_creation_prompt()`
- `TeamBuildingStrategy._create_weekly_update_prompt()`
- `TeamAnalysisStrategy._create_hints_tips_prompt()`

### Extending Data Sources
Modify `data/fetch_fpl.py` to add new data sources or APIs.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

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
