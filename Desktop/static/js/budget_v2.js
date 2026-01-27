/**
 * Budget Management V2 - Subcategory Budgets, Commitments & Recommendations
 * Handles all budget-related functionality for the personal finance dashboard
 */

// Global state management
const budgetState = {
    subcategoryBudgets: [],
    commitments: [],
    unexpectedExpenses: [],
    recommendations: [],
    selectedRecommendations: new Set(),
    currentYear: window.SELECTED_YEAR || new Date().getFullYear(),
    currentMonth: window.SELECTED_MONTH || (new Date().getMonth() + 1),
    collapsedCategories: new Set(JSON.parse(localStorage.getItem('budgetCollapsedCategories') || '[]'))
};

// Save collapsed state to localStorage
function saveCollapsedState() {
    localStorage.setItem('budgetCollapsedCategories', JSON.stringify([...budgetState.collapsedCategories]));
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Budget V2 initialized');
    loadAllData();

    // Setup tab change listeners
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            if (target === '#commitments') {
                loadCommitments();
            } else if (target === '#unexpected') {
                loadUnexpectedExpenses();
            }
        });
    });
});

// ============================================================================
// SUBCATEGORY BUDGETS
// ============================================================================

async function loadSubcategoryBudgets() {
    console.log('Loading subcategory budgets...');

    try {
        const response = await fetch('/budget/api/subcategory_templates');
        const budgets = await response.json();

        // Budgets now include commitment_minimum from backend
        budgetState.subcategoryBudgets = budgets;

        console.log(`✅ Loaded ${budgets.length} budgets (with commitment minimums enforced)`);

        renderSubcategoryBudgets(budgets);
        updateSummaryCards();

    } catch (error) {
        console.error('Error loading subcategory budgets:', error);
        alert('Failed to load subcategory budgets');
    }
}

async function syncSubcategoryTemplates() {
    if (!confirm('Sync budget categories with current transactions? This will add any new category/subcategory pairs from your transactions.')) {
        return;
    }

    try {
        const response = await fetch('/budget/api/subcategory_templates/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            await loadSubcategoryBudgets();
        } else {
            throw new Error(data.error || 'Failed to sync categories');
        }
    } catch (error) {
        console.error('Error syncing categories:', error);
        alert('Failed to sync categories: ' + error.message);
    }
}

async function quickSetupBudgets() {
    if (!confirm('Quick Setup will automatically apply AI recommendations to ALL subcategories and save them. Continue?')) {
        return;
    }

    try {
        // Show loading indicator
        const loadingMsg = document.createElement('div');
        loadingMsg.innerHTML = `
            <div class="alert alert-info position-fixed top-50 start-50 translate-middle" style="z-index: 9999;">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Setting up budgets... This may take a moment.
            </div>
        `;
        document.body.appendChild(loadingMsg);

        // Fetch recommendations
        const recResponse = await fetch('/budget/api/recommend_budgets?owner=all');
        const recData = await recResponse.json();

        if (!recData.success) {
            throw new Error(recData.error || 'Failed to fetch recommendations');
        }

        const recommendations = recData.recommendations;

        // Apply all recommendations to state
        for (const rec of recommendations) {
            const budget = budgetState.subcategoryBudgets.find(
                b => b.category === rec.category && b.sub_category === rec.sub_category
            );

            if (budget) {
                budget.budget_amount = rec.recommended_budget;
            }
        }

        // Save all budgets
        const updates = budgetState.subcategoryBudgets
            .filter(b => b.is_active !== false)
            .map(b => ({
                category: b.category,
                sub_category: b.sub_category,
                budget_amount: b.budget_amount,
                notes: b.notes || '',
                budget_by_category: b.budget_by_category || false,
                is_active: true
            }));

        const saveResponse = await fetch('/budget/api/subcategory_templates/batch_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budgets: updates })
        });

        const saveData = await saveResponse.json();

        // Remove loading indicator
        document.body.removeChild(loadingMsg);

        if (saveData.success) {
            alert(`✅ Quick Setup Complete!\n\n${recommendations.length} budgets set based on AI recommendations.`);
            await loadSubcategoryBudgets();
            updateSummaryCards();
        } else {
            throw new Error(saveData.error || 'Failed to save budgets');
        }

    } catch (error) {
        // Remove loading indicator if it exists
        const loadingMsg = document.querySelector('.alert-info');
        if (loadingMsg) {
            document.body.removeChild(loadingMsg.parentElement);
        }

        console.error('Error in quick setup:', error);
        alert('Quick setup failed: ' + error.message);
    }
}

