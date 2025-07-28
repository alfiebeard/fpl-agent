#!/usr/bin/env python3
"""
Launcher script for FPL Optimizer GUI
"""

import subprocess
import sys
import os

def main():
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