#!/usr/bin/env python3
"""
FPL Optimizer - Main Launcher Script

A comprehensive Fantasy Premier League optimization tool that provides:
- Team optimization and transfer suggestions
- Player rankings and analysis
- Data debugging and validation
- Interactive mode for custom queries

Usage:
    python fpl_optimizer.py --help                    # Show all available commands
    python fpl_optimizer.py --create-team            # Create optimal team from scratch
    python fpl_optimizer.py --optimize-transfers     # Optimize transfers for existing team
    python fpl_optimizer.py --show-rankings          # Show player rankings
    python fpl_optimizer.py --check-data             # Check FPL API data
    python fpl_optimizer.py --interactive            # Run interactive mode
    python fpl_optimizer.py --gui                    # Launch GUI
"""

import sys
import subprocess
import os

def main():
    """Main launcher function"""
    
    # Check if any arguments were provided
    if len(sys.argv) == 1:
        print(__doc__)
        return
    
    # Special case for GUI
    if '--gui' in sys.argv:
        launch_gui()
        return
    
    # For all other commands, delegate to the main module
    try:
        from fpl_optimizer.main import main as fpl_main
        fpl_main()
    except ImportError as e:
        print(f"❌ Error importing FPL Optimizer: {e}")
        print("Make sure you're in the correct directory and the module is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running FPL Optimizer: {e}")
        sys.exit(1)

def launch_gui():
    """Launch the Streamlit GUI"""
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Launch the Streamlit app
    print("🚀 Launching FPL Optimizer GUI...")
    print("📱 The GUI will open in your default web browser")
    print("🔗 If it doesn't open automatically, go to: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "fpl_optimizer/gui.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 GUI stopped. Goodbye!")

if __name__ == "__main__":
    main() 