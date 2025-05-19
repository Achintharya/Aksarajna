import { useState, useEffect } from 'react';
import './App.css';
import ProcessForm from './components/ProcessForm';
import ProcessStatus from './components/ProcessStatus';
import ResultsCard from './components/ResultsCard';
import { socketService } from './services/socketService';
import type { ProcessStatus as ProcessStatusType } from './services/socketService';

function App() {
  const [showForm, setShowForm] = useState(true);
  const [showResults, setShowResults] = useState(false);
  const [status, setStatus] = useState<ProcessStatusType>({
    running: false,
    current_step: '',
    progress: 0,
    logs: [],
    error: null,
    completed: false
  });

  // Initialize socket connection and fetch status
  useEffect(() => {
    socketService.connect();
    
    // Register for status updates
    const unsubscribe = socketService.onStatusUpdate((newStatus) => {
      setStatus(newStatus);
      
      // Show results when process completes successfully
      if (newStatus.completed && !newStatus.error) {
        setShowResults(true);
      }
    });
    
    // Fetch initial status
    socketService.fetchStatus().catch(console.error);
    
    // Cleanup on unmount
    return () => {
      unsubscribe();
      socketService.disconnect();
    };
  }, []);

  // Handle process start
  const handleProcessStart = () => {
    setShowForm(false);
    setShowResults(false);
  };

  // Handle new process button click
  const handleNewProcess = () => {
    setShowForm(true);
  };

  return (
    <div className="container mt-4">
      <h1 className="mb-4">Vārnika</h1>
      
      {showForm ? (
        <ProcessForm onProcessStart={handleProcessStart} />
      ) : (
        <ProcessStatus status={status} onNewProcess={handleNewProcess} />
      )}
      
      {showResults && <ResultsCard />}
    </div>
  );
}

export default App;
