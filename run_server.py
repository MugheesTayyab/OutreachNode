#!/usr/bin/env python3
"""
Simple Flask server launcher for Outreach Node.
Run: python run_server.py
"""
from app import app

if __name__ == "__main__":
    print("Starting Outreach Node Flask application...")
    print("Server will be available at: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=True)
