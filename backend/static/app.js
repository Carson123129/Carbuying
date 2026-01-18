// State management
let state = {
    query: '',
    results: null,
    isLoading: false,
    expandedCardId: null
};

// DOM Elements
const heroSection = document.getElementById('heroSection');
const resultsSection = document.getElementById('resultsSection');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resetBtn = document.getElementById('resetBtn');
const intentSummary = document.getElementById('intentSummary');
const refinementBar = document.getElementById('refinementBar');
const carResults = document.getElementById('carResults');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const fallbackBanner = document.getElementById('fallbackBanner');

// Initialize
if (fallbackBanner) {
    fallbackBanner.classList.add('hidden');
}
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSearch(e);
    }
});

// Search functionality
async function handleSearch(event) {
    event.preventDefault();
    const query = searchInput.value.trim();
    if (!query || state.isLoading) return;

    state.query = query;
    setLoading(true);
    hideError();

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        if (!response.ok) throw new Error('Search failed');

        const data = await response.json();
        state.results = data;
        renderResults();
    } catch (err) {
        showError('Something went wrong. Make sure the backend is running.');
    } finally {
        setLoading(false);
    }
}

// Try example queries
function tryExample(query) {
    searchInput.value = query;
    handleSearch(new Event('submit'));
}

// Refinement
async function handleRefine(refinement) {
    if (!state.results || state.isLoading) return;

    setLoading(true);
    hideError();

    try {
        const response = await fetch('/api/refine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_query: state.query,
                previous_intent: state.results.interpreted_intent,
                refinement
            })
        });

        if (!response.ok) throw new Error('Refinement failed');

        const data = await response.json();
        state.results = data;
        renderResults();
    } catch (err) {
        showError('Refinement failed. Please try again.');
    } finally {
        setLoading(false);
    }
}

// Reset search
function resetSearch() {
    state = {
        query: '',
        results: null,
        isLoading: false,
        expandedCardId: null
    };
    searchInput.value = '';
    heroSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    resetBtn.classList.add('hidden');
    hideError();
    searchInput.focus();
}

// Toggle card expansion
function toggleCard(carId) {
    state.expandedCardId = state.expandedCardId === carId ? null : carId;
    renderCarCards();
}

// Loading state
function setLoading(loading) {
    state.isLoading = loading;
    searchBtn.disabled = loading;
    searchBtn.classList.toggle('loading', loading);
    
    document.querySelectorAll('.refinement-chip').forEach(chip => {
        chip.disabled = loading;
    });
}

// Error handling
function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

// Render functions
function renderResults() {
    heroSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    resetBtn.classList.remove('hidden');

    renderIntentSummary();
    renderRefinementBar();
    renderCarCards();
}

function renderIntentSummary() {
    const { intent_summary, interpreted_intent: intent } = state.results;
    
    let tagsHtml = '';
    
    if (intent.budget_max) {
        tagsHtml += `<span class="intent-tag budget"><span class="tag-icon">$</span>Under $${intent.budget_max.toLocaleString()}</span>`;
    }
    
    if (intent.drivetrain) {
        tagsHtml += `<span class="intent-tag drivetrain"><span class="tag-icon">◎</span>${intent.drivetrain}</span>`;
    }
    
    if (intent.performance_priority > 0.6) {
        tagsHtml += `<span class="intent-tag performance"><span class="tag-icon">⚡</span>Performance focused</span>`;
    }
    
    if (intent.reliability_priority > 0.6) {
        tagsHtml += `<span class="intent-tag reliability"><span class="tag-icon">✓</span>Reliability matters</span>`;
    }
    
    if (intent.body_style) {
        tagsHtml += `<span class="intent-tag body"><span class="tag-icon">◇</span>${intent.body_style}</span>`;
    }
    
    if (intent.emotional_tags) {
        intent.emotional_tags.slice(0, 3).forEach(tag => {
            tagsHtml += `<span class="intent-tag emotion">${tag}</span>`;
        });
    }
    
    if (intent.reference_car) {
        tagsHtml += `<span class="intent-tag reference"><span class="tag-icon">≈</span>Like ${intent.reference_car}</span>`;
    }

    intentSummary.innerHTML = `
        <div class="intent-header">
            <span class="intent-icon">✦</span>
            <span class="intent-label">We understood:</span>
        </div>
        <p class="intent-text">${intent_summary}</p>
        <div class="intent-details">${tagsHtml}</div>
    `;
}

function renderRefinementBar() {
    const { suggestions } = state.results;
    
    if (!suggestions || suggestions.length === 0) {
        refinementBar.innerHTML = '';
        return;
    }

    const chipsHtml = suggestions.map(s => 
        `<button class="refinement-chip" onclick="handleRefine('${s}')" ${state.isLoading ? 'disabled' : ''}>${s}</button>`
    ).join('');

    refinementBar.innerHTML = `
        <span class="refinement-label">Refine:</span>
        <div class="refinement-chips">${chipsHtml}</div>
    `;
}

function renderCarCards() {
    const { matches } = state.results;

    if (!matches || matches.length === 0) {
        carResults.innerHTML = `
            <div class="results-header">
                <h2>No matches found</h2>
            </div>
            <p style="color: var(--text-tertiary);">Try a different search.</p>
        `;
        return;
    }

    const cardsHtml = matches.map((match, index) => renderCarCard(match, index + 1)).join('');

    carResults.innerHTML = `
        <div class="results-header">
            <h2><span class="results-count">${matches.length}</span> cars match your criteria</h2>
        </div>
        <div class="results-list">${cardsHtml}</div>
    `;
}

