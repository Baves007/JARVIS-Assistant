"""
JARVIS AI Assistant - Main Entry Point
Iron Man style HUD Dashboard
"""

import sys
import threading
from jarvis_core import JarvisCore
from dashboard import JarvisDashboard


def main():
    print("Initializing JARVIS AI Assistant...")
    print(" Starting core systems...")

   
    jarvis = JarvisCore()

   
    dashboard = JarvisDashboard(jarvis)
    
  
    voice_thread = threading.Thread(target=jarvis.start_listening, daemon=True)
    voice_thread.start()

    print("JARVIS online. Say 'Hey Jarvis' to activate.")
    
    
    dashboard.run()


if __name__ == "__main__":
    main()
