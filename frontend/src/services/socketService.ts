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

    // Connect to the server with explicit URL and options
    console.log('Connecting to Socket.IO server at:', window.location.origin);
    this.socket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 20000,
      forceNew: true
    });
    console.log('Socket.IO instance created:', this.socket);

    // Set up event listeners
    this.socket.on('connect', () => {
      console.log('Connected to server with ID:', this.socket?.id);
    });

    this.socket.on('status_update', (status: ProcessStatus) => {
      console.log('Status update received:', status);
      this.notifyStatusUpdate(status);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected from server. Reason:', reason);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('Reconnected to server after', attemptNumber, 'attempts');
      this.fetchStatus();
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log('Attempting to reconnect:', attemptNumber);
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('Reconnection error:', error);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('Failed to reconnect to server');
    });

    this.socket.on('error', (error) => {
      console.error('Socket.IO error:', error);
    });

    this.socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
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
