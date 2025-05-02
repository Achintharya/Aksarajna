// Connect to Socket.IO server
const socket = io();

// DOM elements
const processForm = document.getElementById('processForm');
const runBtn = document.getElementById('runBtn');
const progressCard = document.getElementById('progressCard');
const resultsCard = document.getElementById('resultsCard');
const currentStep = document.getElementById('currentStep');
const progressBar = document.querySelector('.progress-bar');
// Removed logs element
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');
const successAlert = document.getElementById('successAlert');
const newProcessBtn = document.getElementById('newProcessBtn');

// Form elements
const queryInput = document.getElementById('query');
const extractCheck = document.getElementById('extractCheck');
const summarizeCheck = document.getElementById('summarizeCheck');
const writeCheck = document.getElementById('writeCheck');
const articleTypeSelect = document.getElementById('articleType');
const articleTypeContainer = document.getElementById('articleTypeContainer');

const articleFilenameContainer = document.getElementById('articleFilenameContainer');

// Show/hide article type and filename based on write checkbox
writeCheck.addEventListener('change', function() {
    articleTypeContainer.style.display = this.checked ? 'block' : 'none';
    articleFilenameContainer.style.display = this.checked ? 'block' : 'none';
});

// Initialize article type and filename visibility
articleTypeContainer.style.display = writeCheck.checked ? 'block' : 'none';
articleFilenameContainer.style.display = writeCheck.checked ? 'block' : 'none';

// Initialize by fetching current status
fetch('/api/status')
    .then(response => response.json())
    .then(status => {
        if (status.running) {
            showProgressCard();
            updateUI(status);
        }
    })
    .catch(error => console.error('Error fetching status:', error));

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
    // Fetch current status when connected
    fetch('/api/status')
        .then(response => response.json())
        .then(status => {
            updateUI(status);
        })
        .catch(error => console.error('Error fetching status:', error));
});

socket.on('status_update', (status) => {
    console.log('Status update received:', status);
    updateUI(status);
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Reconnect logic
socket.on('reconnect', () => {
    console.log('Reconnected to server');
    // Fetch current status when reconnected
    fetch('/api/status')
        .then(response => response.json())
        .then(status => {
            updateUI(status);
        })
        .catch(error => console.error('Error fetching status:', error));
});

// Form submission
processForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    // Validate form
    const components = [];
    if (extractCheck.checked) components.push('extract');
    if (summarizeCheck.checked) components.push('summarize');
    if (writeCheck.checked) components.push('write');
    
    if (components.length === 0) {
        alert('Please select at least one component to run');
        return;
    }
    
    if (components.includes('extract') && !queryInput.value.trim()) {
        alert('Please enter a search query for web context extraction');
        queryInput.focus();
        return;
    }
    
    const articleFilenameInput = document.getElementById('articleFilename');
    
    // Prepare data
    const data = {
        query: queryInput.value.trim(),
        components: components,
        articleType: articleTypeSelect.value,
        articleFilename: articleFilenameInput.value.trim()
    };
    
    // Send request to start process
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
    
    fetch('/api/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to start process');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Process started:', data);
        showProgressCard();
    })
    .catch(error => {
        alert('Error: ' + error.message);
        runBtn.disabled = false;
        runBtn.textContent = 'Run Process';
    });
});

// New process button
newProcessBtn.addEventListener('click', () => {
    hideProgressCard();
    hideResultsCard();
    runBtn.disabled = false;
    runBtn.textContent = 'Run Process';
});

// Update UI based on status
function updateUI(status) {
    console.log('Updating UI with status:', status);
    
    // Update progress
    currentStep.textContent = status.current_step || '-';
    
    // Force a reflow to ensure the animation works
    const currentWidth = progressBar.style.width;
    progressBar.style.width = currentWidth;
    void progressBar.offsetWidth; // Force reflow
    
    // Update progress bar
    const progress = status.progress || 0;
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    progressBar.textContent = `${progress}%`;
    
    // Show error if any
    if (status.error) {
        errorMessage.textContent = status.error;
        errorAlert.style.display = 'block';
    } else {
        errorAlert.style.display = 'none';
    }
    
    // Show success message if completed
    if (status.completed) {
        if (!status.error) {
            successAlert.style.display = 'block';
            showResultsCard();
        }
        newProcessBtn.style.display = 'inline-block';
    } else {
        successAlert.style.display = 'none';
        newProcessBtn.style.display = 'none';
    }
    
    // Log the current status to console for debugging
    console.log(`Current step: ${status.current_step}, Progress: ${progress}%`);
}

// Show/hide cards
function showProgressCard() {
    progressCard.style.display = 'block';
    processForm.style.display = 'none';
}

function hideProgressCard() {
    progressCard.style.display = 'none';
    processForm.style.display = 'block';
    errorAlert.style.display = 'none';
    successAlert.style.display = 'none';
    // Logs reset removed
    currentStep.textContent = '-';
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);
    progressBar.textContent = '0%';
}

function showResultsCard() {
    resultsCard.style.display = 'block';
}

function hideResultsCard() {
    resultsCard.style.display = 'none';
}

// Form validation
extractCheck.addEventListener('change', validateForm);
queryInput.addEventListener('input', validateForm);

function validateForm() {
    if (extractCheck.checked && !queryInput.value.trim()) {
        runBtn.disabled = true;
    } else {
        runBtn.disabled = false;
    }
}
