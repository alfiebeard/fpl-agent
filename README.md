# FPL Optimizer

A streamlined Fantasy Premier League optimization tool that uses real-time API data to create optimal teams.

## Overview

FPL Optimizer is a Python application that:
- Fetches live data from FPL, Understat, and FBRef APIs
- Samples players dynamically (no hardcoded names)
- Optimizes team selection using Integer Linear Programming
- Provides fast, efficient optimization for testing and development

## Features

- **API-Driven**: All player and team data comes from live APIs
- **Dynamic Sampling**: Automatically samples players based on position and price distribution
- **Fast Testing**: Sample 50 players in ~20 seconds instead of fetching all 666
- **Streamlined**: Minimal dependencies, focused on core optimization
- **Extensible**: Clean architecture for adding features later

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fpl-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r fpl_optimizer/requirements.txt
```

## Usage

### Basic Optimization

Run the optimizer with default settings (50 players):
```bash
python -m fpl_optimizer.main
```

### Custom Sample Size

Optimize with a different number of players:
```bash
python -m fpl_optimizer.main --sample-size 100
```

### Custom Configuration

Use a custom config file:
```bash
python -m fpl_optimizer.main --config path/to/config.yaml
```

## Project Structure

```
fpl-agent/
├── fpl_optimizer/
│   ├── ingestion/           # Data fetching from APIs
│   │   ├── fetch_fpl.py     # FPL API integration
│   │   ├── fetch_understat.py # xG/xA data
│   │   ├── fetch_fbref.py   # Additional stats
│   │   └── test_data_fetcher.py # Dynamic sampling
│   ├── optimizer/           # Optimization algorithms
│   │   └── ilp_solver.py    # Integer Linear Programming solver
│   ├── models.py           # Data models
│   ├── config.py           # Configuration management
│   ├── config.yaml         # Configuration file
│   └── main.py             # Main application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Data Sources

- **FPL API**: Official Fantasy Premier League data (players, teams, fixtures)
- **Understat**: Expected Goals (xG) and Expected Assists (xA) statistics
- **FBRef**: Additional player and team statistics

## Configuration

Edit `fpl_optimizer/config.yaml` to customize:
- API endpoints
- Optimization parameters
- Data sampling settings

## Development

The application is designed to be easily extensible:

1. **Add new data sources**: Implement new fetchers in `ingestion/`
2. **Modify optimization**: Update `optimizer/ilp_solver.py`
3. **Add features**: Extend `main.py` with new functionality

## License

[Add your license here] 