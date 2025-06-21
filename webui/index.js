// Main Application Module
// New modular index.js - imports and coordinates all modules

// Core modules
import { 
    generateGUID, 
    sendJsonData, 
    downloadFile, 
    readJsonFiles,
    adjustTextareaHeight
} from './js/core-utils.js';

import { 
    toast, 
    toastFetchError, 
    toastSuccess, 
    toastWarning, 
    toastError 
} from './js/toast-system.js';

import { 
    toggleSidebar, 
    setupSidebarToggle, 
    scrollChanged, 
    updateAfterScroll 
} from './js/ui-layout.js';

import { 
    initializeChatCore,
    sendMessage, 
    updateChatInput, 
    setContext, 
    getContext, 
    selectChat,
    switchFromContext,
    pauseAgent, 
    resetChat, 
    newChat, 
    killChat,
    getConnectionStatus,
    setConnectionStatus
} from './js/chat-core.js';

import { 
    handleFiles, 
    loadKnowledge, 
    uploadWorkDirFiles, 
    downloadWorkDirFile, 
    deleteWorkDirFile,
    formatFileSize
} from './js/file-management.js';

import { 
    updateUserTime, 
    startTimeUpdates, 
    formatTimestamp, 
    getRelativeTime 
} from './js/time-utils.js';

import { 
    startPolling, 
    stopPolling, 
    isPollingActive 
} from './js/polling-system.js';

import { 
    openTaskDetail, 
    setupTabs, 
    activateTab, 
    initializeActiveTab,
    filterTasks,
    sortTasks,
    getTaskStatusColor,
    getTaskStatusIcon
} from './js/task-management.js';

// Import speech module to ensure it's loaded and window.speech is available
import { speech } from './js/speech.js';

// Import messages module to ensure message handlers are available
import './js/messages.js';

// Global DOM elements
let chatInput, sendButton, chatHistory, inputSection, chatsSection, progressBar;
let context = null;
let autoScroll = true;

// Initialize all DOM references
function initializeDOM() {
    chatInput = document.getElementById('chat-input');
    sendButton = document.getElementById('send-button');
    chatHistory = document.getElementById('chat-history');
    inputSection = document.getElementById('input-section');
    chatsSection = document.getElementById('chats-section');
    progressBar = document.getElementById('progress-bar');
}

// File upload handler
window.handleFileUpload = function(event) {
    const files = event.target.files;
    const inputAD = Alpine.$data(inputSection);
    handleFiles(files, inputAD);
};

// Blank state HTML component
function createBlankState() {
    const blankStateHTML = `
        <div id="blank-state" class="flex flex-col items-center justify-center h-full text-center p-8" style="display: flex;">
            <div class="mb-6">
                <div class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.959 8.959 0 01-4.906-1.471L3 21l2.471-5.094A8.959 8.959 0 013 12c0-4.418 3.582-8 8-8s8 3.582 8 8z"></path>
                    </svg>
                </div>
            </div>
            <h2 class="text-2xl font-semibold text-gray-800 dark:text-gray-200 mb-2">Ready when you are</h2>
            <p class="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
                Start a conversation by typing a message below, or select an existing chat from the sidebar.
            </p>
            <div class="flex flex-wrap gap-2 justify-center">
                <button onclick="updateChatInput('Help me write some code')" class="px-4 py-2 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:hover:bg-blue-800 text-blue-800 dark:text-blue-200 rounded-lg text-sm transition-colors">
                    Help me write code
                </button>
                <button onclick="updateChatInput('Explain this concept')" class="px-4 py-2 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:hover:bg-green-800 text-green-800 dark:text-green-200 rounded-lg text-sm transition-colors">
                    Explain a concept
                </button>
                <button onclick="updateChatInput('Debug this error')" class="px-4 py-2 bg-purple-100 hover:bg-purple-200 dark:bg-purple-900 dark:hover:bg-purple-800 text-purple-800 dark:text-purple-200 rounded-lg text-sm transition-colors">
                    Debug an error
                </button>
            </div>
        </div>
    `;
    
    // Insert blank state into chat history
    if (chatHistory && !document.getElementById('blank-state')) {
        chatHistory.innerHTML = blankStateHTML;
    }
}

