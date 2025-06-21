// UI Layout Module
// Handles responsive layout, sidebar, and UI state management

import { isMobile, addClassToElement, removeClassFromElement } from './core-utils.js';

let sidebarState = {
    isOpen: false,
    isInitialized: false
};

export function toggleSidebar(show) {
    const sidebar = document.getElementById('left-panel');
    const mainContent = document.querySelector('.main-content');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (!sidebar) return;

    if (show === undefined) {
        show = !sidebarState.isOpen;
    }

    sidebarState.isOpen = show;

    if (show) {
        removeClassFromElement(sidebar, 'hidden');
        if (overlay) addClassToElement(overlay, 'visible');
        if (isMobile() && mainContent) {
            addClassToElement(mainContent, 'sidebar-push');
        }
    } else {
        addClassToElement(sidebar, 'hidden');
        if (overlay) removeClassFromElement(overlay, 'visible');
        if (mainContent) {
            removeClassFromElement(mainContent, 'sidebar-push');
        }
    }

    // Store preference
    localStorage.setItem('sidebarOpen', show.toString());
}

export function handleResize() {
    const sidebar = document.getElementById('left-panel');
    if (!sidebar) return;

    if (isMobile()) {
        // On mobile, sidebar should be closed by default
        if (!sidebarState.isInitialized) {
            toggleSidebar(false);
        }
    } else {
        // On desktop, restore saved preference
        const savedState = localStorage.getItem('sidebarOpen');
        if (savedState !== null && !sidebarState.isInitialized) {
            toggleSidebar(savedState === 'true');
        } else if (!sidebarState.isInitialized) {
            toggleSidebar(true); // Default open on desktop
        }
    }
    
    sidebarState.isInitialized = true;
}

export function setupSidebarToggle() {
    const toggleButton = document.getElementById('toggle-sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (toggleButton) {
        toggleButton.addEventListener('click', (e) => {
            e.preventDefault();
            toggleSidebar();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            if (isMobile()) {
                toggleSidebar(false);
            }
        });
    }

    // Handle escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebarState.isOpen && isMobile()) {
            toggleSidebar(false);
        }
    });

    // Initial setup
    handleResize();
    
    // Listen for resize events
    window.addEventListener('resize', handleResize);
}

// Tab Management
let activeTab = null;

export function setupTabs() {
    const tabButtons = document.querySelectorAll('[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = button.getAttribute('data-tab');
            activateTab(tabName);
        });
    });

    // Initialize first tab
    if (tabButtons.length > 0) {
        const firstTab = tabButtons[0].getAttribute('data-tab');
        activateTab(firstTab);
    }
}

export function activateTab(tabName) {
    const tabButtons = document.querySelectorAll('[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    // Update buttons
    tabButtons.forEach(button => {
        if (button.getAttribute('data-tab') === tabName) {
            addClassToElement(button, 'active');
        } else {
            removeClassFromElement(button, 'active');
        }
    });

    // Update content
    tabContents.forEach(content => {
        if (content.getAttribute('data-tab-content') === tabName) {
            content.style.display = 'block';
            addClassToElement(content, 'active');
        } else {
            content.style.display = 'none';
            removeClassFromElement(content, 'active');
        }
    });

    activeTab = tabName;
    
    // Trigger custom event for tab change
    document.dispatchEvent(new CustomEvent('tabChanged', { 
        detail: { tabName } 
    }));
}

export function initializeActiveTab() {
    if (activeTab) {
        activateTab(activeTab);
    }
}

export function getActiveTab() {
    return activeTab;
}

// Scroll Management
let isAtBottom = true;

export function scrollChanged(atBottom) {
    isAtBottom = atBottom;
    updateAfterScroll();
}

export function updateAfterScroll() {
    const scrollToBottomBtn = document.getElementById('scroll-to-bottom');
    if (scrollToBottomBtn) {
        if (isAtBottom) {
            scrollToBottomBtn.style.display = 'none';
        } else {
            scrollToBottomBtn.style.display = 'block';
        }
    }
}

// Global exports for backward compatibility
window.toggleSidebar = toggleSidebar;
window.setupTabs = setupTabs;
window.activateTab = activateTab;
window.scrollChanged = scrollChanged; 