function renderSubcategoryBudgets(budgets) {
    const container = document.getElementById('subcategoryBudgetContainer');
    const loading = document.getElementById('subcategoryLoadingMessage');

    if (!budgets || budgets.length === 0) {
        loading.style.display = 'none';
        container.innerHTML = `
            <div class="text-center py-5">
                <p class="text-muted">No subcategory budgets found. Click "Recommend Budgets" to get started!</p>
            </div>
        `;
        container.style.display = 'block';
        return;
    }

    // Filter active budgets only
    const activeBudgets = budgets.filter(b => b.is_active !== false);
    const inactiveBudgets = budgets.filter(b => b.is_active === false);

    // Group budgets by category
    const groupedBudgets = activeBudgets.reduce((acc, budget) => {
        if (!acc[budget.category]) {
            acc[budget.category] = [];
        }
        acc[budget.category].push(budget);
        return acc;
    }, {});

    let html = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <button class="btn btn-sm btn-outline-secondary" onclick="toggleShowHiddenBudgets()">
                    <span id="showHiddenButtonText">Show Hidden (${inactiveBudgets.length})</span>
                </button>
            </div>
        </div>
    `;

    for (const [category, categoryBudgets] of Object.entries(groupedBudgets)) {
        const categoryTotal = categoryBudgets.reduce((sum, b) => sum + b.budget_amount, 0);
        const budgetByCategory = categoryBudgets[0]?.budget_by_category || false;
        const toggleId = `toggle-${category.replace(/\s+/g, '-')}`;
        const collapseId = `collapse-${category.replace(/\s+/g, '-')}`;

        // Check if this category should be collapsed (from saved state or default for category-level budgeting)
        const isCollapsed = budgetState.collapsedCategories.has(category) || budgetByCategory;

        html += `
            <div class="subcategory-group border rounded mb-3 p-3" data-category-name="${category}">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="d-flex align-items-center">
                        <button class="btn btn-sm btn-link text-decoration-none p-0 me-2"
                                type="button"
                                data-bs-toggle="collapse"
                                data-bs-target="#${collapseId}"
                                aria-expanded="${!isCollapsed}"
                                aria-controls="${collapseId}"
                                data-category="${category}"
                                title="Expand/Collapse category">
                            <span class="collapse-icon">▼</span>
                        </button>
                        <h6 class="mb-0 d-inline">${category}</h6>
                        <small class="text-muted ms-2 category-total">Total: $${categoryTotal.toFixed(2)}</small>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <button class="btn btn-sm btn-outline-danger"
                                onclick="hideBudgetCategory('${category}')"
                                title="Hide this category from budget view">
                            Hide
                        </button>
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="${toggleId}"
                                   ${budgetByCategory ? 'checked' : ''}
                                   onchange="toggleCategoryGranularity('${category}', this.checked)">
                            <label class="form-check-label" for="${toggleId}" title="Toggle between category-level and subcategory-level budgeting">
                                <small>Budget by Category</small>
                            </label>
                        </div>
                    </div>
                </div>
                ${budgetByCategory ? `
                    <div class="alert alert-info py-2 mb-2">
                        <small>
                            <strong>Category-level budgeting:</strong> Set one budget for all "${category}" expenses.
                            Subcategories are tracked for analysis only.
                        </small>
                    </div>
                    <div class="subcategory-row">
                        <div class="row align-items-center">
                            <div class="col-md-4">
                                <strong>Category Budget</strong>
                            </div>
                            <div class="col-md-3">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text">$</span>
                                    <input type="number" class="form-control" step="0.01" min="0"
                                           value="${categoryTotal}"
                                           data-category="${category}"
                                           data-is-category-level="true"
                                           onchange="updateCategoryLevelBudget(this)">
                                </div>
                            </div>
                            <div class="col-md-4">
                                <small class="text-muted">Applied to all subcategories below</small>
                            </div>
                            <div class="col-md-1">
                                <button class="btn btn-sm btn-outline-success"
                                        onclick="saveCategoryLevelBudget('${category}')">
                                    💾
                                </button>
                            </div>
                        </div>
                    </div>
                ` : ''}
                <div class="collapse ${!isCollapsed ? 'show' : ''}" id="${collapseId}">
                    ${budgetByCategory ? '<hr><div class="mb-2"><small class="text-muted"><strong>Subcategories (for tracking only):</strong></small></div>' : ''}
                    ${categoryBudgets.map((budget, idx) => `
                        <div class="subcategory-row ${budgetByCategory ? 'opacity-75' : ''}">
                            <div class="row align-items-center">
                                <div class="col-md-3">
                                    <strong>${budget.sub_category}</strong>
                                </div>
                                <div class="col-md-2">
                                    <div class="input-group input-group-sm">
                                        <span class="input-group-text">$</span>
                                        <input type="number" class="form-control" step="0.01"
                                               min="${budget.commitment_minimum || 0}"
                                               value="${budget.budget_amount}"
                                               data-category="${budget.category}"
                                               data-subcategory="${budget.sub_category}"
                                               data-commitment-minimum="${budget.commitment_minimum || 0}"
                                               ${budgetByCategory ? 'readonly' : ''}
                                               onchange="updateSubcategoryBudgetInState(this)"
                                               title="${budget.commitment_minimum > 0 ? 'Minimum: $' + budget.commitment_minimum.toFixed(2) + ' (based on commitments)' : 'No minimum'}">
                                    </div>
                                    ${budget.commitment_minimum > 0 ? `<small class="text-muted">Min: $${budget.commitment_minimum.toFixed(2)}</small>` : ''}
                                </div>
                                <div class="col-md-4">
                                    <input type="text" class="form-control form-control-sm"
                                           placeholder="Notes..."
                                           value="${budget.notes || ''}"
                                           data-category="${budget.category}"
                                           data-subcategory="${budget.sub_category}"
                                           onchange="updateSubcategoryNoteInState(this)">
                                </div>
                                <div class="col-md-3 d-flex gap-1">
                                    ${!budgetByCategory ? `
                                        <button class="btn btn-sm btn-outline-success"
                                                onclick="saveSubcategoryBudget('${budget.category}', '${budget.sub_category}')">
                                            💾
                                        </button>
                                    ` : ''}
                                    <button class="btn btn-sm btn-outline-secondary"
                                            onclick="hideBudgetSubcategory('${budget.category}', '${budget.sub_category}')"
                                            title="Hide this subcategory">
                                        Hide
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
    loading.style.display = 'none';
    container.style.display = 'block';

    // Add event listeners to track collapse/expand state
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(button => {
        const category = button.dataset.category;
        if (!category) return;

        const collapseId = button.getAttribute('data-bs-target').substring(1);
        const collapseElement = document.getElementById(collapseId);

        if (collapseElement) {
            collapseElement.addEventListener('hide.bs.collapse', () => {
                budgetState.collapsedCategories.add(category);
                saveCollapsedState();
            });

            collapseElement.addEventListener('show.bs.collapse', () => {
                budgetState.collapsedCategories.delete(category);
                saveCollapsedState();
            });
        }
    });
}

function updateSubcategoryBudgetInState(input) {
    const category = input.dataset.category;
    const subcategory = input.dataset.subcategory;
    let value = parseFloat(input.value) || 0;
    const commitmentMinimum = parseFloat(input.dataset.commitmentMinimum) || 0;

    // Enforce minimum based on commitments
    if (value < commitmentMinimum) {
        showToast(`Budget cannot be less than commitment total ($${commitmentMinimum.toFixed(2)})`, 'error');
        value = commitmentMinimum;
        input.value = commitmentMinimum.toFixed(2);
    }

    const budget = budgetState.subcategoryBudgets.find(
        b => b.category === category && b.sub_category === subcategory
    );

    if (budget) {
        budget.budget_amount = value;
        updateSummaryCards();
        updateCategoryTotal(category);
    }
}

function updateCategoryTotal(category) {
    // Calculate new total for the category
    const categoryBudgets = budgetState.subcategoryBudgets.filter(
        b => b.category === category && b.is_active !== false
    );
    const total = categoryBudgets.reduce((sum, b) => sum + parseFloat(b.budget_amount || 0), 0);

    // Find and update the total display in the DOM
    const categoryElement = document.querySelector(`[data-category-name="${category}"]`);
    if (categoryElement) {
        const totalElement = categoryElement.querySelector('.category-total');
        if (totalElement) {
            totalElement.textContent = `Total: $${total.toFixed(2)}`;
        }
    }
}

function updateSubcategoryNoteInState(input) {
    const category = input.dataset.category;
    const subcategory = input.dataset.subcategory;
    const value = input.value;

    const budget = budgetState.subcategoryBudgets.find(
        b => b.category === category && b.sub_category === subcategory
    );

    if (budget) {
        budget.notes = value;
    }
}

async function saveSubcategoryBudget(category, subcategory) {
    const budget = budgetState.subcategoryBudgets.find(
        b => b.category === category && b.sub_category === subcategory
    );

    if (!budget) {
        alert('Budget not found');
        return;
    }

    try {
        const response = await fetch('/budget/api/subcategory_templates/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: budget.category,
                sub_category: budget.sub_category,
                budget_amount: budget.budget_amount,
                notes: budget.notes || ''
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showToast('Budget saved successfully', 'success');
        } else {
            // Handle validation errors (e.g., budget below commitment minimum)
            if (result.error && result.minimum_budget !== undefined) {
                // Budget validation error with minimum budget info
                alert(`❌ ${result.error}\n\nMinimum required: $${result.minimum_budget.toFixed(2)}`);
                // Optionally restore the input to the minimum value
                const input = document.querySelector(`input[data-category="${category}"][data-subcategory="${subcategory}"]`);
                if (input) {
                    input.value = result.minimum_budget.toFixed(2);
                    budget.budget_amount = result.minimum_budget;
                }
            } else {
                throw new Error(result.error || 'Failed to save budget');
            }
        }
    } catch (error) {
        console.error('Error saving budget:', error);
        alert('Failed to save budget: ' + error.message);
    }
}

async function saveAllSubcategoryBudgets() {
    if (budgetState.subcategoryBudgets.length === 0) {
        alert('No budgets to save');
        return;
    }

    try {
        const response = await fetch('/budget/api/subcategory_templates/batch_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                budgets: budgetState.subcategoryBudgets
            })
        });

        const result = await response.json();

        if (result.success) {
            showToast('All budgets saved successfully!', 'success');
        } else {
            throw new Error(result.error || 'Failed to save budgets');
        }
    } catch (error) {
        console.error('Error saving all budgets:', error);
        alert('Failed to save budgets: ' + error.message);
    }
}

// Hide a subcategory from budget view
async function hideBudgetSubcategory(category, subCategory) {
    if (!confirm(`Hide "${subCategory}" from budget view? You can restore it later from "Show Hidden" section.`)) {
        return;
    }

    try {
        // Find the budget to get current values
        const budget = budgetState.subcategoryBudgets.find(
            b => b.category === category && b.sub_category === subCategory
        );

        if (!budget) {
            throw new Error('Budget not found');
        }

        const response = await fetch('/budget/api/subcategory_templates/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: category,
                sub_category: subCategory,
                budget_amount: budget.budget_amount,
                notes: budget.notes || '',
                budget_by_category: budget.budget_by_category || false,
                is_active: false
            })
        });

        const data = await response.json();

        if (data.success) {
            await loadSubcategoryBudgets();
        } else {
            throw new Error(data.error || 'Failed to hide subcategory');
        }
    } catch (error) {
        console.error('Error hiding subcategory:', error);
        alert('Failed to hide subcategory: ' + error.message);
    }
}

// Hide entire category from budget view
async function hideBudgetCategory(category) {
    if (!confirm(`Hide entire "${category}" category from budget view? You can restore it later from "Show Hidden" section.`)) {
        return;
    }

    try {
        // Get all subcategories for this category
        const subcategories = budgetState.subcategoryBudgets.filter(b => b.category === category);

        // Hide all subcategories
        const promises = subcategories.map(sub =>
            fetch('/budget/api/subcategory_templates/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: sub.category,
                    sub_category: sub.sub_category,
                    budget_amount: sub.budget_amount,
                    notes: sub.notes || '',
                    budget_by_category: sub.budget_by_category || false,
                    is_active: false
                })
            })
        );

        const responses = await Promise.all(promises);
        const results = await Promise.all(responses.map(r => r.json()));

        const failed = results.filter(r => !r.success);
        if (failed.length > 0) {
            throw new Error(`Failed to hide ${failed.length} subcategories`);
        }

        await loadSubcategoryBudgets();

    } catch (error) {
        console.error('Error hiding category:', error);
        alert('Failed to hide category: ' + error.message);
    }
}

// Toggle showing hidden budgets
function toggleShowHiddenBudgets() {
    const modal = new bootstrap.Modal(document.getElementById('hiddenBudgetsModal') || createHiddenBudgetsModal());
    renderHiddenBudgets();
    modal.show();
}

// Create modal for hidden budgets if it doesn't exist
function createHiddenBudgetsModal() {
    const modalHtml = `
        <div class="modal fade" id="hiddenBudgetsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Hidden Budget Items</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="hiddenBudgetsContent">
                        <!-- Content will be rendered here -->
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    return document.getElementById('hiddenBudgetsModal');
}

// Render hidden budgets list
function renderHiddenBudgets() {
    const container = document.getElementById('hiddenBudgetsContent');
    const hiddenBudgets = budgetState.subcategoryBudgets.filter(b => b.is_active === false);

    if (hiddenBudgets.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-4">No hidden budget items</p>';
        return;
    }

    // Group by category
    const grouped = hiddenBudgets.reduce((acc, budget) => {
        if (!acc[budget.category]) {
            acc[budget.category] = [];
        }
        acc[budget.category].push(budget);
        return acc;
    }, {});

    let html = '<div class="list-group">';
    for (const [category, items] of Object.entries(grouped)) {
        html += `<div class="list-group-item">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>${category}</strong>
                <button class="btn btn-sm btn-success" onclick="restoreBudgetCategory('${category}')">
                    Restore All
                </button>
            </div>
            <ul class="list-unstyled ms-3">
                ${items.map(item => `
                    <li class="d-flex justify-content-between align-items-center py-1">
                        <span>${item.sub_category}</span>
                        <button class="btn btn-sm btn-outline-success" onclick="restoreBudgetSubcategory('${item.category}', '${item.sub_category}')">
                            Restore
                        </button>
                    </li>
                `).join('')}
            </ul>
        </div>`;
    }
    html += '</div>';

    container.innerHTML = html;
}

// Restore a hidden subcategory
async function restoreBudgetSubcategory(category, subCategory) {
    try {
        // Find the budget to get current values
        const budget = budgetState.subcategoryBudgets.find(
            b => b.category === category && b.sub_category === subCategory
        );

        if (!budget) {
            throw new Error('Budget not found');
        }

        const response = await fetch('/budget/api/subcategory_templates/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: category,
                sub_category: subCategory,
                budget_amount: budget.budget_amount,
                notes: budget.notes || '',
                budget_by_category: budget.budget_by_category || false,
                is_active: true
            })
        });

        const data = await response.json();

        if (data.success) {
            await loadSubcategoryBudgets();
            renderHiddenBudgets();
        } else {
            throw new Error(data.error || 'Failed to restore subcategory');
        }
    } catch (error) {
        console.error('Error restoring subcategory:', error);
        alert('Failed to restore subcategory: ' + error.message);
    }
}

