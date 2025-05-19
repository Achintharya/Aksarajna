import os
import subprocess
import sys
import time
import shutil

def main():
    """
    Build the React app and run the Flask server
    """
    print("Building React app...")
    
    # Get the absolute path to the frontend directory
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
    
    # Check if npm is available
    npm_path = shutil.which('npm')
    if not npm_path:
        print("Error: npm not found. Please make sure Node.js and npm are installed and in your PATH.")
        return 1
    
    print(f"Using npm from: {npm_path}")
    
    # Change to the frontend directory
    original_dir = os.getcwd()
    os.chdir(frontend_dir)
    
    try:
        # Check if node_modules exists
        if not os.path.exists('node_modules'):
            print("Node modules not found. Running npm install...")
            install_process = subprocess.run([npm_path, 'install'], capture_output=True, text=True)
            
            if install_process.returncode != 0:
                print("Error installing dependencies:")
                print(install_process.stderr)
                return 1
            
            print("Dependencies installed successfully!")
        
        # Run npm build
        print("Running npm build in:", os.getcwd())
        build_process = subprocess.run([npm_path, 'run', 'build'], capture_output=True, text=True)
        
        if build_process.returncode != 0:
            print("Error building React app:")
            print(build_process.stderr)
            return 1
        
        print("React app built successfully!")
    except Exception as e:
        print(f"Error during build process: {e}")
        return 1
    finally:
        # Change back to the original directory
        os.chdir(original_dir)
    
    # Run the Flask server
    print("Starting Flask server...")
    # Use subprocess.PIPE for both stdout and stderr to capture all output
    flask_process = subprocess.Popen(['python', 'src/web_ui_react.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    print("Flask server running at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Keep the script running until interrupted
        while True:
            # Print any output from the Flask server
            if flask_process.stdout:
                output = flask_process.stdout.readline()
                if output:
                    print(output.strip())
            
            # Print any errors from the Flask server
            if flask_process.stderr:
                error = flask_process.stderr.readline()
                if error:
                    print(error.strip(), file=sys.stderr)
            
            # Check if the Flask server has exited
            if flask_process.poll() is not None:
                print("Flask server exited with code", flask_process.returncode)
                break
            
            # Sleep briefly to avoid high CPU usage
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping Flask server...")
        flask_process.terminate()
        flask_process.wait()
        print("Flask server stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
