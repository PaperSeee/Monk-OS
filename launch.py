#!/usr/bin/env python3
"""
MONK-OS Launcher — Launches the app as a native application
"""

import subprocess
import webbrowser
import time
import sys
import os

def launch_app():
    """Launch Streamlit app and open in browser"""
    
    # Get the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(app_dir, "app.py")
    
    print("🚀 Lancement de MONK-OS...")
    print("   localhost:8503 s'ouvrira automatiquement dans 3 secondes...\n")
    
    # Start Streamlit app
    try:
        # Launch Streamlit in a subprocess
        process = subprocess.Popen(
            ["streamlit", "run", app_file, "--server.port", "8503", "--logger.level=error"],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a bit for server to start, then open browser
        time.sleep(3)
        webbrowser.open("http://localhost:8503")
        
        # Keep process running
        process.wait()
    except KeyboardInterrupt:
        print("\n\n✓ MONK-OS fermée")
        sys.exit(0)
    except FileNotFoundError:
        print("❌ Erreur: Streamlit n'est pas installé")
        print("   Installez-le avec: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    launch_app()