// Restore entire category
async function restoreBudgetCategory(category) {
    try {
        const subcategories = budgetState.subcategoryBudgets.filter(
            b => b.category === category && b.is_active === false
        );

        const promises = subcategories.map(sub =>
            fetch('/budget/api/subcategory_templates/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: sub.category,
                    sub_category: sub.sub_category,
                    budget_amount: sub.budget_amount,
                    notes: sub.notes || '',
                    budget_by_category: sub.budget_by_category || false,
                    is_active: true
                })
            })
        );

        const responses = await Promise.all(promises);
        const results = await Promise.all(responses.map(r => r.json()));

        const failed = results.filter(r => !r.success);
        if (failed.length > 0) {
            throw new Error(`Failed to restore ${failed.length} subcategories`);
        }

        await loadSubcategoryBudgets();
        renderHiddenBudgets();

    } catch (error) {
        console.error('Error restoring category:', error);
        alert('Failed to restore category: ' + error.message);
    }
}

// Toggle between category-level and subcategory-level budgeting
async function toggleCategoryGranularity(category, budgetByCategory) {
    try {
        const response = await fetch('/budget/api/subcategory_templates/toggle_granularity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: category,
                budget_by_category: budgetByCategory
            })
        });

        const data = await response.json();

        if (data.success) {
            // Refresh the budgets to reflect the change
            await loadSubcategoryBudgets();
        } else {
            throw new Error(data.error || 'Failed to toggle granularity');
        }
    } catch (error) {
        console.error('Error toggling granularity:', error);
        alert('Failed to toggle budget granularity: ' + error.message);
        // Reload to reset the toggle state
        await loadSubcategoryBudgets();
    }
}

