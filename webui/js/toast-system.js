// Toast System Module
// Handles all toast notifications and error messaging

export function toast(text, type = 'info', timeout = 5000) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toastElement = document.createElement('div');
    toastElement.className = `toast toast-${type}`;
    toastElement.innerHTML = `
        <div class="toast-content">
            <span class="toast-text">${text}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;

    toastContainer.appendChild(toastElement);

    // Auto-hide after timeout
    if (timeout > 0) {
        setTimeout(() => {
            if (toastElement.parentElement) {
                toastElement.remove();
            }
        }, timeout);
    }

    // Add click to dismiss
    toastElement.addEventListener('click', () => {
        toastElement.remove();
    });

    return toastElement;
}

export function hideToast() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => toast.remove());
}

export function toastFetchError(text, error) {
    let errorMessage = text;
    
    if (error) {
        if (error.message) {
            errorMessage += `: ${error.message}`;
        } else if (typeof error === 'string') {
            errorMessage += `: ${error}`;
        }
    }
    
    console.error('Fetch error:', error);
    toast(errorMessage, 'error', 8000);
}

// Success toast shorthand
export function toastSuccess(text, timeout = 3000) {
    return toast(text, 'success', timeout);
}

// Warning toast shorthand
export function toastWarning(text, timeout = 5000) {
    return toast(text, 'warning', timeout);
}

// Error toast shorthand
export function toastError(text, timeout = 8000) {
    return toast(text, 'error', timeout);
}

// Global exports for backward compatibility
window.toast = toast;
window.hideToast = hideToast;
window.toastFetchError = toastFetchError; 