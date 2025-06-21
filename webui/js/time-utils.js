/**
 * Time utilities for handling UTC to local time conversion
 */

/**
 * Convert a UTC ISO string to a local time string
 * @param {string} utcIsoString - UTC time in ISO format
 * @param {Object} options - Formatting options for Intl.DateTimeFormat
 * @returns {string} Formatted local time string
 */
export function toLocalTime(utcIsoString, options = {}) {
  if (!utcIsoString) return '';

  const date = new Date(utcIsoString);
  const defaultOptions = {
    dateStyle: 'medium',
    timeStyle: 'medium'
  };

  return new Intl.DateTimeFormat(
    undefined, // Use browser's locale
    { ...defaultOptions, ...options }
  ).format(date);
}

/**
 * Convert a local Date object to UTC ISO string
 * @param {Date} date - Date object in local time
 * @returns {string} UTC ISO string
 */
export function toUTCISOString(date) {
  if (!date) return '';
  return date.toISOString();
}

/**
 * Get current time as UTC ISO string
 * @returns {string} Current UTC time in ISO format
 */
export function getCurrentUTCISOString() {
  return new Date().toISOString();
}

/**
 * Format a UTC ISO string for display in local time with configurable format
 * @param {string} utcIsoString - UTC time in ISO format
 * @param {string} format - Format type ('full', 'date', 'time', 'short')
 * @returns {string} Formatted local time string
 */
export function formatDateTime(utcIsoString, format = 'full') {
  if (!utcIsoString) return '';

  const date = new Date(utcIsoString);

  const formatOptions = {
    full: { dateStyle: 'medium', timeStyle: 'medium' },
    date: { dateStyle: 'medium' },
    time: { timeStyle: 'medium' },
    short: { dateStyle: 'short', timeStyle: 'short' }
  };

  return toLocalTime(utcIsoString, formatOptions[format] || formatOptions.full);
}

/**
 * Get the user's local timezone name
 * @returns {string} Timezone name (e.g., 'America/New_York')
 */
export function getUserTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// Time & Date Utilities Module
// Handles time display, formatting, and date operations

let timeUpdateInterval = null;

export function updateUserTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();
    const ampm = hours >= 12 ? 'pm' : 'am';
    const formattedHours = hours % 12 || 12;

    // Format the time
    const timeString = `${formattedHours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')} ${ampm}`;

    // Format the date
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    const dateString = now.toLocaleDateString(undefined, options);

    // Update the HTML
    const userTimeElement = document.getElementById('time-date');
    if (userTimeElement) {
        userTimeElement.innerHTML = `${timeString}<br><span id="user-date">${dateString}</span>`;
    }
}

export function startTimeUpdates() {
    // Initial update
    updateUserTime();
    
    // Set up interval for updates
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
    }
    timeUpdateInterval = setInterval(updateUserTime, 1000);
}

export function stopTimeUpdates() {
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
        timeUpdateInterval = null;
    }
}

// Format timestamp for display
export function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    
    // If it's today, show time only
    if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // If it's this year, show month and day
    if (date.getFullYear() === now.getFullYear()) {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
    
    // Otherwise show full date
    return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
}

// Get relative time (e.g., "2 minutes ago")
export function getRelativeTime(timestamp) {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) {
        return 'just now';
    } else if (diffMin < 60) {
        return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
    } else if (diffHour < 24) {
        return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
    } else if (diffDay < 7) {
        return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
    } else {
        return formatTimestamp(timestamp);
    }
}

// Format duration in a human-readable way
export function formatDuration(milliseconds) {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
        return `${days}d ${hours % 24}h ${minutes % 60}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

// Get timezone information
export function getTimezone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// Format date for API calls
export function formatDateForAPI(date) {
    return date.toISOString();
}

// Parse API date string
export function parseAPIDate(dateString) {
    return new Date(dateString);
}

// Global exports for backward compatibility
window.updateUserTime = updateUserTime;
window.formatTimestamp = formatTimestamp;
window.getRelativeTime = getRelativeTime;
