/**
 * Authentication & User Management
 * Handles login status, user display, connected providers
 */

// Track auth state
let currentUser = null;
let isAuthenticated = false;

/**
 * Initialize auth module
 */
async function initAuth() {
    await checkAuthStatus();
    setupLogoutButton();
    renderConnectedAccounts();
}

/**
 * Check if user is authenticated
 */
async function checkAuthStatus() {
    try {
        // Try to get user info from session via a check endpoint
        // For now, we'll use a simple session cookie check approach
        // The backend will serve the page only if logged in

        // If we got here, user is authenticated (served by /login redirect if not)
        isAuthenticated = true;

        // Try to extract user info from session (if available via meta tags or API)
        // For now, use a generic user display
        currentUser = {
            email: 'user@example.com',
        };

        updateUserDisplay();
    } catch (e) {
        console.log('Not authenticated, redirecting...');
        isAuthenticated = false;
    }
}

/**
 * Update user display in sidebar
 */
function updateUserDisplay() {
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');

    if (isAuthenticated && currentUser) {
        const initials = getInitials(currentUser.email || 'User');
        avatarEl.textContent = initials;
        nameEl.textContent = currentUser.email?.split('@')[0] || 'User';
    } else {
        avatarEl.textContent = '–';
        nameEl.textContent = 'Not logged in';
    }
}

/**
 * Render connected accounts panel
 */
async function renderConnectedAccounts() {
    const container = document.getElementById('connected-accounts');

    if (!container) return;

    const providers = [
        { id: 'gmail', name: 'Gmail', emoji: '✉️' },
        { id: 'google-calendar', name: 'Google Calendar', emoji: '📅' },
        { id: 'github', name: 'GitHub', emoji: '🐙' },
    ];

    try {
        // Fetch connected providers from backend (if available)
        // For now, assume all providers as available for reconnection
        container.innerHTML = providers.map(provider => `
            <div class="account-card">
                <div class="account-header">
                    <span class="account-icon">${provider.emoji}</span>
                    <span>${provider.name}</span>
                </div>
                <div class="account-status connected">Connected</div>
                <div class="account-actions">
                    <button class="btn btn-secondary btn-small" onclick="reconnectProvider('${provider.id}')">
                        Reconnect
                    </button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error rendering connected accounts:', e);
        container.innerHTML = '<p style="color: var(--text-dim);">Unable to load connected accounts</p>';
    }
}

/**
 * Reconnect a provider
 * @param {string} provider - Provider ID (gmail, google-calendar, github)
 */
function reconnectProvider(provider) {
    window.location.href = `/connect/${provider}`;
}

/**
 * Setup logout button
 */
function setupLogoutButton() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
}

/**
 * Logout the user
 */
function logout() {
    window.location.href = '/logout';
}

/**
 * Reconnect all providers
 */
function reconnectAll() {
    window.location.href = '/connect/all';
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', initAuth);
