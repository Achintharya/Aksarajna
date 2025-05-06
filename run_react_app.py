import os
import subprocess
import sys
import time

def main():
    """
    Build the React app and run the Flask server
    """
    print("Building React app...")
    
    # Change to the frontend directory
    os.chdir('frontend')
    
    # Run npm build
    build_process = subprocess.run(['npm', 'run', 'build'], capture_output=True, text=True)
    
    if build_process.returncode != 0:
        print("Error building React app:")
        print(build_process.stderr)
        return 1
    
    print("React app built successfully!")
    
    # Change back to the root directory
    os.chdir('..')
    
    # Run the Flask server
    print("Starting Flask server...")
    flask_process = subprocess.Popen(['python', 'src/web_ui_react.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    print("Flask server running at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Keep the script running until interrupted
        while True:
            # Print any output from the Flask server
            output = flask_process.stdout.readline()
            if output:
                print(output.strip())
            
            # Print any errors from the Flask server
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
