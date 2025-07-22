#!/usr/bin/env python3
"""
Standalone ASGI server runner for Yargı MCP

This script provides a simple way to run the Yargı MCP server
as a web service using uvicorn.

Usage:
    python run_asgi.py
    python run_asgi.py --host 0.0.0.0 --port 8080
    python run_asgi.py --reload  # For development
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import uvicorn
except ImportError:
    print("Error: uvicorn is not installed.")
    print("Please install it with: pip install uvicorn")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(
        description="Run Yargı MCP server as an ASGI web service"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--transport",
        choices=["http", "sse"],
        default="http",
        help="Transport type (default: http)"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default=os.getenv("LOG_LEVEL", "info").lower(),
        help="Log level (default: info)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    args = parser.parse_args()
    
    # Select app based on transport
    app_name = "asgi_app:app" if args.transport == "http" else "asgi_app:sse_app"
    
    # Configure uvicorn
    config = {
        "app": app_name,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "reload": args.reload,
        "access_log": True,
    }
    
    # Add workers only if not in reload mode
    if not args.reload and args.workers > 1:
        config["workers"] = args.workers
    
    # Print startup information
    print(f"Starting Yargı MCP server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Transport: {args.transport}")
    print(f"Log level: {args.log_level}")
    if args.reload:
        print("Auto-reload: enabled")
    else:
        print(f"Workers: {args.workers}")
    print(f"\nServer will be available at: http://{args.host}:{args.port}")
    print(f"MCP endpoint: http://{args.host}:{args.port}/mcp/")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"API status: http://{args.host}:{args.port}/status")
    print("\nPress CTRL+C to stop the server\n")
    
    # Run uvicorn
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)

if __name__ == "__main__":
    main()