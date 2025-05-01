import os
import sys
import json
import threading
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import subprocess

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import logger, config

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static'))
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables to track process status
process_status = {
    "running": False,
    "current_step": "",
    "progress": 0,
    "logs": [],
    "error": None,
    "completed": False
}

def reset_status():
    """Reset the process status"""
    global process_status
    process_status = {
        "running": False,
        "current_step": "",
        "progress": 0,
        "logs": [],
        "error": None,
        "completed": False
    }

def update_status(step=None, progress=None, log=None, error=None, completed=False):
    """Update the process status and emit to clients"""
    global process_status
    
    if step is not None:
        process_status["current_step"] = step
    
    if progress is not None:
        process_status["progress"] = progress
    
    if log is not None:
        process_status["logs"].append(log)
        logger.info(log)
    
    if error is not None:
        process_status["error"] = error
        logger.error(error)
    
    process_status["completed"] = completed
    
    # Emit the updated status to all clients
    socketio.emit('status_update', process_status)

def run_process(query, components):
    """
    Run the selected components with the given query
    
    Args:
        query (str): The search query
        components (list): List of components to run ('extract', 'summarize', 'write')
    """
    global process_status
    process_status["running"] = True
    
    try:
        # Build the command
        cmd = ['python', 'src/main.py']
        
        if 'extract' in components:
            cmd.append('--extract')
            if query:
                cmd.extend(['--query', query])
        
        if 'summarize' in components:
            cmd.append('--summarize')
        
        if 'write' in components:
            cmd.append('--write')
        
        if len(components) > 1:
            cmd.append('--concurrent')
        
        update_status(step="Starting process", progress=5, 
                     log=f"Running command: {' '.join(cmd)}")
        
        # Create a process to run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Track progress based on output
        progress_markers = {
            "Starting web context extraction": 10,
            "Searching DuckDuckGo": 15,
            "Searching Google": 20,
            "Found results": 25,
            "Starting web crawling": 30,
            "Processing crawl results": 50,
            "Starting context summarization": 60,
            "Summarizing context data": 70,
            "Context summarization completed": 80,
            "Generating article": 85,
            "Article saved": 95,
            "All tasks completed": 100
        }
        
        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            update_status(log=line.strip())
            
            # Update progress based on markers
            for marker, prog in progress_markers.items():
                if marker in line:
                    update_status(progress=prog)
                    if marker == "All tasks completed":
                        update_status(completed=True)
                    break
        
        # Read any errors
        for line in iter(process.stderr.readline, ''):
            if not line:
                break
            update_status(error=line.strip())
        
        # Wait for process to complete
        process.wait()
        
        # Check if process completed successfully
        if process.returncode != 0:
            update_status(
                error=f"Process exited with code {process.returncode}",
                completed=True
            )
        else:
            update_status(
                step="Process completed",
                progress=100,
                log="All tasks completed successfully",
                completed=True
            )
    
    except Exception as e:
        update_status(
            error=f"Error running process: {str(e)}",
            completed=True
        )
    
    finally:
        process_status["running"] = False
        socketio.emit('status_update', process_status)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get the current process status"""
    return jsonify(process_status)

@app.route('/api/run', methods=['POST'])
def run():
    """Start the process with the given parameters"""
    if process_status["running"]:
        return jsonify({"error": "A process is already running"}), 400
    
    # Get parameters from request
    data = request.json
    query = data.get('query', '')
    components = data.get('components', [])
    
    if not components:
        return jsonify({"error": "No components selected"}), 400
    
    # Reset status
    reset_status()
    
    # Start the process in a separate thread
    thread = threading.Thread(target=run_process, args=(query, components))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Process started"})

@app.route('/api/logs')
def get_logs():
    """Get the logs as a text file"""
    logs = "\n".join(process_status["logs"])
    return Response(logs, mimetype='text/plain')

def create_directories():
    """Create necessary directories if they don't exist"""
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

def main():
    """Main function to run the web UI"""
    create_directories()
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':
    main()
