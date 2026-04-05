/**
 * Main Navigation & Application Setup
 */

/**
 * Page titles mapping
 */
const PAGE_TITLES = {
    dashboard: 'Dashboard',
    agent: 'Run Agent Task',
};

/**
 * Navigate to a page
 * @param {string} pageId - Page ID to navigate to
 */
function navigateTo(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Deactivate all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Show selected page
    const pageEl = document.getElementById(`page-${pageId}`);
    if (pageEl) {
        pageEl.classList.add('active');
    }

    // Activate nav item
    const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }

    // Update page title
    const titleEl = document.getElementById('page-title');
    if (titleEl) {
        titleEl.textContent = PAGE_TITLES[pageId] || 'SecureProxy';
    }
}

/**
 * Setup navigation event listeners
 */
function setupNavigation() {
    // Page navigation links
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const pageId = item.dataset.page;
            navigateTo(pageId);
        });
    });
}

/**
 * Initialize application
 */
function initApp() {
    setupNavigation();

    // Set homepage
    navigateTo('dashboard');

    // Log initialization
    console.log('✓ SecureProxy Control Panel initialized');
    console.log('✓ Version: 2.0 (Modular)');
}

/**
 * Handle page visibility changes
 * Refresh connected accounts when returning to dashboard
 */
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && document.querySelector('.page.active')?.id === 'page-dashboard') {
        // Optionally refresh connected accounts
        // renderConnectedAccounts();
    }
});

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
