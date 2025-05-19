import { useEffect, useRef } from 'react';
import type { ProcessStatus as ProcessStatusType } from '../services/socketService';

interface ProcessStatusProps {
  status: ProcessStatusType;
  onNewProcess: () => void;
}

const ProcessStatus: React.FC<ProcessStatusProps> = ({ status, onNewProcess }) => {
  const progressBarRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Force a reflow to ensure the animation works when the progress changes
  useEffect(() => {
    console.log('Progress changed:', status.progress);
    if (progressBarRef.current) {
      const currentWidth = progressBarRef.current.style.width;
      progressBarRef.current.style.width = currentWidth;
      void progressBarRef.current.offsetWidth; // Force reflow
      progressBarRef.current.style.width = `${status.progress}%`;
      console.log('Progress bar width updated to:', `${status.progress}%`);
    }
  }, [status.progress]);

  // Auto-scroll logs to bottom when new logs are added
  useEffect(() => {
    console.log('Logs updated, count:', status.logs.length);
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
      console.log('Scrolled logs container to bottom');
    }
  }, [status.logs]);

  // Log status changes
  useEffect(() => {
    console.log('ProcessStatus component received new status:', status);
  }, [status]);

  return (
    <div className="card mb-4">
      <div className="card-header">
        <h2 className="card-title h5 mb-0">Process Status</h2>
      </div>
      <div className="card-body">
        <div className="mb-3">
          <label className="form-label">
            Current Step: <span>{status.current_step || '-'}</span>
          </label>
          <div className="progress mb-3">
            <div
              ref={progressBarRef}
              className="progress-bar"
              role="progressbar"
              style={{ width: `${status.progress}%` }}
              aria-valuenow={status.progress}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              {status.progress}%
            </div>
          </div>
          
          {/* Display logs */}
          <div className="mt-3">
            <h6>Process Logs:</h6>
            <div 
              ref={logsContainerRef}
              className="border p-2 bg-light" 
              style={{ 
                height: '200px', 
                overflowY: 'auto', 
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
            >
              {status.logs.length > 0 ? 
                status.logs.map((log, index) => (
                  <div key={index}>{log}</div>
                )) : 
                <div className="text-muted">No logs yet...</div>
              }
            </div>
          </div>
        </div>

        {status.error && (
          <div className="alert alert-danger">
            <strong>Error:</strong> {status.error}
          </div>
        )}

        {status.completed && !status.error && (
          <div className="alert alert-success">
            <strong>Success!</strong> Process completed successfully.
          </div>
        )}

        {status.completed && (
          <div className="mt-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={onNewProcess}
            >
              Start New Process
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcessStatus;
