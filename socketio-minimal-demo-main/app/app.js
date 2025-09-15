
console.log('Frontend JavaScript loading...');

const socket = new WebSocket('ws://localhost:8081/ws');
let myId = null;
let currentClientId = null;
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const resultsList = document.getElementById('resultsList');

console.log('Initializing WebSocket connection to ws://localhost:8081/ws');
console.log('DOM elements loaded:', {
    fileInput: !!fileInput,
    uploadBtn: !!uploadBtn, 
    resultsList: !!resultsList
});

socket.onmessage = ({ data }) => {
    console.log('WebSocket message received:', data);
    addLog('WEBSOCKET', `Received: ${data}`);
    
    if (data.startsWith('Your ID: ')) {
        myId = data.split(': ')[1];
        console.log('Connected with WebSocket ID:', myId);
        addLog('CONNECTION', `WebSocket connected with ID: ${myId}`);
        return;
    }
    
    if (data.startsWith('DETECTION:')) {
        console.log('Processing DETECTION message');
        addLog('DETECTION', 'Processing detection message');
        const parts = data.split(':');
        if (parts.length >= 5) {
            const clientId = parts[1];
            const status = parts[2];
            const confidence = parseFloat(parts[3]);
            const message = parts.slice(4).join(':');
            
            console.log('Detection data:', { clientId, status, confidence, message, currentClientId });
            addLog('DETECTION', `Client: ${clientId}, Status: ${status}, Message: ${message}`);
            
            updateDetectionUI(clientId, status, confidence, message);
            addDetectionResult(clientId, status, confidence, message);
        }
        return;
    }
    
    if (data.startsWith('PAGE_COUNT:')) {
        console.log('Processing PAGE_COUNT message');
        addLog('PAGE_COUNT', 'Processing page count message');
        const parts = data.split(':');
        if (parts.length >= 3) {
            const clientId = parts[1];
            const pages = parseInt(parts[2]);
            
            console.log('Page count data:', { clientId, pages, currentClientId });
            addLog('PAGE_COUNT', `Client: ${clientId}, Pages: ${pages}`);
        }
        return;
    }
    
    if (data.startsWith('PAGE_RESULT:')) {
        console.log('Processing PAGE_RESULT message');
        addLog('PAGE_RESULT', 'Processing page result message');
        const parts = data.split(':');
        if (parts.length >= 7) {
            const clientId = parts[1];
            const pageNum = parseInt(parts[2]);
            const orientation = parts[3];
            const aspectRatio = parseFloat(parts[4]);
            const width = parseInt(parts[5]);
            const height = parseInt(parts[6]);
            
            console.log('Page result data:', { clientId, pageNum, orientation, aspectRatio, width, height });
            addLog('PAGE_RESULT', `Page ${pageNum}: ${orientation} (${width}x${height})`);
        }
        return;
    }
    
    console.log('Unknown message type:', data);
    addLog('UNKNOWN', `Unknown message: ${data}`);
    const el = document.createElement('li');
    el.innerHTML = data;
    resultsList.appendChild(el);
};

socket.onopen = () => {
    console.log('WebSocket connection opened');
    addLog('CONNECTION', 'WebSocket connection opened');
};

socket.onerror = (error) => {
    console.error('WebSocket error:', error);
    addLog('ERROR', `WebSocket error: ${error.message || 'Unknown error'}`);
};

socket.onclose = (event) => {
    console.log(' WebSocket connection closed:', event.code, event.reason);
    addLog('CONNECTION', `WebSocket closed (${event.code}): ${event.reason || 'No reason given'}`);
};

// Logging function
function addLog(type, message) {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${type}: ${message}`;
    console.log(` ${logMessage}`);
}

function generateClientId() {
    return 'client_' + Math.random().toString(36).substr(2, 8);
}

uploadBtn.onclick = async () => {
    console.log('Upload button clicked');
    addLog('UI', 'Upload button clicked');
    
    const file = fileInput.files[0];
    if (!file) {
        console.log('No file selected');
        addLog('UI', 'No file selected - showing alert');
        alert('Please select a file first');
        return;
    }
    
    const clientId = generateClientId();
    console.log('Generated client ID:', clientId);
    addLog('CLIENT', `Generated client ID: ${clientId}`);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', clientId);
    
    console.log('Starting file upload:', file.name, file.size, 'bytes');
    addLog('UPLOAD', `Starting upload: ${file.name} (${file.size} bytes)`);
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        addLog('UI', 'Upload button disabled, text changed to "Uploading..."');
        
        const response = await fetch('http://localhost:8080/api/upload-document', {
            method: 'POST',
            body: formData
        });
        
        console.log(' Upload response status:', response.status);
        addLog('UPLOAD', `Upload response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        const result = await response.json();
        console.log('Upload result:', result);
        addLog('UPLOAD', `Upload result: ${JSON.stringify(result)}`);
        
        if (result.error) {
            console.log(' Upload error:', result.error);
            addLog('ERROR', `Upload error: ${result.error}`);
            alert(`Error: ${result.error}\nSupported types: ${result.supported_types.join(', ')}`);
            uploadBtn.textContent = 'Upload & Analyze';
            uploadBtn.disabled = false;  
            return;
        }
        
        currentClientId = clientId;
        console.log(' Set current client ID:', currentClientId);
        addLog('CLIENT', `Set current client ID: ${currentClientId}`);
        
        resultsList.innerHTML = '';
        addLog('UI', 'Cleared results list');
        
        uploadBtn.textContent = 'Upload & Analyze';
        uploadBtn.disabled = false;
        addLog('UI', 'Upload button re-enabled');
        
        console.log(' Upload completed successfully, waiting for WebSocket messages...');
        addLog('UPLOAD', 'Upload completed successfully, awaiting processing messages');
        
    } catch (error) {
        console.error('Upload error:', error);
        addLog('ERROR', `Upload failed: ${error.message}`);
        alert('Error uploading file: ' + error.message);
        uploadBtn.textContent = 'Upload & Analyze';
        uploadBtn.disabled = false;
    }
};

function updateDetectionUI(clientId, status, confidence, message) {
    console.log(' updateDetectionUI called:', { clientId, currentClientId, status, message });
    addLog('UI_FUNCTION', `updateDetectionUI: ${clientId} vs ${currentClientId}`);
    
    if (clientId !== currentClientId) {
        console.log('Client ID mismatch - skipping updateDetectionUI');
        addLog('UI_FUNCTION', 'Client ID mismatch - skipping updateDetectionUI');
        return;
    }
    
    console.log('Client ID matches - processing updateDetectionUI');
    addLog('UI_FUNCTION', 'Client ID matches - processing updateDetectionUI');
}

function addDetectionResult(clientId, status, confidence, message) {
    console.log(' addDetectionResult called:', { clientId, status, confidence, message });
    addLog('UI_FUNCTION', `addDetectionResult: ${message}`);
    
    // Show clean detection messages in the UI
    const li = document.createElement('li');
    li.className = 'result-item';
    li.innerHTML = message;  // Just show the message without extra formatting
    resultsList.appendChild(li);
    li.scrollIntoView({ behavior: 'smooth' });
    
    console.log(' Detection result added to UI:', message);
    addLog('UI_UPDATE', `Detection result displayed: ${message}`);
}


