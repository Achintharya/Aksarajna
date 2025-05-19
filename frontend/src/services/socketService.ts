import { io, Socket } from 'socket.io-client';

// Define the status interface
export interface ProcessStatus {
  running: boolean;
  current_step: string;
  progress: number;
  logs: string[];
  error: string | null;
  completed: boolean;
}

class SocketService {
  private socket: Socket | null = null;
  private statusUpdateCallbacks: ((status: ProcessStatus) => void)[] = [];

  // Initialize the socket connection
  connect(): void {
    if (this.socket) return;

    // Connect to the server
    this.socket = io();

    // Set up event listeners
    this.socket.on('connect', () => {
      console.log('Connected to server');
    });

    this.socket.on('status_update', (status: ProcessStatus) => {
      console.log('Status update received:', status);
      this.notifyStatusUpdate(status);
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from server');
    });

    this.socket.on('reconnect', () => {
      console.log('Reconnected to server');
      this.fetchStatus();
    });
  }

  // Disconnect the socket
  disconnect(): void {
    if (!this.socket) return;
    this.socket.disconnect();
    this.socket = null;
  }

  // Register a callback for status updates
  onStatusUpdate(callback: (status: ProcessStatus) => void): () => void {
    this.statusUpdateCallbacks.push(callback);
    
    // Return a function to unregister the callback
    return () => {
      this.statusUpdateCallbacks = this.statusUpdateCallbacks.filter(cb => cb !== callback);
    };
  }

  // Notify all registered callbacks of a status update
  private notifyStatusUpdate(status: ProcessStatus): void {
    this.statusUpdateCallbacks.forEach(callback => callback(status));
  }

  // Fetch the current status from the server
  async fetchStatus(): Promise<ProcessStatus> {
    try {
      const response = await fetch('/api/status');
      const status = await response.json();
      this.notifyStatusUpdate(status);
      return status;
    } catch (error) {
      console.error('Error fetching status:', error);
      throw error;
    }
  }

  // Start a new process
  async startProcess(data: {
    query: string;
    urls: string;
    components: string[];
    articleType: string;
    articleFilename: string;
  }): Promise<void> {
    try {
      const response = await fetch('/api/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start process');
      }

      return await response.json();
    } catch (error) {
      console.error('Error starting process:', error);
      throw error;
    }
  }
}

// Create a singleton instance
export const socketService = new SocketService();