function renderCarCard(match, rank) {
    const { car, match_score, match_reasons, tradeoffs, listings } = match;
    const isExpanded = state.expandedCardId === car.id;
    const scoreClass = getScoreClass(match_score);

    const reasonsHtml = match_reasons.slice(0, 2).map(r => 
        `<span class="reason-tag"><span class="reason-icon">✓</span>${r}</span>`
    ).join('');

    let detailsHtml = '';
    if (isExpanded) {
        detailsHtml = renderCarDetails(car, tradeoffs, listings);
    }

    return `
        <div class="car-card ${isExpanded ? 'expanded' : ''}" style="animation-delay: ${rank * 50}ms">
            <div class="car-card-main" onclick="toggleCard('${car.id}')">
                <div class="car-rank">#${rank}</div>
                
                <div class="car-info">
                    <div class="car-title-row">
                        <h3 class="car-title">
                            ${car.year} ${car.make} ${car.model}
                            <span class="car-trim">${car.trim}</span>
                        </h3>
                    </div>
                    
                    <div class="car-specs">
                        <span class="spec"><span class="spec-value">${car.power_hp}</span><span class="spec-label">hp</span></span>
                        <span class="spec-divider">·</span>
                        <span class="spec"><span class="spec-value">${car.zero_to_sixty}s</span><span class="spec-label">0-60</span></span>
                        <span class="spec-divider">·</span>
                        <span class="spec"><span class="spec-value">${car.drivetrain}</span></span>
                        <span class="spec-divider">·</span>
                        <span class="spec price">~${formatPrice(car.avg_price)}</span>
                    </div>

                    <div class="car-reasons">${reasonsHtml}</div>
                </div>

                <div class="car-score-area">
                    <div class="score-circle ${scoreClass}">
                        <span class="score-value">${Math.round(match_score)}</span>
                        <span class="score-label">match</span>
                    </div>
                    <button class="expand-btn" onclick="event.stopPropagation(); toggleCard('${car.id}')">
                        <span class="expand-icon ${isExpanded ? 'rotated' : ''}">▾</span>
                    </button>
                </div>
            </div>
            ${detailsHtml}
        </div>
    `;
}

function renderCarDetails(car, tradeoffs, listings) {
    const charTagsHtml = car.emotional_tags.map(t => `<span class="char-tag">${t}</span>`).join('');
    const feelTagsHtml = car.driving_feel_tags.map(t => `<span class="feel-tag">${t}</span>`).join('');
    
    let tradeoffsHtml = '';
    if (tradeoffs && tradeoffs.length > 0) {
        const tradeoffItems = tradeoffs.map(t => `<li>${t}</li>`).join('');
        tradeoffsHtml = `
            <div class="details-section tradeoffs">
                <h4>Tradeoffs</h4>
                <ul class="tradeoffs-list">${tradeoffItems}</ul>
            </div>
        `;
    }

    let listingsHtml = '';
    if (listings && listings.length > 0) {
        const listingCards = listings.map(l => `
            <a href="${l.url}" target="_blank" rel="noopener noreferrer" class="listing-card">
                <div class="listing-price">${formatPrice(l.price)}</div>
                <div class="listing-details">
                    <span class="listing-mileage">${l.mileage.toLocaleString()} mi</span>
                    <span class="listing-divider">·</span>
                    <span class="listing-location">${l.location}</span>
                </div>
                <div class="listing-condition">${l.condition}</div>
                <div class="listing-source">${l.source} →</div>
            </a>
        `).join('');

        listingsHtml = `
            <div class="listings-section">
                <h4>Available Listings</h4>
                <div class="listings-grid">${listingCards}</div>
            </div>
        `;
    }

    return `
        <div class="car-card-details">
            <div class="details-grid">
                <div class="details-section">
                    <h4>Full Specs</h4>
                    <div class="specs-grid">
                        <div class="spec-item"><span class="spec-name">Power</span><span class="spec-val">${car.power_hp} hp</span></div>
                        <div class="spec-item"><span class="spec-name">Torque</span><span class="spec-val">${car.torque_lb_ft} lb-ft</span></div>
                        <div class="spec-item"><span class="spec-name">0-60 mph</span><span class="spec-val">${car.zero_to_sixty}s</span></div>
                        <div class="spec-item"><span class="spec-name">Drivetrain</span><span class="spec-val">${car.drivetrain}</span></div>
                        <div class="spec-item"><span class="spec-name">Body</span><span class="spec-val">${car.body_type}</span></div>
                        <div class="spec-item"><span class="spec-name">MPG</span><span class="spec-val">${car.fuel_economy_mpg}</span></div>
                        <div class="spec-item"><span class="spec-name">Reliability</span><span class="spec-val">${car.reliability_score}/10</span></div>
                        <div class="spec-item"><span class="spec-name">Ownership Cost</span><span class="spec-val">${car.ownership_cost_score}/10</span></div>
                    </div>
                </div>

                <div class="details-section">
                    <h4>Character</h4>
                    <div class="tags-container">
                        ${charTagsHtml}
                        ${feelTagsHtml}
                    </div>
                </div>

                ${tradeoffsHtml}
            </div>
            ${listingsHtml}
        </div>
    `;
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
    }).format(price);
}

function getScoreClass(score) {
    if (score >= 85) return 'excellent';
    if (score >= 75) return 'great';
    if (score >= 65) return 'good';
    if (score >= 50) return 'fair';
    return 'low';
}

// Focus search input on page load
window.addEventListener('load', () => {
    searchInput.focus();
});