// Update category-level budget amount in state
function updateCategoryLevelBudget(input) {
    const category = input.dataset.category;
    const amount = parseFloat(input.value) || 0;

    // Store the category-level budget amount
    if (!budgetState.categoryBudgets) {
        budgetState.categoryBudgets = {};
    }
    budgetState.categoryBudgets[category] = amount;
}

// Save category-level budget and distribute across subcategories
async function saveCategoryLevelBudget(category) {
    try {
        const categoryBudget = budgetState.categoryBudgets?.[category] || 0;

        if (categoryBudget < 0) {
            alert('Budget amount cannot be negative');
            return;
        }

        // Get all subcategories for this category
        const subcategories = budgetState.subcategoryBudgets.filter(b => b.category === category);

        if (subcategories.length === 0) {
            alert('No subcategories found for this category');
            return;
        }

        // Calculate total current spending to determine proportional distribution
        // If all subcategories have 0 budget, distribute equally
        const totalExistingBudget = subcategories.reduce((sum, sub) => sum + parseFloat(sub.budget_amount || 0), 0);

        const updates = [];

        if (totalExistingBudget === 0) {
            // Equal distribution
            const amountPerSub = categoryBudget / subcategories.length;
            for (const sub of subcategories) {
                updates.push({
                    category: sub.category,
                    sub_category: sub.sub_category,
                    budget_amount: amountPerSub,
                    notes: sub.notes || '',
                    budget_by_category: true
                });
            }
        } else {
            // Proportional distribution based on existing budgets
            for (const sub of subcategories) {
                const proportion = parseFloat(sub.budget_amount || 0) / totalExistingBudget;
                const newAmount = categoryBudget * proportion;
                updates.push({
                    category: sub.category,
                    sub_category: sub.sub_category,
                    budget_amount: newAmount,
                    notes: sub.notes || '',
                    budget_by_category: true
                });
            }
        }

        // Save all updates
        const promises = updates.map(update =>
            fetch('/budget/api/subcategory_templates/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(update)
            })
        );

        const responses = await Promise.all(promises);
        const results = await Promise.all(responses.map(async (r, i) => {
            const json = await r.json();
            return { ok: r.ok, data: json, subcategory: updates[i].sub_category };
        }));

        const failed = results.filter(r => !r.ok);
        if (failed.length > 0) {
            // Check if any failures were due to commitment validation
            const validationErrors = failed.filter(r => r.data.minimum_budget !== undefined);
            if (validationErrors.length > 0) {
                const errorMessages = validationErrors.map(r =>
                    `  • ${r.subcategory}: Min $${r.data.minimum_budget.toFixed(2)}`
                ).join('\n');
                alert(`❌ Cannot set category budget below commitment minimums:\n\n${errorMessages}\n\nPlease increase the category budget or adjust commitments.`);
            } else {
                throw new Error(`Failed to save ${failed.length} subcategory budgets`);
            }
            return; // Don't reload on validation failure
        }

        // Reload budgets and summary
        await loadSubcategoryBudgets();
        showToast('Category budget saved successfully!', 'success');

    } catch (error) {
        console.error('Error saving category budget:', error);
        alert('Failed to save category budget: ' + error.message);
    }
}

// ============================================================================
// BUDGET RECOMMENDATIONS
// ============================================================================

async function showRecommendationsModal() {
    const modal = new bootstrap.Modal(document.getElementById('recommendationsModal'));
    modal.show();

    // Show loading, hide content
    document.getElementById('recommendationsLoading').style.display = 'block';
    document.getElementById('recommendationsContent').style.display = 'none';

    try {
        const response = await fetch('/budget/api/recommend_budgets?owner=all');
        const data = await response.json();

        if (data.success) {
            budgetState.recommendations = data.recommendations;
            budgetState.selectedRecommendations.clear();
            renderRecommendations(data.recommendations);
        } else {
            throw new Error(data.error || 'Failed to load recommendations');
        }
    } catch (error) {
        console.error('Error loading recommendations:', error);
        alert('Failed to load recommendations: ' + error.message);
        modal.hide();
    }
}

