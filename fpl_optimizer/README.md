# 🧐 FPL Optimizer — Fully Automated Fantasy Premier League Manager

A fully automated, AI-assisted Fantasy Premier League (FPL) team manager that uses expected points models, fixture forecasting, optimization, and natural language analysis to build and maintain the optimal team across the season.

## 🌟 Features

- **Automated Team Selection**: Uses Integer Linear Programming (ILP) to optimize team selection based on expected points
- **Expected Points Calculation**: Sophisticated xPts model with fixture difficulty, form, and injury adjustments
- **LLM Integration**: AI-powered insights from expert tips and analysis
- **Transfer Optimization**: Smart transfer strategy with cost-benefit analysis
- **Injury Management**: Automatic injury detection and playing time adjustments
- **Scheduled Automation**: Runs automatically 30 minutes before each deadline
- **Beautiful Reports**: HTML, JSON, and text reports with visualizations
- **Human Approval**: Single-click approval system for changes

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fpl_optimizer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the optimizer**:
   ```bash
   python -m fpl_optimizer.main
   ```

### Configuration

The optimizer uses a YAML configuration file (`config.yaml`) with the following key settings:

```yaml
# LLM Configuration
llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "your-api-key-here"

# Optimization Settings
optimization:
  planning_window: 5  # Gameweeks to plan ahead
  xpts_decay_factor: 0.85  # Decay for future gameweeks
  transfer_hit_threshold: 4  # Minimum xPts gain for transfers

# Team Constraints
team:
  budget: 100.0
  max_players_per_team: 3
  valid_formations:
    - [3, 4, 3]
    - [3, 5, 2]
    - [4, 3, 3]
```

## 📊 How It Works

### 1. Data Ingestion
- **FPL API**: Player stats, fixtures, gameweeks
- **Understat**: xG/xA data for players
- **FBRef**: Additional statistics and injury data
- **LLM**: Expert tips and insights

### 2. Expected Points Calculation
The xPts formula considers:
- **Goals & Assists**: Based on xG/xA and fixture difficulty
- **Clean Sheets**: Team defense vs opponent attack
- **Bonus Points**: Attacking contribution probability
- **Cards**: Position-based yellow/red card risk
- **Playing Time**: Injury status and rotation risk

### 3. Optimization Engine
Uses Integer Linear Programming to:
- Maximize expected points over planning window
- Respect budget constraints (£100M)
- Maintain valid formations
- Limit transfers per gameweek
- Apply team limits (max 3 per club)

### 4. LLM Integration
- Summarizes expert tips from multiple sources
- Provides injury updates and playing time insights
- Adjusts xPts based on qualitative factors
- Offers captain and transfer recommendations

## 🛠️ Usage

### Command Line Interface

```bash
# Create initial team from scratch
python -m fpl_optimizer.main --create-team

# Create team for specific gameweek
python -m fpl_optimizer.main --create-team --gameweek 5

# Optimize transfers for existing team
python -m fpl_optimizer.main --optimize-transfers --max-transfers 2

# Optimize transfers for specific team
python -m fpl_optimizer.main --optimize-transfers --team-id 12345 --max-transfers 1

# Basic optimization (legacy mode)
python -m fpl_optimizer.main

# Optimize for specific gameweek
python -m fpl_optimizer.main --gameweek 5

# Use specific team ID
python -m fpl_optimizer.main --team-id 12345

# Run scheduled optimization
python -m fpl_optimizer.main --scheduled

# Use custom config
python -m fpl_optimizer.main --config my_config.yaml
```

### Programmatic Usage

```python
from fpl_optimizer import FPLOptimizer

# Initialize optimizer
optimizer = FPLOptimizer()

# Create initial team from scratch
result = optimizer.create_initial_team(gameweek=5)
print(f"Initial team expected points: {result.expected_points}")

# Optimize transfers for existing team
from fpl_optimizer.models import FPLTeam
current_team = FPLTeam(team_id=1, players=[])  # Your current team
result = optimizer.optimize_transfers(current_team, gameweek=5, max_transfers=2)
print(f"Transfer optimization expected points: {result.expected_points}")

# Legacy optimization (combines both approaches)
result = optimizer.run_optimization(gameweek=5)

# Access results
print(f"Expected Points: {result.expected_points}")
print(f"Transfers: {len(result.transfers)}")
print(f"Captain: {result.captain_id}")
```

## 📈 Output

The optimizer generates comprehensive reports including:

### HTML Reports
- Beautiful, interactive reports with charts
- Transfer recommendations with reasoning
- Captain and vice-captain selections
- AI insights and expert tips
- Formation and team structure

### Visualizations
- Player comparison charts
- Value analysis scatter plots
- Fixture difficulty heatmaps
- Team performance comparisons
- Optimization summary dashboards

### Data Formats
- **HTML**: Interactive web reports
- **JSON**: Machine-readable data
- **Text**: Simple console output

## 🔧 Architecture

```
fpl_optimizer/
├── ingestion/          # Data fetching modules
│   ├── fetch_fpl.py    # FPL API integration
│   ├── fetch_understat.py  # xG/xA data
│   └── fetch_fbref.py  # Additional stats
├── processing/         # Data processing
│   ├── normalize.py    # Data cleaning
│   └── compute_form.py # Form calculations
├── projection/         # Expected points
│   └── xpts.py        # xPts calculation engine
├── optimizer/          # Optimization engine
│   ├── ilp_solver.py   # Integer Linear Programming
│   └── transfer_optimizer.py  # Transfer logic
├── llm_layer/          # AI integration
│   └── summarize_tips.py  # LLM insights
├── output/             # Reports and visualizations
│   ├── generate_report.py  # Report generation
│   └── visualize.py    # Charts and graphs
└── main.py            # Main application
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test module
pytest fpl_optimizer/tests/test_xpts.py

# Run with coverage
pytest --cov=fpl_optimizer
```

## 🔄 Scheduling

For automated weekly runs:

```bash
# Set up cron job (Linux/Mac)
crontab -e

# Add this line to run 30 minutes before each deadline
0 11 * * 5 cd /path/to/fpl_optimizer && python -m fpl_optimizer.main --scheduled
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FPL API for providing official data
- Understat for xG/xA statistics
- FBRef for additional player data
- OpenAI for LLM capabilities
- The FPL community for inspiration and feedback

## 🆘 Support

- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join the community discussions
- **Documentation**: Check the inline code documentation

## 🔮 Roadmap

- [ ] Browser automation for automatic transfers
- [ ] Machine learning model for improved predictions
- [ ] Mobile app for quick approvals
- [ ] Integration with more data sources
- [ ] Advanced chip strategy optimization
- [ ] Historical performance analysis
- [ ] League comparison features

---

**Disclaimer**: This tool is for educational and entertainment purposes. Use at your own risk and always verify decisions before making transfers in FPL.
