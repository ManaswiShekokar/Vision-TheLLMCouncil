/**
 * LLM Council - Main JavaScript
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
});

/**
 * Initialize tab functionality
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Remove active from all buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Show selected tab
            const tabContent = document.getElementById(`tab-${tabId}`);
            if (tabContent) {
                tabContent.classList.add('active');
            }
        });
    });
}

/**
 * Format text with basic markdown
 */
function formatText(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
}

/**
 * Format date/time
 */
function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString();
}

/**
 * Get role icon
 */
function getRoleIcon(role) {
    const icons = {
        'researcher': '📚',
        'critic': '🔍',
        'creative_thinker': '💡',
        'practical_advisor': '🛠️',
        'verifier': '✅',
        'chairman': '👔'
    };
    return icons[role] || '🤖';
}

/**
 * Get role display name
 */
function getRoleName(role) {
    const names = {
        'researcher': 'Researcher',
        'critic': 'Critic',
        'creative_thinker': 'Creative Thinker',
        'practical_advisor': 'Practical Advisor',
        'verifier': 'Verifier',
        'chairman': 'Chairman'
    };
    return names[role] || role;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success');
    } catch (err) {
        showNotification('Failed to copy', 'error');
    }
}