function renderRecommendations(recommendations) {
    const tbody = document.getElementById('recommendationsTableBody');
    const loading = document.getElementById('recommendationsLoading');
    const content = document.getElementById('recommendationsContent');

    if (!recommendations || recommendations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4">No recommendations available. Need at least 1 month of spending data.</td></tr>';
        loading.style.display = 'none';
        content.style.display = 'block';
        return;
    }

    // Get current budgets to compare
    const currentBudgets = budgetState.subcategoryBudgets;

    let html = '';

    recommendations.forEach(rec => {
        const current = currentBudgets.find(
            b => b.category === rec.category && b.sub_category === rec.sub_category
        );
        const currentAmount = current ? current.budget_amount : 0;
        const difference = rec.recommended_budget - currentAmount;
        const diffClass = difference > 0 ? 'text-danger' : difference < 0 ? 'text-success' : '';
        const diffSign = difference > 0 ? '+' : '';

        const confidenceClass = `confidence-${rec.confidence}`;

        html += `
            <tr>
                <td>
                    <input type="checkbox" class="recommendation-checkbox"
                           data-category="${rec.category}"
                           data-subcategory="${rec.sub_category}"
                           data-recommended="${rec.recommended_budget}"
                           onchange="toggleRecommendation(this)">
                </td>
                <td>${rec.category}</td>
                <td>${rec.sub_category}</td>
                <td>$${currentAmount.toFixed(2)}</td>
                <td>
                    <strong>$${rec.recommended_budget.toFixed(2)}</strong>
                    ${difference !== 0 ? `<br><small class="${diffClass}">${diffSign}$${Math.abs(difference).toFixed(2)}</small>` : ''}
                </td>
                <td>$${rec.last_6mo_avg.toFixed(2)}</td>
                <td>$${rec.last_3mo_avg.toFixed(2)}</td>
                <td>$${rec.last_1mo_actual.toFixed(2)}</td>
                <td>
                    <span class="badge recommendation-badge ${confidenceClass}">
                        ${rec.confidence.toUpperCase()}
                    </span>
                    <br><small class="text-muted">${rec.data_months}mo data</small>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
    loading.style.display = 'none';
    content.style.display = 'block';
}

function toggleRecommendation(checkbox) {
    const key = `${checkbox.dataset.category}|${checkbox.dataset.subcategory}`;

    if (checkbox.checked) {
        budgetState.selectedRecommendations.add(key);
    } else {
        budgetState.selectedRecommendations.delete(key);
    }
}

function toggleAllRecommendations(checked) {
    document.querySelectorAll('.recommendation-checkbox').forEach(checkbox => {
        checkbox.checked = checked;
        toggleRecommendation(checkbox);
    });
}

async function applySelectedRecommendations() {
    if (budgetState.selectedRecommendations.size === 0) {
        alert('Please select at least one recommendation to apply');
        return;
    }

    const budgetsToUpdate = [];

    budgetState.selectedRecommendations.forEach(key => {
        const [category, subcategory] = key.split('|');
        const recommendation = budgetState.recommendations.find(
            r => r.category === category && r.sub_category === subcategory
        );

        if (recommendation) {
            budgetsToUpdate.push({
                category: recommendation.category,
                sub_category: recommendation.sub_category,
                budget_amount: recommendation.recommended_budget,
                notes: `AI recommended based on ${recommendation.data_months} months of data (${recommendation.confidence} confidence)`
            });
        }
    });

    try {
        const response = await fetch('/budget/api/subcategory_templates/batch_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budgets: budgetsToUpdate })
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Applied ${budgetsToUpdate.length} recommendations successfully!`, 'success');

            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('recommendationsModal')).hide();

            // Reload subcategory budgets
            await loadSubcategoryBudgets();
        } else {
            throw new Error(result.error || 'Failed to apply recommendations');
        }
    } catch (error) {
        console.error('Error applying recommendations:', error);
        alert('Failed to apply recommendations: ' + error.message);
    }
}

// ============================================================================
// COMMITMENTS
// ============================================================================

async function loadCommitments() {
    console.log('Loading commitments...');

    try {
        const response = await fetch('/budget/api/commitments');
        const commitments = await response.json();

        budgetState.commitments = commitments;

        renderCommitments(commitments);
        updateSummaryCards();

    } catch (error) {
        console.error('Error loading commitments:', error);
        alert('Failed to load commitments');
    }
}

