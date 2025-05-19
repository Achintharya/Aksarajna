import os
import sys
import json
import threading
import time
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_socketio import SocketIO
import subprocess

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import logger, config

# Initialize Flask app
app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist'))
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Log that the app has been initialized
print("Flask app initialized with Socket.IO")

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    print(f"Current process status: {process_status}")
    # Send the current status to the newly connected client
    socketio.emit('status_update', process_status, room=request.sid)
    print(f"Sent status_update event to client {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on_error()
def handle_error(e):
    print(f"Socket.IO error: {e}")

@socketio.on_error_default
def handle_error_default(e):
    print(f"Socket.IO default error handler: {e}")

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
    
    print(f"Updating status: step={step}, progress={progress}, log={log}, error={error}, completed={completed}")
    
    if step is not None:
        process_status["current_step"] = step
        print(f"Updated current_step to: {step}")
    
    if progress is not None:
        process_status["progress"] = progress
        print(f"Updated progress to: {progress}%")
    
    if log is not None:
        process_status["logs"].append(log)
        logger.info(log)
        print(f"Added log: {log}")
    
    if error is not None:
        process_status["error"] = error
        logger.error(error)
        print(f"Set error: {error}")
    
    process_status["completed"] = completed
    if completed:
        print("Process marked as completed")
    
    # Emit the updated status to all clients
    print("Emitting status_update event with data:", process_status)
    socketio.emit('status_update', process_status)
    print("status_update event emitted")

def run_process(query, urls, components, article_type='detailed', article_filename=''):
    """
    Run the selected components with the given query and/or URLs
    
    Args:
        query (str): The search query
        urls (str): Comma-separated list of URLs to extract from
        components (list): List of components to run ('extract', 'summarize', 'write')
        article_type (str): Type of article to generate (detailed, summarized, points)
        article_filename (str): File name for the article (without extension)
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
            if urls:
                cmd.extend(['--urls', urls])
        
        if 'summarize' in components:
            cmd.append('--summarize')
        
        if 'write' in components:
            cmd.append('--write')
            cmd.extend(['--article-type', article_type])
            if article_filename:
                cmd.extend(['--article-filename', article_filename])
        
        if len(components) > 1:
            cmd.append('--concurrent')
        
        update_status(step="Starting process", progress=5, 
                     log=f"Running command: {' '.join(cmd)}")
        
        # Set environment variables
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        
        # Create a process to run the command
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Set up progress tracking based on components
        total_steps = len(components)
        current_step = 0
        progress_per_step = 90 / total_steps  # 90% divided by number of steps (5% is initial, 5% is final)
        
        # Map components to step names
        component_names = {
            'extract': 'Web Context Extraction',
            'summarize': 'Context Summarization',
            'write': 'Article Writing'
        }
        
        # Track which components have started and completed
        started_components = set()
        completed_components = set()
        
        # Track the current component being processed
        current_component = None
        
        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            line_text = line.strip()
            # Print to console for debugging
            print(f"Process output: {line_text}", flush=True)
            update_status(log=line_text)
            
            # Force flush the output to ensure it's displayed immediately
            sys.stdout.flush()
            
            # Add more debug information
            if "Starting:" in line_text:
                print(f"DEBUG: Detected component start: {line_text}", flush=True)
            if "Successfully completed:" in line_text:
                print(f"DEBUG: Detected component completion: {line_text}", flush=True)
            if "%" in line_text:
                print(f"DEBUG: Detected progress update: {line_text}", flush=True)
            
            # Check for component start indicators
            if "Starting:" in line_text:
                for comp in components:
                    if comp in line_text.lower() and comp not in started_components:
                        started_components.add(comp)
                        current_component = comp
                        current_step += 1
                        step_name = component_names.get(comp, comp)
                        progress = 5 + (current_step - 1) * progress_per_step
                        update_status(step=f"Running {step_name}", progress=int(progress))
                        break
            
            # Check for component completion indicators
            if "Successfully completed:" in line_text:
                for comp in components:
                    if comp in line_text.lower() and comp not in completed_components:
                        completed_components.add(comp)
                        current_component = None  # Reset current component
                        progress = 5 + current_step * progress_per_step
                        update_status(step=f"Completed {component_names.get(comp, comp)}", progress=int(progress))
                        break
            
            # Update progress based on percentage indicators in output
            if "%" in line_text:
                try:
                    # Extract percentage from progress bar output
                    percent_parts = line_text.split('%')[0].split('|')
                    if len(percent_parts) > 1:
                        percent_str = percent_parts[-1].strip()
                        if percent_str.isdigit():
                            percent = int(percent_str)
                            # Map the component's progress to the overall progress
                            if current_step > 0 and current_step <= len(components):
                                # Calculate the progress for the current component
                                component_progress = 5 + (current_step - 1) * progress_per_step + (percent * progress_per_step / 100)
                                update_status(progress=int(component_progress))
                                # Debug log to see progress updates
                                logger.info(f"Progress update: {percent}% for component {current_component}, overall {int(component_progress)}%")
                except Exception as e:
                    logger.error(f"Error parsing progress: {e}")
        
        # Read any errors
        stderr_output = []
        for line in iter(process.stderr.readline, ''):
            if not line:
                break
            line_text = line.strip()
            stderr_output.append(line_text)
            update_status(error=line_text)
        
        # Wait for process to complete with a timeout
        try:
            process.wait(timeout=300)  # Wait up to 5 minutes for the process to complete
        except subprocess.TimeoutExpired:
            update_status(error="Process timed out after 5 minutes")
            process.kill()
            process.wait()
        
        # Check if process completed successfully
        if process.returncode != 0:
            # Check if there's a rate limit error but a basic summary was created
            stderr_text = '\n'.join(stderr_output)
            if "rate_limit" in stderr_text.lower() and "created basic summary" in stderr_text.lower():
                update_status(
                    step="Process completed with fallback",
                    progress=100,
                    log="Process completed with rate limit fallback",
                    completed=True
                )
            else:
                update_status(
                    error=f"Process exited with code {process.returncode}",
                    completed=True
                )
        else:
            # Add a small delay to ensure file operations are complete
            time.sleep(1)
            
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

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

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
    urls = data.get('urls', '')
    components = data.get('components', [])
    article_type = data.get('articleType', 'detailed')
    article_filename = data.get('articleFilename', '')
    
    if not components:
        return jsonify({"error": "No components selected"}), 400
    
    # Reset status
    reset_status()
    
    # Start the process in a separate thread
    thread = threading.Thread(target=run_process, args=(query, urls, components, article_type, article_filename))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Process started"})

@app.route('/api/logs')
def get_logs():
    """Get the logs as a text file"""
    logs = "\n".join(process_status["logs"])
    return Response(logs, mimetype='text/plain')

def main():
    """Main function to run the web UI"""
    port = int(os.environ.get('PORT', 5000))
    # Disable debug mode to prevent auto-reloading which can break Socket.IO connections
    # Set allow_unsafe_werkzeug=True to avoid warnings about the development server
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
