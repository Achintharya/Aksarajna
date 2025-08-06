#!/usr/bin/env python3
"""
Run script for the Varnika application.
Provides commands to run the application in different modes.
"""

import argparse
import os
import subprocess
import sys

def run_dev():
    """Run the application in development mode."""
    print("Starting Varnika in development mode...")
    os.environ['VARNIKA_ENV'] = 'development'
    
    # Start the Flask app
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    subprocess.run([sys.executable, 'src/app.py'], env=env)

def run_prod():
    """Run the application in production mode."""
    print("Starting Varnika in production mode...")
    os.environ['VARNIKA_ENV'] = 'production'
    subprocess.run([sys.executable, 'src/app.py'])

def run_test():
    """Run the application tests."""
    print("Running Varnika tests...")
    os.environ['VARNIKA_ENV'] = 'testing'
    # Add test command here when tests are implemented
    print("Tests not implemented yet.")

def main():
    """Main function to parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description='Run the Varnika application.')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Development mode
    dev_parser = subparsers.add_parser('dev', help='Run in development mode')
    
    # Production mode
    prod_parser = subparsers.add_parser('prod', help='Run in production mode')
    
    # Test mode
    test_parser = subparsers.add_parser('test', help='Run tests')
    
    args = parser.parse_args()
    
    if args.command == 'dev':
        run_dev()
    elif args.command == 'prod':
        run_prod()
    elif args.command == 'test':
        run_test()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
