/**
 * UI Utilities — Toast notifications and helper functions
 */

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Type: 'success', 'error', 'info' (default: 'info')
 * @param {number} duration - Duration in ms (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Format JSON for display
 * @param {any} data - Data to format
 * @returns {string} Formatted JSON string
 */
function formatJSON(data) {
    return JSON.stringify(data, null, 2);
}

/**
 * Parse JSON safely
 * @param {string} str - JSON string
 * @returns {any|null} Parsed object or null on error
 */
function parseJSON(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        return null;
    }
}

/**
 * Debounce function
 * @param {Function} fn - Function to debounce
 * @param {number} ms - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(fn, ms = 300) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), ms);
    };
}

/**
 * Convert email to initials (e.g., "John Doe" -> "JD")
 * @param {string} email - Email or name
 * @returns {string} Initials (max 2 chars)
 */
function getInitials(email) {
    if (!email) return '–';
    const parts = email.replace(/@.*/, '')
        .split(/[._-]/)
        .map(p => p.charAt(0).toUpperCase())
        .filter(Boolean);
    return parts.slice(0, 2).join('');
}

/**
 * Get color for service icons
 * @param {string} service - Service name (gmail, github, google-calendar)
 * @returns {string} Service emoji
 */
function getServiceEmoji(service) {
    const emojis = {
        gmail: '✉️',
        'google-calendar': '📅',
        github: '🐙',
    };
    return emojis[service] || '⚙️';
}

/**
 * Get service display name
 * @param {string} service - Service slug
 * @returns {string} Display name
 */
function getServiceName(service) {
    const names = {
        gmail: 'Gmail',
        'google-calendar': 'Google Calendar',
        github: 'GitHub',
    };
    return names[service] || service;
}

/**
 * Add loading spinner to element
 * @param {HTMLElement} element - Element to add spinner to
 */
function addSpinner(element) {
    element.style.opacity = '0.6';
    element.style.pointerEvents = 'none';
    element.dataset.loading = 'true';
}

/**
 * Remove loading spinner from element
 * @param {HTMLElement} element - Element to remove spinner from
 */
function removeSpinner(element) {
    element.style.opacity = '1';
    element.style.pointerEvents = 'auto';
    delete element.dataset.loading;
}
