"""
Streamlit GUI for FPL Optimizer
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .main import FPLOptimizer
from .config import Config


def main():
    """Main Streamlit application"""
    
    st.set_page_config(
        page_title="FPL Optimizer",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1e3a8a;
        margin: 0.5rem 0;
    }
    .transfer-card {
        background-color: #fef3c7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f59e0b;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🧐 FPL Optimizer</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem;">Fully Automated Fantasy Premier League Manager</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Gameweek selection
        gameweek = st.number_input("Gameweek", min_value=1, max_value=38, value=1)
        
        # Team ID
        team_id = st.number_input("FPL Team ID (optional)", min_value=1, value=None)
        
        # Planning window
        planning_window = st.slider("Planning Window (gameweeks)", min_value=1, max_value=10, value=5)
        
        # Transfer threshold
        transfer_threshold = st.slider("Transfer Hit Threshold (points)", min_value=1, max_value=10, value=4)
        
        # Run button
        if st.button("🚀 Run Optimization", type="primary"):
            st.session_state.run_optimization = True
    
    # Main content
    if 'run_optimization' in st.session_state and st.session_state.run_optimization:
        run_optimization_interface(gameweek, team_id, planning_window, transfer_threshold)
    else:
        show_welcome_screen()


def show_welcome_screen():
    """Show welcome screen with instructions"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ## 🎯 Welcome to FPL Optimizer!
        
        This tool uses advanced algorithms and AI to optimize your Fantasy Premier League team.
        
        ### How it works:
        1. **Data Analysis**: Fetches player stats, fixtures, and expert insights
        2. **Expected Points**: Calculates xPts using sophisticated models
        3. **Optimization**: Uses Integer Linear Programming for optimal team selection
        4. **AI Insights**: Incorporates expert tips and analysis
        5. **Smart Transfers**: Recommends transfers with cost-benefit analysis
        
        ### Features:
        - ✅ Automated team selection
        - ✅ Transfer optimization
        - ✅ Captain selection
        - ✅ Injury management
        - ✅ Beautiful visualizations
        - ✅ AI-powered insights
        
        ### Getting Started:
        1. Configure your settings in the sidebar
        2. Click "Run Optimization"
        3. Review the results and recommendations
        4. Apply changes to your FPL team
        
        ---
        
        **Note**: This tool is for educational purposes. Always verify decisions before making transfers.
        """)
        
        # Show sample metrics
        st.subheader("📊 Sample Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Expected Points", "78.5", "↑ 12.3")
        
        with col2:
            st.metric("Confidence", "85%", "↑ 5%")
        
        with col3:
            st.metric("Transfers", "2", "↓ 1")
        
        with col4:
            st.metric("Formation", "3-4-3", "→")


def run_optimization_interface(gameweek, team_id, planning_window, transfer_threshold):
    """Run optimization and display results"""
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize optimizer
        status_text.text("Initializing optimizer...")
        progress_bar.progress(10)
        
        optimizer = FPLOptimizer()
        
        # Update config with user settings
        optimizer.config._config['optimization']['planning_window'] = planning_window
        optimizer.config._config['optimization']['transfer_hit_threshold'] = transfer_threshold
        
        # Run optimization
        status_text.text("Fetching data...")
        progress_bar.progress(20)
        
        status_text.text("Processing data...")
        progress_bar.progress(40)
        
        status_text.text("Calculating expected points...")
        progress_bar.progress(60)
        
        status_text.text("Getting AI insights...")
        progress_bar.progress(80)
        
        status_text.text("Optimizing team...")
        progress_bar.progress(90)
        
        result = optimizer.run_optimization(gameweek=gameweek, team_id=team_id)
        
        progress_bar.progress(100)
        status_text.text("Optimization complete!")
        
        # Display results
        display_optimization_results(result, optimizer)
        
    except Exception as e:
        st.error(f"Optimization failed: {str(e)}")
        st.exception(e)


def display_optimization_results(result, optimizer):
    """Display optimization results"""
    
    # Clear progress indicators
    st.empty()
    
    # Results header
    st.success("✅ Optimization completed successfully!")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Expected Points", 
            f"{result.expected_points:.1f}",
            delta=f"+{result.expected_points - 70:.1f}" if result.expected_points > 70 else f"{result.expected_points - 70:.1f}"
        )
    
    with col2:
        st.metric(
            "Confidence", 
            f"{result.confidence:.1%}",
            delta=f"+{result.confidence - 0.7:.1%}" if result.confidence > 0.7 else f"{result.confidence - 0.7:.1%}"
        )
    
    with col3:
        st.metric(
            "Transfers", 
            len(result.transfers),
            delta=f"-{2 - len(result.transfers)}" if len(result.transfers) < 2 else "0"
        )
    
    with col4:
        formation_str = f"{result.formation[0]}-{result.formation[1]}-{result.formation[2]}"
        st.metric("Formation", formation_str)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🔄 Transfers", "🤖 AI Insights", "📊 Visualizations"])
    
    with tab1:
        display_summary_tab(result)
    
    with tab2:
        display_transfers_tab(result)
    
    with tab3:
        display_insights_tab(result)
    
    with tab4:
        display_visualizations_tab(result, optimizer)


def display_summary_tab(result):
    """Display summary tab"""
    
    st.subheader("📋 Optimization Summary")
    
    # Formation breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Formation")
        formation_data = {
            'Position': ['Defenders', 'Midfielders', 'Forwards'],
            'Count': result.formation
        }
        df_formation = pd.DataFrame(formation_data)
        
        fig = px.pie(df_formation, values='Count', names='Position', 
                    title="Team Formation")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Captain Selection")
        if result.captain_id:
            st.info(f"**Captain**: Player ID {result.captain_id}")
        if result.vice_captain_id:
            st.info(f"**Vice Captain**: Player ID {result.vice_captain_id}")
        
        st.markdown("### Reasoning")
        st.write(result.reasoning)
    
    # Performance comparison
    st.markdown("### Expected Performance")
    
    # Mock current team performance for comparison
    current_performance = 70.0  # This would come from actual current team
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=['Current Team', 'Optimized Team'],
        y=[current_performance, result.expected_points],
        marker_color=['#ff7f0e', '#2ca02c'],
        text=[f"{current_performance:.1f}", f"{result.expected_points:.1f}"],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Expected Points Comparison",
        yaxis_title="Expected Points",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_transfers_tab(result):
    """Display transfers tab"""
    
    st.subheader("🔄 Transfer Recommendations")
    
    if result.transfers:
        st.markdown(f"**Recommended Transfers ({len(result.transfers)}):**")
        
        for i, transfer in enumerate(result.transfers, 1):
            with st.container():
                st.markdown(f"""
                <div class="transfer-card">
                    <h4>Transfer {i}</h4>
                    <p><strong>OUT:</strong> {transfer.player_out.name} ({transfer.player_out.team_name})</p>
                    <p><strong>IN:</strong> {transfer.player_in.name} ({transfer.player_in.team_name})</p>
                    <p><strong>Cost:</strong> {transfer.cost} points</p>
                    <p><strong>Reason:</strong> {transfer.reason}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Transfer impact analysis
        st.markdown("### Transfer Impact Analysis")
        
        transfer_costs = [t.cost for t in result.transfers]
        total_cost = sum(transfer_costs)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Transfer Cost", f"{total_cost} points")
        
        with col2:
            st.metric("Net Expected Gain", f"{result.expected_points - 70:.1f} points")
        
        with col3:
            net_gain = result.expected_points - 70 - total_cost
            st.metric("Net Gain After Cost", f"{net_gain:.1f} points")
        
    else:
        st.success("✅ No transfers recommended!")
        st.info("Your current team is already optimized for this gameweek.")
        
        # Show current team strength
        st.markdown("### Current Team Analysis")
        st.metric("Team Strength", "Strong", "↑")


