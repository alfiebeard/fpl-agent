# FPL Optimizer

A comprehensive Fantasy Premier League optimization tool that provides data-driven team selection, transfer suggestions, and player analysis.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r fpl_optimizer/requirements.txt

# Run the main optimizer
python fpl_optimizer.py --help

# Create an optimal team from scratch
python fpl_optimizer.py --create-team

# Show player rankings
python fpl_optimizer.py --show-rankings

# Launch the GUI
python fpl_optimizer.py --gui
```

## 📁 Project Structure

```
fpl-agent/
├── fpl_optimizer.py              # Main launcher script
├── fpl_optimizer/                # Core module
│   ├── __init__.py
│   ├── main.py                   # Main application logic
│   ├── config.py                 # Configuration management
│   ├── config.yaml              # Configuration file
│   ├── models.py                # Data models
│   ├── gui.py                   # Streamlit GUI
│   ├── requirements.txt         # Python dependencies
│   ├── setup.py                 # Package setup
│   ├── README.md                # Module documentation
│   ├── data/                    # Data management
│   │   ├── __init__.py
│   │   ├── historical_data.py
│   │   ├── xg_xa_fetcher.py
│   │   ├── processed/           # Processed data storage
│   │   └── raw/                 # Raw data storage
│   ├── ingestion/               # Data ingestion
│   │   ├── __init__.py
│   │   ├── fetch_fpl.py
│   │   ├── fetch_understat.py
│   │   └── fetch_fbref.py
│   ├── processing/              # Data processing
│   │   ├── __init__.py
│   │   ├── compute_form.py
│   │   ├── join_data.py
│   │   └── normalize.py
│   ├── projection/              # Expected points calculation
│   │   ├── __init__.py
│   │   ├── xpts.py
│   │   ├── historical_xpts.py
│   │   ├── fixture_difficulty.py
│   │   └── predict_minutes.py
│   ├── optimizer/               # Optimization algorithms
│   │   ├── __init__.py
│   │   ├── ilp_solver.py
│   │   ├── transfer_optimizer.py
│   │   └── chip_strategy.py
│   ├── llm_layer/               # AI/LLM integration
│   │   ├── __init__.py
│   │   ├── extract_insights.py
│   │   └── summarize_tips.py
│   ├── output/                  # Report generation
│   │   ├── __init__.py
│   │   ├── generate_report.py
│   │   └── visualize.py
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   └── player_ranking.py
│   └── tests/                   # Test suite
│       ├── __init__.py
│       ├── test_optimizer.py
│       ├── test_xpts.py
│       ├── test_data_sources.py
│       └── test_real_apis.py
├── reports/                     # Generated reports
├── fpl_optimizer_readme.md      # Detailed documentation
└── README.md                    # This file
```

## 🎯 Features

### Core Functionality
- **Team Optimization**: Create optimal teams from scratch using ILP optimization
- **Transfer Optimization**: Optimize transfers for existing teams
- **Expected Points Calculation**: Advanced xPts calculation with multiple data sources
- **Player Rankings**: Comprehensive player analysis and rankings
- **Data Integration**: Multiple data sources (FPL API, FBRef, Understat)

### Analysis Tools
- **Player Rankings**: Sort by xPts, price, form, position, team
- **xPts Table**: Comprehensive table with detailed breakdowns (xG, xA, clean sheets, bonus, cards, minutes)
- **Value Analysis**: Find best value players at different price points
- **Position Analysis**: Top players by position (GK, DEF, MID, FWD)
- **Team Analysis**: Team strength and fixture difficulty analysis

### Data Sources
- **FPL API**: Official Fantasy Premier League data
- **FBRef**: Advanced statistics and xG/xA data
- **Understat**: Expected goals and assists data
- **Historical Data**: Multi-season performance analysis

## 🛠️ Usage

### Command Line Interface

```bash
# Show all available commands
python fpl_optimizer.py --help

# Create optimal team from scratch
python fpl_optimizer.py --create-team

