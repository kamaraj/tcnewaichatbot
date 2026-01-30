/**
 * TCA AI Chatbot - Frontend Application
 * Handles file upload, chat functionality, and UI interactions
 */

// API Base URL
const API_BASE = '/api';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('fileInput');
const uploadZone = document.getElementById('uploadZone');
const uploadProgress = document.getElementById('uploadProgress');
const documentsList = document.getElementById('documentsList');
const docCount = document.getElementById('docCount');
const statusCard = document.getElementById('statusCard');
const statusIndicator = document.getElementById('statusIndicator');
const statusDetail = document.getElementById('statusDetail');
const toastContainer = document.getElementById('toastContainer');

// State
let isStreaming = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Check health status
    await checkHealth();

    // Load documents
    await loadDocuments();

    // Setup event listeners
    setupEventListeners();

    // Auto-resize textarea
    userInput.addEventListener('input', autoResizeTextarea);
}

// Event Listeners
function setupEventListeners() {
    // Chat form submission
    chatForm.addEventListener('submit', handleChatSubmit);

    // Keyboard shortcuts
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // File upload
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadZone.addEventListener('dragover', handleDragOver);
    uploadZone.addEventListener('dragleave', handleDragLeave);
    uploadZone.addEventListener('drop', handleDrop);
}

// Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        statusCard.className = 'status-card ' + (data.llm.status === 'healthy' ? 'healthy' : 'error');
        statusIndicator.querySelector('.status-text').textContent =
            data.llm.status === 'healthy' ? 'Connected' : 'Disconnected';
        statusDetail.textContent = `LLM: ${data.llm.model || 'Unknown'}`;

        if (data.llm.status !== 'healthy') {
            showToast('warning', 'LLM not available. Please ensure Ollama is running with TinyLlama.');
        }
    } catch (error) {
        statusCard.className = 'status-card error';
        statusIndicator.querySelector('.status-text').textContent = 'Error';
        statusDetail.textContent = 'Disconnected';
        console.error('Cannot connect to server');
    }
}

