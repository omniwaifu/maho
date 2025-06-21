// Polling System Module
// Handles real-time polling for updates and connection management

import { poll } from './chat-core.js';

let pollingInterval = null;
let isPolling = false;
const POLL_INTERVAL = 1000; // 1 second

export async function startPolling() {
    if (isPolling) {
        console.log('Polling already started');
        return;
    }

    console.log('Starting polling...');
    isPolling = true;

    // Clear any existing interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Start immediate poll
    await _doPoll();

    // Set up regular polling
    pollingInterval = setInterval(_doPoll, POLL_INTERVAL);
}

export function stopPolling() {
    console.log('Stopping polling...');
    isPolling = false;
    
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function _doPoll() {
    if (!isPolling) return;

    try {
        const updated = await poll();
        
        // Optional: Handle specific update events
        if (updated) {
            // Dispatch custom event for other modules to listen to
            document.dispatchEvent(new CustomEvent('chatUpdated', {
                detail: { timestamp: Date.now() }
            }));
        }
    } catch (error) {
        console.error('Error during polling:', error);
        
        // Don't stop polling on errors, just log them
        // The poll function itself handles connection status
    }
}

export function isPollingActive() {
    return isPolling;
}

export function restartPolling() {
    stopPolling();
    setTimeout(() => {
        startPolling();
    }, 100); // Small delay to ensure clean restart
}

// Handle page visibility changes to optimize polling
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, could reduce polling frequency
        console.log('Page hidden - polling continues at normal rate');
    } else {
        // Page is visible, ensure normal polling
        console.log('Page visible - ensuring polling is active');
        if (!isPolling) {
            startPolling();
        }
    }
});

// Handle online/offline events
window.addEventListener('online', () => {
    console.log('Connection restored - restarting polling');
    restartPolling();
});

window.addEventListener('offline', () => {
    console.log('Connection lost - polling will continue with error handling');
    // Don't stop polling completely, let the poll function handle connection status
});

// Global exports for backward compatibility
window.startPolling = startPolling;
window.stopPolling = stopPolling; 