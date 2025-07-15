#!/usr/bin/env python3
"""
Yemen Qaat Production Server
Run this script to start the Yemen Qaat application server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🇾🇪 Yemen Qaat Application Server")
    print("=" * 40)
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    src_dir = script_dir / "src"
    
    # Change to the source directory
    os.chdir(src_dir)
    
    print(f"📁 Working directory: {src_dir}")
    print("🚀 Starting Yemen Qaat server...")
    print("📱 Frontend will be available at: http://localhost:5000")
    print("🔧 API will be available at: http://localhost:5000/api")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 40)
    
    try:
        # Run the Flask application
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