def display_insights_tab(result):
    """Display AI insights tab"""
    
    st.subheader("🤖 AI Insights & Expert Tips")
    
    if result.llm_insights:
        st.markdown("### Expert Analysis")
        st.info(result.llm_insights)
    else:
        st.info("No AI insights available for this optimization.")
    
    # Mock insights for demonstration
    st.markdown("### Key Insights")
    
    insights = [
        "🎯 **Captain Pick**: Haaland has excellent home form and favorable fixture",
        "⚡ **Differential**: Consider Saka as a differential pick (5% ownership)",
        "🚨 **Injury Alert**: De Bruyne doubtful, consider alternatives",
        "📈 **Form Watch**: Arsenal players showing strong underlying stats",
        "💰 **Value Pick**: Toney offers great value at his price point"
    ]
    
    for insight in insights:
        st.markdown(f"- {insight}")
    
    # Confidence breakdown
    st.markdown("### Confidence Breakdown")
    
    confidence_factors = {
        'Data Quality': 0.9,
        'Model Accuracy': 0.8,
        'Expert Consensus': 0.7,
        'Fixture Difficulty': 0.85,
        'Player Form': 0.75
    }
    
    fig = go.Figure(data=[
        go.Bar(x=list(confidence_factors.keys()), 
               y=list(confidence_factors.values()),
               marker_color='lightblue')
    ])
    
    fig.update_layout(
        title="Confidence Factors",
        yaxis_title="Confidence Score",
        yaxis_range=[0, 1],
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_visualizations_tab(result, optimizer):
    """Display visualizations tab"""
    
    st.subheader("📊 Data Visualizations")
    
    # Mock data for visualizations
    st.info("📈 Interactive charts and visualizations would be generated here based on the optimization results.")
    
    # Sample player comparison chart
    st.markdown("### Top Players by Expected Points")
    
    # Mock player data
    players_data = {
        'Player': ['Haaland', 'Salah', 'Saka', 'Toney', 'Kane'],
        'Team': ['Man City', 'Liverpool', 'Arsenal', 'Brentford', 'Spurs'],
        'Position': ['FWD', 'MID', 'MID', 'FWD', 'FWD'],
        'xPts': [8.5, 7.2, 6.8, 6.5, 6.2],
        'Price': [12.0, 11.5, 8.0, 7.5, 10.0]
    }
    
    df_players = pd.DataFrame(players_data)
    
    fig = px.bar(df_players, x='Player', y='xPts', 
                color='Position', 
                title="Top Players by Expected Points",
                hover_data=['Team', 'Price'])
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Value analysis
    st.markdown("### Player Value Analysis")
    
    fig = px.scatter(df_players, x='Price', y='xPts', 
                    color='Position', 
                    size='xPts',
                    hover_data=['Player', 'Team'],
                    title="Price vs Expected Points")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Formation distribution
    st.markdown("### Formation Distribution")
    
    formation_data = {
        'Formation': ['3-4-3', '3-5-2', '4-3-3', '4-4-2', '5-3-2'],
        'Usage': [35, 25, 20, 15, 5]
    }
    
    df_formation = pd.DataFrame(formation_data)
    
    fig = px.pie(df_formation, values='Usage', names='Formation',
                title="Most Popular Formations")
    
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main() 