function renderCommitments(commitments) {
    const container = document.getElementById('commitmentsContainer');
    const loading = document.getElementById('commitmentLoadingMessage');
    const noCommitments = document.getElementById('noCommitments');

    loading.style.display = 'none';

    if (!commitments || commitments.length === 0) {
        container.style.display = 'none';
        noCommitments.style.display = 'block';
        return;
    }

    // Sort by due day
    const sorted = [...commitments].sort((a, b) => a.due_day_of_month - b.due_day_of_month);

    let html = '';

    sorted.forEach(commitment => {
        const fixedClass = commitment.is_fixed ? 'fixed' : '';
        const typeLabel = commitment.is_fixed ? 'Fixed' : 'Variable';

        html += `
            <div class="card commitment-card ${fixedClass}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-3">
                            <h6 class="mb-0">${commitment.name}</h6>
                            <small class="text-muted">${commitment.category} > ${commitment.sub_category}</small>
                        </div>
                        <div class="col-md-2">
                            <strong class="text-primary">$${commitment.estimated_amount.toFixed(2)}</strong>
                            <br><small class="badge bg-secondary">${typeLabel}</small>
                        </div>
                        <div class="col-md-2">
                            <span class="badge bg-info">Due: Day ${commitment.due_day_of_month}</span>
                        </div>
                        <div class="col-md-3">
                            <small class="text-muted">Added ${new Date(commitment.created_at).toLocaleDateString()}</small>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-primary" onclick="editCommitment(${commitment.id})">
                                ✏️ Edit
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteCommitment(${commitment.id})">
                                🗑️
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    container.style.display = 'block';
    noCommitments.style.display = 'none';

    // Render commitment summaries
    renderCommitmentSummaries(commitments);
}

function renderCommitmentSummaries(commitments) {
    const summariesContainer = document.getElementById('commitmentSummaries');

    if (!commitments || commitments.length === 0) {
        summariesContainer.style.display = 'none';
        return;
    }

    // Group by category
    const byCategory = {};
    commitments.forEach(c => {
        if (!byCategory[c.category]) {
            byCategory[c.category] = {
                category: c.category,
                count: 0,
                total: 0
            };
        }
        byCategory[c.category].count++;
        byCategory[c.category].total += parseFloat(c.estimated_amount);
    });

    // Group by subcategory
    const bySubcategory = {};
    commitments.forEach(c => {
        const key = `${c.category}|${c.sub_category}`;
        if (!bySubcategory[key]) {
            bySubcategory[key] = {
                category: c.category,
                subcategory: c.sub_category,
                count: 0,
                total: 0
            };
        }
        bySubcategory[key].count++;
        bySubcategory[key].total += parseFloat(c.estimated_amount);
    });

    // Cache data for sorting
    commitmentDataCache.category = Object.values(byCategory);
    commitmentDataCache.subcategory = Object.values(bySubcategory);

    // Reset sort state
    commitmentSortState.category = { column: 'category', direction: 'asc' };
    commitmentSortState.subcategory = { column: 'category', direction: 'asc' };

    // Initial render with default sort
    sortAndRenderCategoryTable();
    sortAndRenderSubcategoryTable();

    // Reset sort icons
    updateSortIcons('category', 'category', 'asc');
    updateSortIcons('subcategory', 'category', 'asc');

    // Render timeline chart
    renderCommitmentTimelineChart(commitments);

    summariesContainer.style.display = 'block';
}

let commitmentTimelineChart = null;

function renderCommitmentTimelineChart(commitments) {
    const canvas = document.getElementById('commitmentTimelineChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart if it exists
    if (commitmentTimelineChart) {
        commitmentTimelineChart.destroy();
    }

    // Create array for days 1-31
    const days = Array.from({ length: 31 }, (_, i) => i + 1);
    const dailyAmounts = new Array(31).fill(0);
    const dailyCommitments = new Array(31).fill(0);

    // Group commitments by due day
    commitments.forEach(c => {
        const day = c.due_day_of_month;
        if (day >= 1 && day <= 31) {
            dailyAmounts[day - 1] += parseFloat(c.estimated_amount);
            dailyCommitments[day - 1] += 1;
        }
    });

    // Create labels with commitment info
    const labels = days.map((day, index) => {
        const count = dailyCommitments[index];
        return count > 0 ? `Day ${day} (${count})` : `Day ${day}`;
    });

    commitmentTimelineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Commitments Due',
                data: dailyAmounts,
                backgroundColor: dailyAmounts.map(amount =>
                    amount > 0 ? 'rgba(54, 162, 235, 0.7)' : 'rgba(201, 203, 207, 0.2)'
                ),
                borderColor: dailyAmounts.map(amount =>
                    amount > 0 ? 'rgba(54, 162, 235, 1)' : 'rgba(201, 203, 207, 0.5)'
                ),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const day = context[0].label.split(' ')[1];
                            return `Day ${day} of the Month`;
                        },
                        label: function(context) {
                            const amount = context.parsed.y;
                            const dayIndex = context.dataIndex;
                            const count = dailyCommitments[dayIndex];

                            if (amount === 0) {
                                return 'No commitments due';
                            }

                            return [
                                `Total: $${amount.toFixed(2)}`,
                                `Commitments: ${count}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Day of Month'
                    },
                    ticks: {
                        maxRotation: 90,
                        minRotation: 45,
                        font: {
                            size: 9
                        },
                        callback: function(value, index) {
                            // Show only days with commitments or every 5th day
                            if (dailyCommitments[index] > 0 || (index + 1) % 5 === 0) {
                                return index + 1;
                            }
                            return '';
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

function showAddCommitmentModal() {
    document.getElementById('commitmentModalLabel').textContent = 'Add Commitment';
    document.getElementById('commitmentId').value = '';
    document.getElementById('commitmentForm').reset();
    document.getElementById('commitmentIsFixed').checked = true;

    // Load categories and subcategories
    loadCategoriesForCommitment();

    const modal = new bootstrap.Modal(document.getElementById('commitmentModal'));
    modal.show();
}

async function loadCategoriesForCommitment() {
    const categorySelect = document.getElementById('commitmentCategory');

    // Get unique categories from subcategory budgets
    const categories = [...new Set(budgetState.subcategoryBudgets.map(b => b.category))].sort();

    categorySelect.innerHTML = '<option value="">Select category...</option>' +
        categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
}

async function loadSubcategoriesForCommitment() {
    const category = document.getElementById('commitmentCategory').value;
    const subcategorySelect = document.getElementById('commitmentSubCategory');

    if (!category) {
        subcategorySelect.innerHTML = '<option value="">Select subcategory...</option>';
        return;
    }

    const subcategories = budgetState.subcategoryBudgets
        .filter(b => b.category === category)
        .map(b => b.sub_category)
        .sort();

    subcategorySelect.innerHTML = '<option value="">Select subcategory...</option>' +
        subcategories.map(sub => `<option value="${sub}">${sub}</option>`).join('');
}

async function saveCommitment() {
    const id = document.getElementById('commitmentId').value;
    const name = document.getElementById('commitmentName').value;
    const category = document.getElementById('commitmentCategory').value;
    const subCategory = document.getElementById('commitmentSubCategory').value;
    const amount = parseFloat(document.getElementById('commitmentAmount').value);
    const dueDay = parseInt(document.getElementById('commitmentDueDay').value);
    const isFixed = document.getElementById('commitmentIsFixed').checked;

    if (!name || !category || !subCategory || !amount || !dueDay) {
        alert('Please fill in all required fields');
        return;
    }

    const data = {
        name,
        category,
        sub_category: subCategory,
        estimated_amount: amount,
        due_day_of_month: dueDay,
        is_fixed: isFixed
    };

    try {
        const url = id ? `/budget/api/commitments/${id}` : '/budget/api/commitments';
        const method = id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showToast('Commitment saved successfully!', 'success');

            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('commitmentModal')).hide();

            // Reload commitments
            await loadCommitments();
        } else {
            throw new Error(result.error || 'Failed to save commitment');
        }
    } catch (error) {
        console.error('Error saving commitment:', error);
        alert('Failed to save commitment: ' + error.message);
    }
}

async function editCommitment(id) {
    const commitment = budgetState.commitments.find(c => c.id === id);

    if (!commitment) {
        alert('Commitment not found');
        return;
    }

    document.getElementById('commitmentModalLabel').textContent = 'Edit Commitment';
    document.getElementById('commitmentId').value = id;
    document.getElementById('commitmentName').value = commitment.name;
    document.getElementById('commitmentAmount').value = commitment.estimated_amount;
    document.getElementById('commitmentDueDay').value = commitment.due_day_of_month;
    document.getElementById('commitmentIsFixed').checked = commitment.is_fixed;

    // Load categories first
    await loadCategoriesForCommitment();

    // Set category
    document.getElementById('commitmentCategory').value = commitment.category;

    // Load subcategories for selected category
    await loadSubcategoriesForCommitment();

    // Set subcategory
    document.getElementById('commitmentSubCategory').value = commitment.sub_category;

    const modal = new bootstrap.Modal(document.getElementById('commitmentModal'));
    modal.show();
}

async function deleteCommitment(id) {
    if (!confirm('Are you sure you want to delete this commitment?')) {
        return;
    }

    try {
        const response = await fetch(`/budget/api/commitments/${id}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showToast('Commitment deleted successfully!', 'success');
            await loadCommitments();
        } else {
            throw new Error(result.error || 'Failed to delete commitment');
        }
    } catch (error) {
        console.error('Error deleting commitment:', error);
        alert('Failed to delete commitment: ' + error.message);
    }
}

// ============================================================================
// UNEXPECTED EXPENSES (kept from original)
// ============================================================================

async function loadUnexpectedExpenses() {
    console.log('Loading unexpected expenses...');

    try {
        const response = await fetch(`/budget/api/unexpected_expenses?month=${budgetState.currentMonth}&year=${budgetState.currentYear}`);
        const expenses = await response.json();

        budgetState.unexpectedExpenses = expenses;

        renderUnexpectedExpenses(expenses);
        updateSummaryCards();

        // Update the month labels
        const monthStr = String(budgetState.currentMonth).padStart(2, '0');
        const monthLabel = document.getElementById('unexpectedMonthLabel');
        if (monthLabel) {
            monthLabel.textContent = `${budgetState.currentYear}-${monthStr}`;
        }
        const summaryLabel = document.getElementById('unexpectedMonthSummary');
        if (summaryLabel) {
            summaryLabel.textContent = `${budgetState.currentYear}-${monthStr}`;
        }

    } catch (error) {
        console.error('Error loading unexpected expenses:', error);
    }
}

async function changeUnexpectedMonth() {
    const monthSelect = document.getElementById('unexpectedMonthSelect');
    const yearSelect = document.getElementById('unexpectedYearSelect');

    if (monthSelect && yearSelect) {
        budgetState.currentMonth = parseInt(monthSelect.value);
        budgetState.currentYear = parseInt(yearSelect.value);

        console.log(`Changing to ${budgetState.currentYear}-${budgetState.currentMonth}`);
        await loadUnexpectedExpenses();
    }
}

function renderUnexpectedExpenses(expenses) {
    const tbody = document.getElementById('unexpectedExpensesTableBody');
    const container = document.getElementById('unexpectedExpensesTableContainer');
    const loading = document.getElementById('unexpectedLoadingMessage');
    const noExpenses = document.getElementById('noUnexpectedExpenses');

    loading.style.display = 'none';

    if (!expenses || expenses.length === 0) {
        container.style.display = 'none';
        noExpenses.style.display = 'block';
        return;
    }

    let html = '';

    expenses.forEach(expense => {
        html += `
            <tr>
                <td>${expense.category}</td>
                <td>${expense.description}</td>
                <td>$${expense.amount.toFixed(2)}</td>
                <td>${new Date(expense.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editUnexpectedExpense(${expense.id})">
                        ✏️ Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteUnexpectedExpense(${expense.id})">
                        🗑️
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
    container.style.display = 'block';
    noExpenses.style.display = 'none';
}

function showAddUnexpectedExpenseModal() {
    document.getElementById('unexpectedExpenseModalLabel').textContent = 'Add Unexpected Expense';
    document.getElementById('unexpectedExpenseId').value = '';
    document.getElementById('unexpectedExpenseForm').reset();

    // Load categories
    const categorySelect = document.getElementById('unexpectedCategory');
    const categories = [...new Set(budgetState.subcategoryBudgets.map(b => b.category))].sort();

    categorySelect.innerHTML = '<option value="">Select category...</option>' +
        categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');

    const modal = new bootstrap.Modal(document.getElementById('unexpectedExpenseModal'));
    modal.show();
}

async function saveUnexpectedExpense() {
    const id = document.getElementById('unexpectedExpenseId').value;
    const category = document.getElementById('unexpectedCategory').value;
    const description = document.getElementById('unexpectedDescription').value;
    const amount = parseFloat(document.getElementById('unexpectedAmount').value);

    if (!category || !description || !amount) {
        alert('Please fill in all required fields');
        return;
    }

    const data = id ? { amount, description } : {
        category,
        description,
        amount,
        month: budgetState.currentMonth,
        year: budgetState.currentYear
    };

    try {
        const url = id ? `/budget/api/unexpected_expenses/${id}` : '/budget/api/unexpected_expenses';
        const method = id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showToast('Unexpected expense saved successfully!', 'success');

            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('unexpectedExpenseModal')).hide();

            // Reload
            await loadUnexpectedExpenses();
        } else {
            throw new Error(result.error || 'Failed to save unexpected expense');
        }
    } catch (error) {
        console.error('Error saving unexpected expense:', error);
        alert('Failed to save unexpected expense: ' + error.message);
    }
}

async function editUnexpectedExpense(id) {
    const expense = budgetState.unexpectedExpenses.find(e => e.id === id);

    if (!expense) {
        alert('Expense not found');
        return;
    }

    document.getElementById('unexpectedExpenseModalLabel').textContent = 'Edit Unexpected Expense';
    document.getElementById('unexpectedExpenseId').value = id;

    // Load categories into dropdown
    const categorySelect = document.getElementById('unexpectedCategory');
    const categories = [...new Set(budgetState.subcategoryBudgets.map(b => b.category))].sort();
    categorySelect.innerHTML = '<option value="">Select category...</option>' +
        categories.map(cat => `<option value="${cat}"${cat === expense.category ? ' selected' : ''}>${cat}</option>`).join('');

    document.getElementById('unexpectedDescription').value = expense.description;
    document.getElementById('unexpectedAmount').value = expense.amount;

    const modal = new bootstrap.Modal(document.getElementById('unexpectedExpenseModal'));
    modal.show();
}

async function deleteUnexpectedExpense(id) {
    if (!confirm('Are you sure you want to delete this unexpected expense?')) {
        return;
    }

    try {
        const response = await fetch(`/budget/api/unexpected_expenses/${id}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showToast('Unexpected expense deleted successfully!', 'success');
            await loadUnexpectedExpenses();
        } else {
            throw new Error(result.error || 'Failed to delete unexpected expense');
        }
    } catch (error) {
        console.error('Error deleting unexpected expense:', error);
        alert('Failed to delete unexpected expense: ' + error.message);
    }
}

// ============================================================================
// SUMMARY CARDS & UTILITIES
// ============================================================================

function updateSummaryCards() {
    // Total Budget
    const totalBudget = budgetState.subcategoryBudgets.reduce((sum, b) => sum + b.budget_amount, 0);
    document.getElementById('totalBudget').textContent = '$' + totalBudget.toFixed(2);

    // Total Commitments
    const totalCommitments = budgetState.commitments.reduce((sum, c) => sum + c.estimated_amount, 0);
    const commitmentCount = budgetState.commitments.filter(c => c.is_fixed).length;
    document.getElementById('totalCommitments').textContent = '$' + totalCommitments.toFixed(2);
    document.getElementById('commitmentCount').textContent = commitmentCount;

    // Living Budget
    const livingBudget = totalBudget - totalCommitments;
    document.getElementById('livingBudget').textContent = '$' + livingBudget.toFixed(2);

    // Unexpected Expenses
    const totalUnexpected = budgetState.unexpectedExpenses.reduce((sum, e) => sum + e.amount, 0);
    document.getElementById('totalUnexpectedExpenses').textContent = '$' + totalUnexpected.toFixed(2);
}

async function loadAllData() {
    await loadSubcategoryBudgets();
    await loadCommitments();
    await loadUnexpectedExpenses();
}

function showToast(message, type = 'success') {
    // Simple toast notification - you can enhance this with Bootstrap toasts
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';

    const toast = document.createElement('div');
    toast.className = `alert ${alertClass} position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ============================================================================
// COMMITMENT SORTING FUNCTIONALITY
// ============================================================================

let commitmentSortState = {
    category: {
        column: 'category',
        direction: 'asc'
    },
    subcategory: {
        column: 'category',
        direction: 'asc'
    }
};

let commitmentDataCache = {
    category: [],
    subcategory: []
};

function sortCommitmentCategory(column, table) {
    const state = commitmentSortState[table];

    // Toggle direction if same column, otherwise default to ascending
    if (state.column === column) {
        state.direction = state.direction === 'asc' ? 'desc' : 'asc';
    } else {
        state.column = column;
        state.direction = 'asc';
    }

    // Update sort icons
    updateSortIcons(table, column, state.direction);

    // Sort and re-render
    if (table === 'category') {
        sortAndRenderCategoryTable();
    } else {
        sortAndRenderSubcategoryTable();
    }
}

function updateSortIcons(table, activeColumn, direction) {
    const columns = table === 'category'
        ? ['category', 'count', 'total']
        : ['category', 'subcategory', 'count', 'total'];

    columns.forEach(col => {
        const icon = document.getElementById(`sort-icon-${table}-${col}`);
        if (icon) {
            if (col === activeColumn) {
                icon.className = direction === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
            } else {
                icon.className = 'fas fa-sort';
            }
        }
    });
}

function sortAndRenderCategoryTable() {
    const state = commitmentSortState.category;
    const data = [...commitmentDataCache.category];

    // Sort data
    data.sort((a, b) => {
        let valA, valB;

        if (state.column === 'category') {
            valA = a.category.toLowerCase();
            valB = b.category.toLowerCase();
            return state.direction === 'asc'
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
        } else if (state.column === 'count') {
            valA = a.count;
            valB = b.count;
        } else { // total
            valA = a.total;
            valB = b.total;
        }

        if (state.column !== 'category') {
            return state.direction === 'asc' ? valA - valB : valB - valA;
        }
    });

    // Render sorted data
    const categoryBody = document.getElementById('commitmentsByCategoryBody');
    let categoryHtml = '';
    let grandTotal = 0;
    let grandCount = 0;

    data.forEach(item => {
        categoryHtml += `
            <tr>
                <td><strong>${item.category}</strong></td>
                <td class="text-end">${item.count}</td>
                <td class="text-end text-primary"><strong>$${item.total.toFixed(2)}</strong></td>
            </tr>
        `;
        grandTotal += item.total;
        grandCount += item.count;
    });

    categoryHtml += `
        <tr class="table-primary">
            <td><strong>Total</strong></td>
            <td class="text-end"><strong>${grandCount}</strong></td>
            <td class="text-end"><strong>$${grandTotal.toFixed(2)}</strong></td>
        </tr>
    `;
    categoryBody.innerHTML = categoryHtml;
}

function sortAndRenderSubcategoryTable() {
    const state = commitmentSortState.subcategory;
    const data = [...commitmentDataCache.subcategory];

    // Sort data
    data.sort((a, b) => {
        let valA, valB;

        if (state.column === 'category') {
            valA = a.category.toLowerCase();
            valB = b.category.toLowerCase();
            return state.direction === 'asc'
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
        } else if (state.column === 'subcategory') {
            valA = a.subcategory.toLowerCase();
            valB = b.subcategory.toLowerCase();
            return state.direction === 'asc'
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
        } else if (state.column === 'count') {
            valA = a.count;
            valB = b.count;
        } else { // total
            valA = a.total;
            valB = b.total;
        }

        if (state.column === 'count' || state.column === 'total') {
            return state.direction === 'asc' ? valA - valB : valB - valA;
        }
    });

    // Render sorted data
    const subcategoryBody = document.getElementById('commitmentsBySubcategoryBody');
    let subcategoryHtml = '';

    data.forEach(item => {
        subcategoryHtml += `
            <tr>
                <td><small>${item.category}</small></td>
                <td>${item.subcategory}</td>
                <td class="text-end">${item.count}</td>
                <td class="text-end text-primary">$${item.total.toFixed(2)}</td>
            </tr>
        `;
    });

    subcategoryBody.innerHTML = subcategoryHtml;
}
