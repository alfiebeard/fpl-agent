"""
Data visualization for FPL Optimizer
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

from ..config import Config


logger = logging.getLogger(__name__)


class DataVisualizer:
    """Creates visualizations for FPL data and optimization results"""
    
    def __init__(self, config: Config):
        self.config = config
        self.output_config = config.get_output_config()
        
        # Set matplotlib style
        plt.style.use('default')
        
    def create_player_comparison_chart(self, players: List, player_xpts: Dict[int, float],
                                     top_n: int = 20) -> str:
        """Create a chart comparing top players by expected points"""
        
        logger.info("Creating player comparison chart...")
        
        try:
            # Create DataFrame
            data = []
            for player in players:
                if player.id in player_xpts:
                    data.append({
                        'Player': player.name,
                        'Team': player.team_name,
                        'Position': player.position.value,
                        'Price': player.price,
                        'xPts': player_xpts[player.id],
                        'Form': player.form,
                        'Points per Game': player.points_per_game
                    })
            
            df = pd.DataFrame(data)
            
            # Sort by expected points and take top N
            df = df.sort_values('xPts', ascending=False).head(top_n)
            
            # Create plotly figure
            fig = go.Figure()
            
            # Color by position
            colors = {'GK': '#1f77b4', 'DEF': '#ff7f0e', 'MID': '#2ca02c', 'FWD': '#d62728'}
            
            for position in df['Position'].unique():
                pos_data = df[df['Position'] == position]
                fig.add_trace(go.Bar(
                    x=pos_data['Player'],
                    y=pos_data['xPts'],
                    name=position,
                    marker_color=colors.get(position, '#7f7f7f'),
                    text=pos_data['xPts'].round(2),
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>' +
                                'Team: %{customdata[0]}<br>' +
                                'Position: %{customdata[1]}<br>' +
                                'Price: £%{customdata[2]}m<br>' +
                                'xPts: %{y:.2f}<br>' +
                                'Form: %{customdata[3]}<br>' +
                                'PPG: %{customdata[4]:.2f}<extra></extra>',
                    customdata=list(zip(pos_data['Team'], pos_data['Position'], 
                                      pos_data['Price'], pos_data['Form'], 
                                      pos_data['Points per Game']))
                ))
            
            fig.update_layout(
                title=f'Top {top_n} Players by Expected Points',
                xaxis_title='Player',
                yaxis_title='Expected Points',
                barmode='group',
                height=600,
                showlegend=True
            )
            
            # Save the chart
            filename = f"player_comparison_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = f"reports/{filename}"
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create player comparison chart: {e}")
            return ""
    
    def create_team_value_analysis(self, players: List, player_xpts: Dict[int, float]) -> str:
        """Create a scatter plot of value vs expected points"""
        
        logger.info("Creating team value analysis chart...")
        
        try:
            # Create DataFrame
            data = []
            for player in players:
                if player.id in player_xpts:
                    data.append({
                        'Player': player.name,
                        'Team': player.team_name,
                        'Position': player.position.value,
                        'Price': player.price,
                        'xPts': player_xpts[player.id],
                        'Value': player_xpts[player.id] / player.price if player.price > 0 else 0
                    })
            
            df = pd.DataFrame(data)
            
            # Create plotly scatter plot
            fig = px.scatter(
                df, x='Price', y='xPts', 
                color='Position', 
                hover_data=['Player', 'Team', 'Value'],
                title='Player Value Analysis: Price vs Expected Points',
                labels={'Price': 'Price (£m)', 'xPts': 'Expected Points'}
            )
            
            # Add trend line
            z = np.polyfit(df['Price'], df['xPts'], 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(
                x=df['Price'], 
                y=p(df['Price']),
                mode='lines',
                name='Trend Line',
                line=dict(color='red', dash='dash')
            ))
            
            fig.update_layout(height=600)
            
            # Save the chart
            filename = f"value_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = f"reports/{filename}"
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create value analysis chart: {e}")
            return ""
    
    def create_optimization_summary(self, optimization_result, 
                                  current_team_xpts: float) -> str:
        """Create a summary chart of optimization results"""
        
        logger.info("Creating optimization summary chart...")
        
        try:
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Expected Points Comparison', 'Confidence Level', 
                              'Formation Distribution', 'Transfer Impact'),
                specs=[[{"type": "bar"}, {"type": "indicator"}],
                       [{"type": "pie"}, {"type": "bar"}]]
            )
            
            # 1. Expected Points Comparison
            fig.add_trace(
                go.Bar(
                    x=['Current Team', 'Optimized Team'],
                    y=[current_team_xpts, optimization_result.expected_points],
                    name='Expected Points',
                    marker_color=['#ff7f0e', '#2ca02c']
                ),
                row=1, col=1
            )
            
            # 2. Confidence Level
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=optimization_result.confidence * 100,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Confidence (%)"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkblue"},
                           'steps': [
                               {'range': [0, 50], 'color': "lightgray"},
                               {'range': [50, 80], 'color': "yellow"},
                               {'range': [80, 100], 'color': "green"}
                           ]}
                ),
                row=1, col=2
            )
            
            # 3. Formation Distribution
            formation = optimization_result.formation
            fig.add_trace(
                go.Pie(
                    labels=['Defenders', 'Midfielders', 'Forwards'],
                    values=formation,
                    name="Formation"
                ),
                row=2, col=1
            )
            
            # 4. Transfer Impact
            if optimization_result.transfers:
                transfer_costs = [t.cost for t in optimization_result.transfers]
                transfer_names = [f"{t.player_out.name} → {t.player_in.name}" 
                                for t in optimization_result.transfers]
                
                fig.add_trace(
                    go.Bar(
                        x=transfer_names,
                        y=transfer_costs,
                        name='Transfer Cost',
                        marker_color='red'
                    ),
                    row=2, col=2
                )
            else:
                fig.add_trace(
                    go.Bar(
                        x=['No Transfers'],
                        y=[0],
                        name='Transfer Cost',
                        marker_color='green'
                    ),
                    row=2, col=2
                )
            
            fig.update_layout(
                title_text="FPL Optimization Summary",
                height=800,
                showlegend=False
            )
            
            # Save the chart
            filename = f"optimization_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = f"reports/{filename}"
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create optimization summary chart: {e}")
            return ""
    
    def create_fixture_difficulty_chart(self, fixtures: List, teams: List) -> str:
        """Create a fixture difficulty heatmap"""
        
        logger.info("Creating fixture difficulty chart...")
        
        try:
            # Create fixture matrix
            team_names = [team.name for team in teams]
            fixture_matrix = np.zeros((len(team_names), len(team_names)))
            
            for fixture in fixtures:
                home_idx = next((i for i, name in enumerate(team_names) 
                               if name == fixture.home_team_name), None)
                away_idx = next((i for i, name in enumerate(team_names) 
                               if name == fixture.away_team_name), None)
                
                if home_idx is not None and away_idx is not None:
                    fixture_matrix[home_idx][away_idx] = fixture.home_difficulty
                    fixture_matrix[away_idx][home_idx] = fixture.away_difficulty
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=fixture_matrix,
                x=team_names,
                y=team_names,
                colorscale='RdYlGn_r',  # Red (hard) to Green (easy)
                zmin=1, zmax=5,
                text=fixture_matrix.round(1),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title='Fixture Difficulty Matrix',
                xaxis_title='Away Team',
                yaxis_title='Home Team',
                height=800
            )
            
            # Save the chart
            filename = f"fixture_difficulty_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = f"reports/{filename}"
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create fixture difficulty chart: {e}")
            return ""
    
    def create_team_performance_chart(self, teams: List) -> str:
        """Create a team performance comparison chart"""
        
        logger.info("Creating team performance chart...")
        
        try:
            # Create DataFrame
            data = []
            for team in teams:
                data.append({
                    'Team': team.name,
                    'Strength': team.strength,
                    'Form': team.form,
                    'xG': team.xG,
                    'xGA': team.xGA
                })
            
            df = pd.DataFrame(data)
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Team Strength', 'Team Form', 'Expected Goals', 'Expected Goals Against'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "bar"}]]
            )
            
            # Team Strength
            fig.add_trace(
                go.Bar(x=df['Team'], y=df['Strength'], name='Strength'),
                row=1, col=1
            )
            
            # Team Form
            fig.add_trace(
                go.Bar(x=df['Team'], y=df['Form'], name='Form'),
                row=1, col=2
            )
            
            # Expected Goals
            fig.add_trace(
                go.Bar(x=df['Team'], y=df['xG'], name='xG'),
                row=2, col=1
            )
            
            # Expected Goals Against
            fig.add_trace(
                go.Bar(x=df['Team'], y=df['xGA'], name='xGA'),
                row=2, col=2
            )
            
            fig.update_layout(
                title_text="Team Performance Comparison",
                height=800,
                showlegend=False
            )
            
            # Save the chart
            filename = f"team_performance_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = f"reports/{filename}"
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create team performance chart: {e}")
            return ""
