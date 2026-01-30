/**
 * TCA AI Chatbot - User Assistant Frontend
 * Handles chat functionality without sidebar/upload controls
 */

// API Base URL
const API_BASE = '/api';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const toastContainer = document.getElementById('toastContainer');

// State
let isStreaming = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Check health status implicitly via chat or initial ping if needed
    // But since there's no status indicator, we might just skip visual health check or log it
    await checkHealth();

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

    // Sample Question clicks (Event Delegation)
    chatMessages.addEventListener('click', (e) => {
        if (e.target.classList.contains('sample-question')) {
            const question = e.target.getAttribute('data-question');
            if (question) {
                userInput.value = question;
                autoResizeTextarea();
                userInput.focus();
                // chatForm.dispatchEvent(new Event('submit')); // Removed auto-submit
            }
        }
    });
}

// Health Check (Logging only since no UI)
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        if (data.llm.status !== 'healthy') {
            showToast('warning', 'LLM not available. Please ensure Ollama is running with TinyLlama.');
        }
    } catch (error) {
        console.error('Cannot connect to server');
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
                        // Sources are hidden per user request
                        /*
                        if (sources.length > 0) {
                            addSourcesToMessage(messageElement, sources);
                        }
                        */
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
