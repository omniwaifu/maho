// Chat Core Module
// Handles chat messaging, context management, and real-time polling

import { generateGUID, sendJsonData, adjustTextareaHeight } from './core-utils.js';
import { toastFetchError, toast } from './toast-system.js';
import { getHandler } from './messages.js';

// State management
let context = null;
let lastLogVersion = 0;
let lastLogGuid = null;
let lastSpokenNo = 0;
let autoScroll = true;
let isFirstMessage = false;

// DOM elements (initialized on load)
let chatInput, sendButton, chatHistory, inputSection, chatsSection, progressBar;

// Initialize DOM references
export function initializeChatCore() {
    chatInput = document.getElementById('chat-input');
    sendButton = document.getElementById('send-button');
    chatHistory = document.getElementById('chat-history');
    inputSection = document.getElementById('input-section');
    chatsSection = document.getElementById('chats-section');
    progressBar = document.getElementById('progress-bar');

    // Setup event listeners
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    // Initialize with blank state
    setContext(null);
}

export async function sendMessage() {
    try {
        const message = chatInput.value.trim();
        const inputAD = Alpine.$data(inputSection);
        const attachments = inputAD.attachments;
        const hasAttachments = attachments && attachments.length > 0;

        if (message || hasAttachments) {
            // Clear input and attachments immediately for better UX (no duplication)
            chatInput.value = '';
            inputAD.attachments = [];
            inputAD.hasAttachments = false;
            adjustTextareaHeight();
            
            let currentContext = getContext();
            
            // If no context, create a new one
            if (!currentContext) {
                currentContext = generateGUID();
                isFirstMessage = true;
                setContext(currentContext);
            }
            
            let response;
            const messageId = generateGUID();

            // Include attachments in the user message
            if (hasAttachments) {
                const attachmentsWithUrls = attachments.map(attachment => {
                    if (attachment.type === 'image') {
                        return {
                            ...attachment,
                            url: URL.createObjectURL(attachment.file)
                        };
                    } else {
                        return {
                            ...attachment
                        };
                    }
                });

                // Render user message with attachments
                setMessage(messageId, 'user', '', message, false, {
                    attachments: attachmentsWithUrls
                });

                const formData = new FormData();
                formData.append('text', message);
                formData.append('context', currentContext);
                formData.append('message_id', messageId);

                for (let i = 0; i < attachments.length; i++) {
                    formData.append('attachments', attachments[i].file);
                }

                response = await fetch('/api/v1/message_async', {
                    method: 'POST',
                    body: formData
                });
            } else {
                // For text-only messages - display user message first
                setMessage(messageId, 'user', '', message, false);
                
                const data = {
                    text: message,
                    context: currentContext,
                    message_id: messageId
                };
                response = await fetch('/api/v1/message_async', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
            }

            // Handle response
            const jsonResponse = await response.json();
            if (!jsonResponse) {
                toast("No response returned.", "error");
            } else {
                // Only set context if it's different to avoid clearing chat history
                if (jsonResponse.context !== getContext()) {
                    setContext(jsonResponse.context);
                }
                isFirstMessage = false;
            }
        }
    } catch (e) {
        toastFetchError("Error sending message", e);
    }
}

export function updateChatInput(text) {
    console.log('updateChatInput called with:', text);

    // Append text with proper spacing
    const currentValue = chatInput.value;
    const needsSpace = currentValue.length > 0 && !currentValue.endsWith(' ');
    chatInput.value = currentValue + (needsSpace ? ' ' : '') + text + ' ';

    // Adjust height and trigger input event
    adjustTextareaHeight();
    chatInput.dispatchEvent(new Event('input'));

    console.log('Updated chat input value:', chatInput.value);
}

export function setMessage(id, type, heading, content, temp, kvps = null) {
    // Search for the existing message container by id
    let messageContainer = document.getElementById(`message-${id}`);

    if (messageContainer) {
        // Don't re-render user messages
        if (type === 'user') {
            return; // Skip re-rendering
        }
        // For other types, update the message
        messageContainer.innerHTML = '';
    } else {
        // Create a new container if not found
        const sender = type === 'user' ? 'user' : 'ai';
        messageContainer = document.createElement('div');
        messageContainer.id = `message-${id}`;
        messageContainer.classList.add('message-container', `${sender}-container`);
        if (temp) messageContainer.classList.add("message-temp");
    }

    const handler = getHandler(type);
    handler(messageContainer, id, type, heading, content, temp, kvps);

    // If the container was found, it was already in the DOM, no need to append again
    if (!document.getElementById(`message-${id}`)) {
        chatHistory.appendChild(messageContainer);
    }

    if (autoScroll) chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Context Management
export const setContext = function (id) {
    const wasBlank = !context;
    context = id;
    
    // Update blank state visibility
    const blankState = document.getElementById('blank-state');
    if (context) {
        // Hide blank state when we have a context
        if (blankState) {
            blankState.style.display = 'none';
        }
    } else {
        // Show blank state when no context - recreate if needed
        if (!blankState) {
            createBlankState();
        } else {
            blankState.style.display = 'flex';
        }
    }
    
    // Only clear history when switching between existing contexts
    // Don't clear when setting initial context (wasBlank = true)
    // Don't clear when processing first message to preserve user input
    if (!wasBlank && context && !isFirstMessage) {
        chatHistory.innerHTML = "";
        lastLogVersion = 0;
        lastLogGuid = null;
    }
    
    console.log(`Context set to: ${context}`);
};

// Helper function to create blank state (moved from index.js)
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

export const getContext = function () {
    return context;
};

export function selectChat(id) {
    console.log('Selecting chat:', id);
    console.log('Current context before:', context);
    
    // Clear chat history when switching to a different chat
    if (context !== id) {
        chatHistory.innerHTML = "";
    }
    
    // Reset polling state when switching contexts to force reload
    lastLogVersion = 0;
    lastLogGuid = null;
    isFirstMessage = false; // Ensure this doesn't interfere
    
    setContext(id);
    console.log('Current context after:', context);
}

export function switchFromContext(id) {
    if (context === id) {
        const chatsAD = Alpine.$data(chatsSection);
        const contexts = chatsAD.contexts || [];
        
        // Find another context to switch to
        const otherContext = contexts.find(ctx => ctx.id !== id);
        
        if (otherContext) {
            // Switch to another chat
            selectChat(otherContext.id);
            chatsAD.selected = otherContext.id;
        } else {
            // No other contexts, clear everything and go to blank state
            chatHistory.innerHTML = "";
            lastLogVersion = 0;
            lastLogGuid = null;
            setContext(null);
            chatsAD.selected = null;
        }
    }
}

// Polling System
export async function poll() {
    let updated = false;
    try {
        // Get timezone from navigator
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        const response = await sendJsonData(
            "/api/v1/poll",
            {
                log_from: lastLogVersion,
                context: context,
                timezone: timezone
            }
        );

        // Check if the response is valid
        if (!response) {
            console.error("Invalid response from poll endpoint");
            return false;
        }

        // Handle context setting - only set context if we don't have one or it matches backend
        if (!context) {
            // Only auto-set context if user hasn't made any selection yet
            // Check if there's an actual UI selection first
            const chatsAD = Alpine.$data(chatsSection);
            const hasUserSelection = chatsAD && chatsAD.selected;
            
            if (!hasUserSelection) {
                // No user selection - keep showing blank state, don't auto-select
                context = null;
            } else {
                // User has made a selection, use backend context
                setContext(response.context);
            }
        } else if (response.context != context) {
            // Context mismatch - skip this poll to avoid conflicts
            return;
        }

        // Only process logs if we have a real context
        if (context) {
            if (lastLogGuid != response.log_guid) {
                // Only clear history if we have an existing log GUID AND we're not on the first message
                // This prevents clearing user messages when starting a new chat
                if (lastLogGuid && !isFirstMessage) {
                    chatHistory.innerHTML = "";
                }
                lastLogVersion = 0;
            }

            if (lastLogVersion != response.log_version) {
                updated = true;
                for (const log of response.logs) {
                    const messageId = log.id || log.no; // Use log.id if available
                    setMessage(messageId, log.type, log.heading, log.content, log.temp, log.kvps);
                }
                afterMessagesUpdate(response.logs);
                
                // Reset first message flag after processing logs from the first exchange
                if (isFirstMessage) {
                    isFirstMessage = false;
                }
            }
        }

        lastLogVersion = response.log_version;
        lastLogGuid = response.log_guid;

        updateProgress(response.log_progress, response.log_progress_active);

        //set ui model vars from backend
        const inputAD = Alpine.$data(inputSection);
        inputAD.paused = response.paused;

        // Update status icon state
        setConnectionStatus(true);

        // Update chats list and sort by created_at time (newer first)
        const chatsAD = Alpine.$data(chatsSection);
        const contexts = response.contexts || [];
        chatsAD.contexts = contexts.sort((a, b) =>
            (b.created_at || 0) - (a.created_at || 0)
        );

        // Update tasks list and sort by creation time (newer first)
        const tasksSection = document.getElementById('tasks-section');
        if (tasksSection) {
            const tasksAD = Alpine.$data(tasksSection);
            let tasks = response.tasks || [];

            // Always update tasks to ensure state changes are reflected
            if (tasks.length > 0) {
                // Sort the tasks by creation time
                const sortedTasks = [...tasks].sort((a, b) =>
                    (b.created_at || 0) - (a.created_at || 0)
                );

                // Assign the sorted tasks to the Alpine data
                tasksAD.tasks = sortedTasks;
            } else {
                // Make sure to use a new empty array instance
                tasksAD.tasks = [];
            }
        }

        // Make sure the active context is properly selected in both lists
        if (context) {
            // Update selection in the active tab
            const activeTab = localStorage.getItem('activeTab') || 'chats';

            if (activeTab === 'chats') {
                chatsAD.selected = context;
                localStorage.setItem('lastSelectedChat', context);

                // Check if this context exists in the chats list
                const contextExists = contexts.some(ctx => ctx.id === context);

                // REMOVED: Auto-selection of first chat when current context doesn't exist
                // This was causing blank state to be overridden on page load
                // Users should explicitly select a chat instead of auto-loading
            } else if (activeTab === 'tasks' && tasksSection) {
                const tasksAD = Alpine.$data(tasksSection);
                tasksAD.selected = context;
                localStorage.setItem('lastSelectedTask', context);

                // Check if this context exists in the tasks list
                const taskExists = response.tasks?.some(task => task.id === context);

                // If it doesn't exist in the tasks list but we're in tasks tab, try to select the first task
                if (!taskExists && response.tasks?.length > 0) {
                    const firstTaskId = response.tasks[0].id;
                    setContext(firstTaskId);
                    tasksAD.selected = firstTaskId;
                    localStorage.setItem('lastSelectedTask', firstTaskId);
                }
            }
        } else if (response.tasks && response.tasks.length > 0 && localStorage.getItem('activeTab') === 'tasks') {
            // If we're in tasks tab with no selection but have tasks, select the first one
            const firstTaskId = response.tasks[0].id;
            setContext(firstTaskId);
            if (tasksSection) {
                const tasksAD = Alpine.$data(tasksSection);
                tasksAD.selected = firstTaskId;
                localStorage.setItem('lastSelectedTask', firstTaskId);
            }
        }
        // REMOVED: Auto-selection of first chat to enable blank state UX like ChatGPT
        // Users will start with a clean slate instead of automatically loading the first chat

    } catch (error) {
        console.error('Error:', error);
        setConnectionStatus(false);
    }

    return updated;
}

function afterMessagesUpdate(logs) {
    if (localStorage.getItem('speech') == 'true') {
        speakMessages(logs);
    }
}

function speakMessages(logs) {
    // log.no, log.type, log.heading, log.content
    for (let i = logs.length - 1; i >= 0; i--) {
        const log = logs[i];
        if (log.type == "response") {
            if (log.no > lastSpokenNo) {
                lastSpokenNo = log.no;
                window.speech.speak(log.content);
                return;
            }
        }
    }
}

function updateProgress(progress, active) {
    if (!progress) progress = "";

    if (!active) {
        progressBar.classList.remove("shiny-text");
    } else {
        progressBar.classList.add("shiny-text");
    }

    if (progressBar.innerHTML != progress) {
        progressBar.innerHTML = progress;
    }
}

// Connection status management
let connectionStatus = true;

export function getConnectionStatus() {
    return connectionStatus;
}

export function setConnectionStatus(connected) {
    connectionStatus = connected;
    // Update UI connection indicator
    const statusIndicator = document.getElementById('connection-status');
    if (statusIndicator) {
        statusIndicator.className = connected ? 'connected' : 'disconnected';
    }
}

// Chat Management Functions
export async function pauseAgent(paused) {
    try {
        const resp = await sendJsonData("/api/v1/pause", { paused: paused, context });
    } catch (e) {
        toastFetchError("Error pausing agent", e);
    }
}

export async function resetChat(ctxid = null) {
    try {
        const resp = await sendJsonData("/api/v1/chat_reset", { "context": ctxid === null ? context : ctxid });
        if (ctxid === null) {
            // Update scroll after reset
            if (autoScroll) chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    } catch (e) {
        toastFetchError("Error resetting chat", e);
    }
}

export async function newChat() {
    try {
        // Clear chat history DOM immediately to prevent lingering messages
        chatHistory.innerHTML = "";
        
        // Reset polling state to start fresh
        lastLogVersion = 0;
        lastLogGuid = null;
        isFirstMessage = false;
        
        // Clear context to show blank state
        setContext(null);
        
        // Clear selection in both lists
        const chatsAD = Alpine.$data(chatsSection);
        const tasksSection = document.getElementById('tasks-section');
        if (tasksSection) {
            const tasksAD = Alpine.$data(tasksSection);
            tasksAD.selected = null;
        }
        chatsAD.selected = null;
        
        // Clear localStorage selections
        localStorage.removeItem('lastSelectedChat');
        localStorage.removeItem('lastSelectedTask');
        
    } catch (e) {
        toastFetchError("Error creating new chat", e);
    }
}

export async function killChat(id) {
    if (!id) {
        console.error("No chat ID provided for deletion");
        return;
    }

    console.log("Deleting chat with ID:", id);

    try {
        const chatsAD = Alpine.$data(chatsSection);
        console.log("Current contexts before deletion:", JSON.stringify(chatsAD.contexts.map(c => ({ id: c.id, name: c.name }))));

        // switch to another context if deleting current
        switchFromContext(id);

        // Delete the chat on the server
        const response = await sendJsonData("/api/v1/chat_remove", { "context": id });
        
        if (response.success) {
            toast("Chat deleted successfully", "success");
        } else {
            toast("Failed to delete chat", "error");
        }
        
    } catch (e) {
        toastFetchError("Error deleting chat", e);
    }
}

// Global exports for backward compatibility
window.sendMessage = sendMessage;
window.updateChatInput = updateChatInput;
window.setContext = setContext;
window.getContext = getContext;
window.pauseAgent = pauseAgent;
window.resetChat = resetChat;
window.newChat = newChat;
window.killChat = killChat; 