// Application initialization
async function initializeApp() {
    console.log('🚀 Initializing Maho Chat Application...');
    
    try {
        // Initialize dark mode first (before DOM manipulation)
        initializeDarkMode();
        
        // Initialize DOM references
        initializeDOM();
        
        // Initialize core modules
        initializeChatCore();
        
        // Setup UI components
    setupSidebarToggle();
    setupTabs();
    
        // Create blank state
        createBlankState();
        
        // Start time updates
        startTimeUpdates();
        
        // Initialize tabs after Alpine.js is ready
    if (window.Alpine) {
        initializeActiveTab();
    } else {
        document.addEventListener('alpine:init', () => {
            initializeActiveTab();
        });
    }
        
        // Start polling for updates
        await startPolling();
        
        console.log('✅ Application initialized successfully');
        
    } catch (error) {
        console.error('❌ Error initializing application:', error);
        toastError('Failed to initialize application');
    }
}

// Setup event handlers once the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    stopPolling();
});

// Dark mode toggle function
function toggleDarkMode(isDark) {
    const body = document.body;
    if (isDark) {
        body.classList.remove('light-mode');
        localStorage.setItem('darkMode', 'true');
    } else {
        body.classList.add('light-mode');
        localStorage.setItem('darkMode', 'false');
    }
}

// Initialize dark mode on page load
function initializeDarkMode() {
    const savedDarkMode = localStorage.getItem('darkMode');
    const body = document.body;
    
    // Default to dark mode if no preference saved
    if (savedDarkMode === 'false') {
        body.classList.add('light-mode');
    } else {
        body.classList.remove('light-mode');
    }
}

// Toggle functions for preferences
function toggleAutoScroll(enabled) {
    window.autoScroll = enabled;
    localStorage.setItem('autoScroll', enabled.toString());
}

function toggleThoughts(enabled) {
    const thoughts = document.querySelectorAll('.msg-thoughts');
    thoughts.forEach(thought => {
        thought.style.display = enabled ? 'block' : 'none';
    });
    localStorage.setItem('showThoughts', enabled.toString());
}

function toggleJson(enabled) {
    const jsonElements = document.querySelectorAll('.msg-json');
    jsonElements.forEach(json => {
        json.style.display = enabled ? 'block' : 'none';
    });
    localStorage.setItem('showJson', enabled.toString());
}

function toggleUtils(enabled) {
    const utilElements = document.querySelectorAll('.message-util');
    utilElements.forEach(util => {
        util.style.display = enabled ? 'block' : 'none';
    });
    localStorage.setItem('showUtils', enabled.toString());
}

function toggleSpeech(enabled) {
    localStorage.setItem('speech', enabled.toString());
    // Speech functionality is handled by the speech module
    if (window.speech) {
        window.speech.enabled = enabled;
    }
}

// Safe call helper function
function safeCall(functionName, ...args) {
    try {
        if (typeof window[functionName] === 'function') {
            return window[functionName](...args);
        } else {
            console.warn(`Function ${functionName} not found`);
        }
    } catch (error) {
        console.error(`Error calling ${functionName}:`, error);
    }
}

// Export key functions for global access (backward compatibility)
window.sendMessage = sendMessage;
window.updateChatInput = updateChatInput;
window.setContext = setContext;
window.getContext = getContext;
window.selectChat = selectChat;
window.pauseAgent = pauseAgent;
window.resetChat = resetChat;
window.newChat = newChat;
window.killChat = killChat;
window.toggleDarkMode = toggleDarkMode;
window.toggleAutoScroll = toggleAutoScroll;
window.toggleThoughts = toggleThoughts;
window.toggleJson = toggleJson;
window.toggleUtils = toggleUtils;
window.toggleSpeech = toggleSpeech;
window.safeCall = safeCall;
window.loadKnowledge = loadKnowledge;
window.toast = toast;
window.toastFetchError = toastFetchError;
window.toggleSidebar = toggleSidebar;
window.scrollChanged = scrollChanged;
window.openTaskDetail = openTaskDetail;
window.setupTabs = setupTabs;
window.activateTab = activateTab;
window.generateGUID = generateGUID;
window.sendJsonData = sendJsonData;
window.downloadFile = downloadFile;
window.readJsonFiles = readJsonFiles;

// Module status logging
console.log('📦 Modules loaded:');
console.log('  ✓ Core Utils');
console.log('  ✓ Toast System'); 
console.log('  ✓ UI Layout');
console.log('  ✓ Chat Core');
console.log('  ✓ File Management');
console.log('  ✓ Time Utils');
console.log('  ✓ Polling System');
console.log('  ✓ Task Management');
console.log('🎯 Maho Chat UI is fully modular!'); 