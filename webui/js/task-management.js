// Task Management Module
// Handles task-related functionality and scheduler integration

import { setContext } from './chat-core.js';
import { safeAlpineData } from './core-utils.js';

// Open the scheduler detail view for a specific task
export function openTaskDetail(taskId) {
    // Wait for Alpine.js to be fully loaded
    if (window.Alpine) {
        // Get the settings modal button and click it to ensure all init logic happens
        const settingsButton = document.getElementById('settings');
        if (settingsButton) {
            // Programmatically click the settings button
            settingsButton.click();

            // Now get a reference to the modal element
            const modalEl = document.getElementById('settingsModal');
            if (!modalEl) {
                console.error('Settings modal element not found after clicking button');
                return;
            }

            // Get the Alpine.js data for the modal
            const modalData = Alpine.$data(modalEl);

            // Use a timeout to ensure the modal is fully rendered
            setTimeout(() => {
                // Switch to the scheduler tab first
                modalData.switchTab('scheduler');

                // Use another timeout to ensure the scheduler component is initialized
                setTimeout(() => {
                    // Get the scheduler component
                    const schedulerComponent = document.querySelector('[x-data="schedulerSettings"]');
                    if (!schedulerComponent) {
                        console.error('Scheduler component not found');
                        return;
                    }

                    // Get the Alpine.js data for the scheduler component
                    const schedulerData = Alpine.$data(schedulerComponent);

                    // Show the task detail view for the specific task
                    schedulerData.showTaskDetail(taskId);

                    console.log('Task detail view opened for task:', taskId);
                }, 50); // Give time for the scheduler tab to initialize
            }, 25); // Give time for the modal to render
        } else {
            console.error('Settings button not found');
        }
    } else {
        console.warn('Alpine.js not loaded yet, retrying in 100ms...');
        setTimeout(() => openTaskDetail(taskId), 100);
    }
}

// Tab management for tasks vs chats
export function activateTab(tabName) {
    const chatsTab = document.getElementById('chats-tab');
    const tasksTab = document.getElementById('tasks-tab');
    const chatsSection = document.getElementById('chats-section');
    const tasksSection = document.getElementById('tasks-section');

    if (!chatsTab || !tasksTab || !chatsSection || !tasksSection) {
        console.error('Tab elements not found');
        return;
    }

    // Get current context to preserve before switching
    const currentContext = window.getContext ? window.getContext() : null;

    // Store the current selection for the active tab before switching
    const previousTab = localStorage.getItem('activeTab');
    if (previousTab === 'chats') {
        localStorage.setItem('lastSelectedChat', currentContext || '');
    } else if (previousTab === 'tasks') {
        localStorage.setItem('lastSelectedTask', currentContext || '');
    }

    // Reset all tabs and sections
    chatsTab.classList.remove('active');
    tasksTab.classList.remove('active');
    chatsSection.style.display = 'none';
    tasksSection.style.display = 'none';

    // Remember the last active tab in localStorage
    localStorage.setItem('activeTab', tabName);

    // Activate selected tab and section
    if (tabName === 'chats') {
        chatsTab.classList.add('active');
        chatsSection.style.display = '';

        // Use safe Alpine data access
        const chatsAD = safeAlpineData(chatsSection);
        if (chatsAD) {
            // Don't auto-restore chat selection for blank state UX
            // Users will start with a clean slate instead
        }
    } else if (tabName === 'tasks') {
        tasksTab.classList.add('active');
        tasksSection.style.display = 'flex';
        tasksSection.style.flexDirection = 'column';

        // Use safe Alpine data access
        const tasksAD = safeAlpineData(tasksSection);
        if (tasksAD) {
            const availableTasks = tasksAD.tasks || [];

            // Restore previous task selection
            const lastSelectedTask = localStorage.getItem('lastSelectedTask');

            // Only switch if:
            // 1. lastSelectedTask exists AND
            // 2. It's different from current context AND
            // 3. The task actually exists in our tasks list
            if (lastSelectedTask &&
                lastSelectedTask !== currentContext &&
                availableTasks.some(task => task.id === lastSelectedTask)) {
                setContext(lastSelectedTask);
            }
        }
    }

    // Request a poll update
    if (window.poll) {
        window.poll();
    }
}

export function setupTabs() {
    const chatsTab = document.getElementById('chats-tab');
    const tasksTab = document.getElementById('tasks-tab');

    if (chatsTab && tasksTab) {
        chatsTab.addEventListener('click', function() {
            activateTab('chats');
        });

        tasksTab.addEventListener('click', function() {
            activateTab('tasks');
        });
    } else {
        console.error('Tab elements not found');
        setTimeout(setupTabs, 100); // Retry setup
    }
}

export function initializeActiveTab() {
    // Initialize selection storage if not present
    if (!localStorage.getItem('lastSelectedChat')) {
        localStorage.setItem('lastSelectedChat', '');
    }
    if (!localStorage.getItem('lastSelectedTask')) {
        localStorage.setItem('lastSelectedTask', '');
    }

    const activeTab = localStorage.getItem('activeTab') || 'chats';
    activateTab(activeTab);
}

// Task filtering and sorting utilities
export function filterTasks(tasks, filter) {
    if (!tasks || !Array.isArray(tasks)) return [];
    
    switch (filter) {
        case 'active':
            return tasks.filter(task => task.status === 'active');
        case 'completed':
            return tasks.filter(task => task.status === 'completed');
        case 'pending':
            return tasks.filter(task => task.status === 'pending');
        case 'all':
        default:
            return tasks;
    }
}

export function sortTasks(tasks, sortBy = 'created_at', order = 'desc') {
    if (!tasks || !Array.isArray(tasks)) return [];
    
    return [...tasks].sort((a, b) => {
        let aVal = a[sortBy];
        let bVal = b[sortBy];
        
        // Handle different data types
        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        if (order === 'desc') {
            return bVal > aVal ? 1 : bVal < aVal ? -1 : 0;
        } else {
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        }
    });
}

// Task status management
export function getTaskStatusColor(status) {
    const statusColors = {
        'pending': 'text-yellow-600',
        'active': 'text-blue-600',
        'completed': 'text-green-600',
        'failed': 'text-red-600',
        'cancelled': 'text-gray-600'
    };
    
    return statusColors[status] || 'text-gray-600';
}

export function getTaskStatusIcon(status) {
    const statusIcons = {
        'pending': '⏳',
        'active': '🔄',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '⏹️'
    };
    
    return statusIcons[status] || '📋';
}

// Global exports for backward compatibility
window.openTaskDetail = openTaskDetail;
window.setupTabs = setupTabs;
window.activateTab = activateTab;
window.initializeActiveTab = initializeActiveTab; 