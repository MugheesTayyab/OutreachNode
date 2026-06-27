#!/usr/bin/env python3
"""
Production Flask server launcher for Outreach Node.
Run: python run_production_server.py
"""
from app import app

if __name__ == "__main__":
    print("Starting Outreach Node Production Flask Application...")
    print("Server will be available at: http://127.0.0.1:5000")
    print("Production Mode: ENABLED")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
