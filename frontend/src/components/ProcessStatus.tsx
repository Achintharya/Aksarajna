import { useEffect, useRef } from 'react';
import type { ProcessStatus as ProcessStatusType } from '../services/socketService';

interface ProcessStatusProps {
  status: ProcessStatusType;
  onNewProcess: () => void;
}

const ProcessStatus: React.FC<ProcessStatusProps> = ({ status, onNewProcess }) => {
  const progressBarRef = useRef<HTMLDivElement>(null);

  // Force a reflow to ensure the animation works when the progress changes
  useEffect(() => {
    if (progressBarRef.current) {
      const currentWidth = progressBarRef.current.style.width;
      progressBarRef.current.style.width = currentWidth;
      void progressBarRef.current.offsetWidth; // Force reflow
      progressBarRef.current.style.width = `${status.progress}%`;
    }
  }, [status.progress]);

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
          <div className="progress">
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
