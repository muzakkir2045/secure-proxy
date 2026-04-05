/**
 * Agent Task Runner
 * Handles agent task execution and result display
 */

/**
 * Initialize agent module
 */
function initAgent() {
    setupTaskForm();
}

/**
 * Setup task form event listeners
 */
function setupTaskForm() {
    const runBtn = document.getElementById('run-task-btn');
    const clearBtn = document.getElementById('clear-result-btn');
    const actionSelect = document.getElementById('action');

    if (runBtn) {
        runBtn.addEventListener('click', runTask);
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', clearResult);
    }

    if (actionSelect) {
        actionSelect.addEventListener('change', updateParamsPlaceholder);
    }
}

/**
 * Update params placeholder based on selected action
 */
function updateParamsPlaceholder() {
    const action = document.getElementById('action').value;
    const paramsTextarea = document.getElementById('params');

    const placeholders = {
        'fetch_emails': '{"max_results": 10}',
        'create_calendar_event': '{"title": "Meeting", "start": "2025-01-15T10:00:00Z"}',
        'create_github_issue': '{"title": "Bug fix", "body": "Description", "repo": "owner/repo"}',
    };

    paramsTextarea.placeholder = placeholders[action] || '{}';
}

/**
 * Run agent task
 */
async function runTask() {
    const action = document.getElementById('action').value;
    const paramsStr = document.getElementById('params').value;
    const runBtn = document.getElementById('run-task-btn');
    const resultEl = document.getElementById('result');
    const statusEl = document.getElementById('result-status');

    // Validate params
    const params = parseJSON(paramsStr);
    if (params === null) {
        showToast('Invalid JSON in parameters', 'error');
        return;
    }

    // Show loading state
    setStatusLoading();
    addSpinner(runBtn);

    try {
        const response = await fetch('/agent/task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action,
                params,
            }),
        });

        const data = await response.json();

        // Display result
        if (response.ok) {
            setStatusSuccess(response.status);
            resultEl.textContent = formatJSON(data);
            showToast('Task executed successfully', 'success');
        } else {
            setStatusError(response.status);
            resultEl.textContent = formatJSON(data);
            showToast(`Task failed: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Task execution error:', error);
        setStatusError('Error');
        resultEl.textContent = `Network Error:\n${error.message}`;
        showToast(`Network error: ${error.message}`, 'error');
    } finally {
        removeSpinner(runBtn);
    }
}

/**
 * Clear result display
 */
function clearResult() {
    const resultEl = document.getElementById('result');
    const statusEl = document.getElementById('result-status');

    resultEl.textContent = 'Results will appear here…';
    resultEl.classList.add('result-empty');
    statusEl.textContent = 'Ready';
    statusEl.className = 'result-status';
}

/**
 * Set status to loading
 */
function setStatusLoading() {
    const statusEl = document.getElementById('result-status');
    statusEl.textContent = 'Loading…';
    statusEl.className = 'result-status loading';
}

/**
 * Set status to success
 * @param {number} code - HTTP status code
 */
function setStatusSuccess(code = 200) {
    const statusEl = document.getElementById('result-status');
    statusEl.textContent = `${code} OK`;
    statusEl.className = 'result-status ok';
}

/**
 * Set status to error
 * @param {string|number} code - HTTP status code or error message
 */
function setStatusError(code = 'Error') {
    const statusEl = document.getElementById('result-status');
    statusEl.textContent = `${code} Error`;
    statusEl.className = 'result-status error';
}

// Initialize agent on page load
document.addEventListener('DOMContentLoaded', initAgent);