# Optimize transfers for existing team
python fpl_optimizer.py --optimize-transfers --team-id 123456

# Show player rankings
python fpl_optimizer.py --show-rankings

# Check FPL API data quality
python fpl_optimizer.py --check-data

# Debug player data
python fpl_optimizer.py --debug-players

# Show detailed expected points
python fpl_optimizer.py --show-xpts

# Show comprehensive xPts table with breakdowns
python fpl_optimizer.py --show-xpts-table

# Export detailed xPts table to CSV
python fpl_optimizer.py --export-xpts-table xpts_breakdown.csv

# Export rankings to CSV
python fpl_optimizer.py --export-rankings rankings.csv

# Interactive mode
python fpl_optimizer.py --interactive

# Launch GUI
python fpl_optimizer.py --gui
```

### GUI Interface

Launch the Streamlit GUI for an interactive experience:

```bash
python fpl_optimizer.py --gui
```

The GUI provides:
- Interactive team builder
- Player search and filtering
- Real-time optimization
- Visual reports and charts

## 📊 Data Sources

### FPL API
- Player statistics and form
- Team information
- Fixture data and difficulty ratings
- Live gameweek data

### FBRef
- Advanced statistics (xG, xA, xCS)
- Minutes played data
- Historical performance metrics

### Understat
- Expected goals and assists
- Team attacking/defending metrics
- Historical xG/xA data

## 🔧 Configuration

Edit `fpl_optimizer/config.yaml` to customize:

```yaml
# Optimization settings
optimization:
  max_transfers: 2
  xpts_decay_factor: 0.85
  budget: 100.0

# Data sources
data_sources:
  fbref_enabled: true
  understat_enabled: true
  cache_duration: 3600

# Points system
points:
  goal:
    gk: 6
    def: 6
    mid: 5
    fwd: 4
  assist: 3
  clean_sheet:
    gk: 4
    def: 4
    mid: 1
    fwd: 0
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest fpl_optimizer/tests/

# Run specific test modules
python fpl_optimizer/tests/test_data_sources.py
python fpl_optimizer/tests/test_real_apis.py
python fpl_optimizer/tests/test_optimizer.py
python fpl_optimizer/tests/test_xpts.py
```

## 📈 Expected Points Calculation

The xPts calculation uses a sophisticated model that considers:

- **Goals & Assists**: Based on xG/xA data from multiple sources
- **Clean Sheets**: Team defensive strength and fixture difficulty
- **Bonus Points**: Player performance metrics
- **Cards**: Historical disciplinary records
- **Minutes**: Team rotation risk and fixture difficulty
- **Form**: Recent performance trends
- **Fixture Difficulty**: Opposition strength and home/away advantage

## 🤖 AI Integration

The optimizer includes LLM integration for:

- **Insight Extraction**: AI-powered analysis of player performance
- **Transfer Reasoning**: Explainable transfer suggestions
- **Risk Assessment**: AI evaluation of transfer risks
- **Trend Analysis**: Pattern recognition in player form

## 📝 Reports

Generated reports include:

- **Team Analysis**: Current team performance and recommendations
- **Transfer Suggestions**: Optimized transfer recommendations
- **Player Rankings**: Comprehensive player analysis
- **Fixture Analysis**: Upcoming fixture difficulty assessment
- **Risk Assessment**: Transfer and selection risk evaluation

## 🔄 Development

### Adding New Features

1. **Data Sources**: Add new data fetchers in `ingestion/`
2. **Algorithms**: Implement new optimization algorithms in `optimizer/`
3. **Models**: Extend data models in `models.py`
4. **Analysis**: Add new analysis tools in `utils/`

### Code Style

- Follow PEP 8 style guidelines
- Use type hints throughout
- Include comprehensive docstrings
- Write unit tests for new functionality

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For questions or issues:
- Check the documentation in `fpl_optimizer_readme.md`
- Review the test files for usage examples
- Open an issue on GitHub

---

**Note**: This tool is for educational and entertainment purposes. Always verify FPL decisions independently and consider the official FPL rules and deadlines. 