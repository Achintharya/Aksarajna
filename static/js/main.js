// Connect to Socket.IO server
const socket = io();

// DOM elements
const processForm = document.getElementById('processForm');
const runBtn = document.getElementById('runBtn');
const progressCard = document.getElementById('progressCard');
const resultsCard = document.getElementById('resultsCard');
const currentStep = document.getElementById('currentStep');
const progressBar = document.querySelector('.progress-bar');
const logsElement = document.getElementById('logs');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');
const successAlert = document.getElementById('successAlert');
const newProcessBtn = document.getElementById('newProcessBtn');

// Form elements
const queryInput = document.getElementById('query');
const extractCheck = document.getElementById('extractCheck');
const summarizeCheck = document.getElementById('summarizeCheck');
const writeCheck = document.getElementById('writeCheck');

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
});

socket.on('status_update', (status) => {
    updateUI(status);
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
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
    
    // Prepare data
    const data = {
        query: queryInput.value.trim(),
        components: components
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
    // Update progress
    currentStep.textContent = status.current_step || '-';
    progressBar.style.width = `${status.progress}%`;
    progressBar.setAttribute('aria-valuenow', status.progress);
    progressBar.textContent = `${status.progress}%`;
    
    // Update logs
    if (status.logs && status.logs.length > 0) {
        logsElement.textContent = status.logs.join('\n');
        logsElement.scrollTop = logsElement.scrollHeight;
    }
    
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
    logsElement.textContent = '';
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
