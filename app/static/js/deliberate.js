/**
 * LLM Council - Deliberation Page JavaScript
 */

// State
let currentSession = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeForm();
    initializeTabs();
});

/**
 * Initialize the query form
 */
function initializeForm() {
    const form = document.getElementById('query-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

/**
 * Toggle advanced options visibility
 */
function toggleOptions() {
    const options = document.getElementById('advanced-options');
    options.classList.toggle('hidden');
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const query = document.getElementById('query').value.trim();
    if (!query) return;
    
    const enablePeerReview = document.getElementById('enable-peer-review').checked;
    const enableVerification = document.getElementById('enable-verification').checked;
    const deliberationRounds = parseInt(document.getElementById('deliberation-rounds').value);
    
    // Get model configuration
    const modelConfig = {};
    document.querySelectorAll('.model-select').forEach(select => {
        if (select.value) {
            modelConfig[select.dataset.role] = select.value;
        }
    });
    
    // Disable submit button
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    // Show progress section
    showProgress();
    
    try {
        const response = await fetch('/api/deliberate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                custom_models: Object.keys(modelConfig).length > 0 ? modelConfig : null,
                enable_peer_review: enablePeerReview,
                enable_verification: enableVerification,
                deliberation_rounds: deliberationRounds
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Deliberation failed');
        }
        
        const data = await response.json();
        currentSession = data;
        
        // Complete progress and show results
        completeProgress();
        displayResults(data);
        
    } catch (error) {
        console.error('Deliberation error:', error);
        const message = error.message === 'Failed to fetch'
            ? 'Connection timed out while waiting for deliberation. Try fewer heavy models or disable one stage.'
            : error.message;
        showError(message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Start Deliberation';
    }
}

/**
 * Show progress section
 */
function showProgress() {
    document.getElementById('progress-section').classList.remove('hidden');
    document.getElementById('results-section').classList.add('hidden');
    
    // Reset progress
    document.getElementById('progress-fill').style.width = '0%';
    document.querySelectorAll('.stage').forEach(s => {
        s.classList.remove('active', 'complete');
    });
    
    // Simulate progress animation
    simulateProgress();
}

/**
 * Simulate progress through stages
 */
function simulateProgress() {
    const stages = ['initial', 'review', 'improve', 'verify', 'synthesis'];
    const progressFill = document.getElementById('progress-fill');
    const statusEl = document.getElementById('progress-status');
    
    const statusMessages = [
        'Generating role-based responses...',
        'Running peer review...',
        'Improving responses based on feedback...',
        'Verifying responses for errors...',
        'Synthesizing final answer...'
    ];
    
    let currentStep = 0;
    
    const interval = setInterval(() => {
        if (currentStep >= stages.length) {
            clearInterval(interval);
            return;
        }
        
        const stage = stages[currentStep];
        const stageEl = document.getElementById(`stage-${stage}`);
        
        // Mark previous stages as complete
        for (let i = 0; i < currentStep; i++) {
            document.getElementById(`stage-${stages[i]}`).classList.remove('active');
            document.getElementById(`stage-${stages[i]}`).classList.add('complete');
        }
        
        // Mark current stage as active
        stageEl.classList.add('active');
        
        // Update progress bar
        progressFill.style.width = `${((currentStep + 1) / stages.length) * 100}%`;
        
        // Update status message
        statusEl.textContent = statusMessages[currentStep];
        
        currentStep++;
    }, 2000);
}

/**
 * Complete progress display
 */
function completeProgress() {
    const progressFill = document.getElementById('progress-fill');
    progressFill.style.width = '100%';
    
    document.querySelectorAll('.stage').forEach(s => {
        s.classList.remove('active');
        s.classList.add('complete');
    });
    
    document.getElementById('progress-status').textContent = 'Deliberation complete!';
}

/**
 * Display results
 */
function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');
    
    const session = data.session;
    const trace = data.reasoning_trace;
    
    // Display final answer
    if (session.chairman_synthesis) {
        const synthesis = session.chairman_synthesis;
        
        document.getElementById('final-answer').innerHTML = formatText(synthesis.final_answer);
        document.querySelector('.consensus-score').textContent = synthesis.consensus_score.toFixed(0);
        document.getElementById('confidence-level').textContent = synthesis.confidence_level;
        document.getElementById('processing-time').textContent = 
            session.processing_time_seconds.toFixed(1) + 's';
        
        // Key points
        const keyPointsList = document.getElementById('key-points-list');
        keyPointsList.innerHTML = synthesis.key_points
            .map(point => `<li>${formatText(point)}</li>`)
            .join('');
        
        // Agreement/Disagreement
        document.getElementById('agreement-list').innerHTML = synthesis.areas_of_agreement
            .map(point => `<li>${formatText(point)}</li>`)
            .join('') || '<li class="text-muted">None identified</li>';
        
        document.getElementById('disagreement-list').innerHTML = synthesis.areas_of_disagreement
            .map(point => `<li>${formatText(point)}</li>`)
            .join('') || '<li class="text-muted">None identified</li>';
    }
    
    // Display role responses
    displayRoleResponses(session.initial_responses);
    
    // Display peer reviews
    displayPeerReviews(session.peer_reviews, session.weighted_scores);
    
    // Display improved responses
    displayImprovedResponses(session.improved_responses);
    
    // Display verification
    displayVerification(session.verification_report);
    
    // Display reasoning trace
    displayReasoningTrace(trace);
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Display role-based responses
 */
function displayRoleResponses(responses) {
    const grid = document.getElementById('responses-grid');
    grid.innerHTML = '';
    
    for (const [role, response] of Object.entries(responses || {})) {
        const card = document.createElement('div');
        card.className = 'response-card';
        card.innerHTML = `
            <h4>${getRoleIcon(role)} ${response.role_name}</h4>
            <p class="model-used">Model: ${response.model_used}</p>
            <div class="response-text">${formatText(response.response)}</div>
        `;
        grid.appendChild(card);
    }
}

/**
 * Display peer reviews
 */
function displayPeerReviews(reviews, weightedScores) {
    const container = document.getElementById('reviews-container');
    container.innerHTML = '';
    
    if (!reviews || reviews.length === 0) {
        container.innerHTML = '<p class="text-muted">No peer reviews available</p>';
        return;
    }
    
    // Group reviews by target
    const reviewsByTarget = {};
    for (const review of reviews) {
        if (!reviewsByTarget[review.target_role]) {
            reviewsByTarget[review.target_role] = [];
        }
        reviewsByTarget[review.target_role].push(review);
    }
    
    for (const [target, targetReviews] of Object.entries(reviewsByTarget)) {
        const card = document.createElement('div');
        card.className = 'review-card';
        
        const avgScore = weightedScores ? weightedScores[target] : 
            targetReviews.reduce((sum, r) => sum + (r.weighted_score || 0), 0) / targetReviews.length;
        
        card.innerHTML = `
            <div class="review-header">
                <h4>${getRoleIcon(target)} ${getRoleName(target)}</h4>
                <span class="review-score">${avgScore.toFixed(1)}/10</span>
            </div>
            <div class="scores-grid">
                ${targetReviews.map(r => `
                    <div class="score-item">
                        <span class="score-label">From ${getRoleName(r.reviewer_role)}</span>
                        <span class="score-value">${r.weighted_score?.toFixed(1) || 'N/A'}</span>
                    </div>
                `).join('')}
            </div>
            ${targetReviews.some(r => r.feedback) ? `
                <div class="review-feedback">
                    <strong>Feedback:</strong><br>
                    ${targetReviews.map(r => r.feedback).filter(f => f).join('<br><br>')}
                </div>
            ` : ''}
        `;
        container.appendChild(card);
    }
}

/**
 * Display improved responses
 */
function displayImprovedResponses(responses) {
    const grid = document.getElementById('improved-grid');
    grid.innerHTML = '';
    
    if (!responses || Object.keys(responses).length === 0) {
        grid.innerHTML = '<p class="text-muted">No improved responses available</p>';
        return;
    }
    
    for (const [role, response] of Object.entries(responses)) {
        const card = document.createElement('div');
        card.className = 'response-card';
        card.innerHTML = `
            <h4>${getRoleIcon(role)} ${response.role_name} (Improved)</h4>
            <div class="response-text">${formatText(response.improved_response)}</div>
        `;
        grid.appendChild(card);
    }
}

/**
 * Display verification report
 */
function displayVerification(report) {
    const container = document.getElementById('verification-report');
    
    if (!report) {
        container.innerHTML = '<p class="text-muted">No verification report available</p>';
        return;
    }
    
    const scoreClass = report.overall_reliability_score >= 80 ? '' :
        report.overall_reliability_score >= 60 ? 'warning' : 'error';
    
    container.innerHTML = `
        <div class="verification-header">
            <div>
                <h3>Verification Report</h3>
                <p class="text-muted">Confidence: ${report.confidence_assessment}</p>
            </div>
            <div class="reliability-score ${scoreClass}">
                ${report.overall_reliability_score.toFixed(0)}%
            </div>
        </div>
        <div class="verification-content">
            <div class="verification-section">
                <h4>Hallucination Flags</h4>
                ${report.hallucination_flags.length > 0 ? `
                    <ul class="issue-list">
                        ${report.hallucination_flags.map(f => `<li>${formatText(f)}</li>`).join('')}
                    </ul>
                ` : '<p class="no-issues">No hallucinations detected</p>'}
            </div>
            
            <div class="verification-section">
                <h4>Factual Errors</h4>
                ${report.factual_errors.length > 0 ? `
                    <ul class="issue-list">
                        ${report.factual_errors.map(f => `<li>${formatText(f)}</li>`).join('')}
                    </ul>
                ` : '<p class="no-issues">No factual errors detected</p>'}
            </div>
            
            <div class="verification-section">
                <h4>Logical Inconsistencies</h4>
                ${report.logical_inconsistencies.length > 0 ? `
                    <ul class="issue-list">
                        ${report.logical_inconsistencies.map(f => `<li>${formatText(f)}</li>`).join('')}
                    </ul>
                ` : '<p class="no-issues">No logical inconsistencies detected</p>'}
            </div>
            
            ${report.recommendations.length > 0 ? `
                <div class="verification-section">
                    <h4>Recommendations</h4>
                    <ul>
                        ${report.recommendations.map(r => `<li>${formatText(r)}</li>`).join('')}
                    </ul>
                </div>
            ` : `
                <div class="verification-section">
                    <h4>Recommendations</h4>
                    <p class="no-issues">No recommendations</p>
                </div>
            `}
        </div>
    `;
}

/**
 * Display reasoning trace
 */
function displayReasoningTrace(trace) {
    const container = document.getElementById('reasoning-trace');
    
    if (!trace || trace.length === 0) {
        container.innerHTML = '<p class="text-muted">No reasoning trace available</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="trace-timeline">
            ${trace.map(step => `
                <div class="trace-step">
                    <div class="step-marker">${step.step}</div>
                    <div class="step-info">
                        <strong>${step.stage}</strong>
                        <pre>${JSON.stringify(step.data, null, 2)}</pre>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Show error message
 */
function showError(message) {
    document.getElementById('progress-status').textContent = `Error: ${message}`;
    document.getElementById('progress-status').style.color = '#ef4444';
}

/**
 * Reset form for new deliberation
 */
function resetForm() {
    document.getElementById('query').value = '';
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('progress-status').style.color = '';
    
    // Reset progress stages
    document.querySelectorAll('.stage').forEach(s => {
        s.classList.remove('active', 'complete');
    });
    document.getElementById('progress-fill').style.width = '0%';
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

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

// Helper functions from main.js
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