// Load Documents
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const documents = await response.json();

        renderDocuments(documents);
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function renderDocuments(documents) {
    docCount.textContent = documents.length;

    if (documents.length === 0) {
        documentsList.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <p>No documents uploaded yet</p>
            </div>
        `;
        return;
    }

    documentsList.innerHTML = documents.map(doc => `
        <div class="document-item" data-doc-id="${doc.doc_id}">
            <i class="bi bi-file-earmark-pdf document-icon"></i>
            <div class="document-info">
                <div class="document-name" title="${doc.filename}">${doc.filename}</div>
                <div class="document-meta">${doc.chunk_count} chunks indexed</div>
            </div>
            <button class="btn btn-link document-delete" onclick="deleteDocument('${doc.doc_id}')" title="Delete">
                <i class="bi bi-trash3"></i>
            </button>
        </div>
    `).join('');
}

// File Upload
function handleDragOver(e) {
    e.preventDefault();
    uploadZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
}

async function uploadFile(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('danger', 'Only PDF files are supported');
        return;
    }

    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        showToast('danger', 'File size exceeds 50MB limit');
        return;
    }

    // Show progress
    uploadZone.classList.add('d-none');
    uploadProgress.classList.remove('d-none');

    const progressBar = uploadProgress.querySelector('.progress-bar');
    const statusText = uploadProgress.querySelector('.upload-status');

    try {
        progressBar.style.width = '30%';
        statusText.textContent = 'Uploading file...';

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        progressBar.style.width = '70%';
        statusText.textContent = 'Processing document...';

        const result = await response.json();

        if (response.ok) {
            progressBar.style.width = '100%';
            statusText.textContent = 'Complete!';

            showToast('success', `Successfully indexed "${file.name}" (${result.chunks_indexed} chunks)`);

            // Reload documents
            await loadDocuments();

            // Add confirmation message to chat
            addMessage('assistant', `📄 Document "${file.name}" has been indexed with ${result.chunks_indexed} chunks. You can now ask questions about it!`);
        } else {
            throw new Error(result.detail || 'Upload failed');
        }
    } catch (error) {
        showToast('danger', `Upload failed: ${error.message}`);
    } finally {
        // Reset upload zone
        setTimeout(() => {
            uploadZone.classList.remove('d-none');
            uploadProgress.classList.add('d-none');
            progressBar.style.width = '0%';
            fileInput.value = '';
        }, 1000);
    }
}

async function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('success', 'Document deleted successfully');
            await loadDocuments();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Delete failed');
        }
    } catch (error) {
        showToast('danger', `Delete failed: ${error.message}`);
    }
}

// Chat Functionality
async function handleChatSubmit(e) {
    e.preventDefault();

    const question = userInput.value.trim();
    if (!question || isStreaming) return;

    // Add user message
    addMessage('user', question);

    // Clear input
    userInput.value = '';
    autoResizeTextarea();

    // Disable input
    isStreaming = true;
    sendBtn.disabled = true;
    userInput.disabled = true;

    // Add typing indicator
    const typingId = addTypingIndicator();

    try {
        // Use streaming for better UX
        await streamChat(question, typingId);
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage('assistant', `❌ Error: ${error.message}. Please check if the LLM is running.`);
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    }
}

async function streamChat(question, typingId) {
    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            question: question,
            stream: true
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Chat request failed');
    }

    // Remove typing indicator and create message element
    removeTypingIndicator(typingId);
    const messageElement = createStreamingMessage();

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let content = '';
    let sources = [];

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.type === 'content') {
                        content += data.content;
                        updateStreamingMessage(messageElement, content);
                    } else if (data.type === 'sources') {
                        sources = data.sources;
                    } else if (data.type === 'done') {
                        // Add sources to message
                        if (sources.length > 0) {
                            addSourcesToMessage(messageElement, sources);
                        }
                    }
                } catch (e) {
                    // Ignore parse errors
                }
            }
        }
    }

    // Fallback if no content received
    if (!content) {
        updateStreamingMessage(messageElement, 'Sorry, I could not generate a response. Please try again.');
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    const icon = role === 'user' ? 'bi-person-fill' : 'bi-robot';

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="bi ${icon}"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                ${role === 'assistant' ? marked.parse(content) : escapeHtml(content)}
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function createStreamingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="bi bi-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <span class="streaming-content"></span>
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

function updateStreamingMessage(element, content) {
    const bubble = element.querySelector('.message-bubble');
    bubble.innerHTML = marked.parse(content);
    scrollToBottom();
}

function addSourcesToMessage(element, sources) {
    const bubble = element.querySelector('.message-bubble');

    const sourcesHtml = `
        <div class="message-sources">
            <div class="sources-title">
                <i class="bi bi-bookmark-fill"></i> Sources
            </div>
            ${sources.map(s => `
                <div class="source-item">
                    <i class="bi bi-file-earmark-text"></i>
                    <span class="filename">${s.filename}</span>
                    <span class="page">Page ${s.page}</span>
                    <span class="score">${(s.relevance_score * 100).toFixed(0)}% match</span>
                </div>
            `).join('')}
        </div>
    `;

    bubble.insertAdjacentHTML('beforeend', sourcesHtml);
    scrollToBottom();
}

function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.id = id;
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="bi bi-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return id;
}

function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// UI Helpers
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function autoResizeTextarea() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function clearChat() {
    // Keep only the welcome message
    const welcomeMessage = chatMessages.querySelector('.message');
    chatMessages.innerHTML = '';
    if (welcomeMessage) {
        chatMessages.appendChild(welcomeMessage);
    }
}

// Toast Notifications
function showToast(type, message) {
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'danger' ? 'bg-danger' : 'bg-warning';
    const icon = type === 'success' ? 'check-circle' : type === 'danger' ? 'x-circle' : 'exclamation-triangle';

    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert">
            <div class="toast-header bg-transparent text-white border-0">
                <i class="bi bi-${icon}-fill me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();

    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Refresh health status periodically
setInterval(checkHealth, 30000);
