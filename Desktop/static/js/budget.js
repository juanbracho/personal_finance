/* Budget Management JavaScript */

// Budget management state
let budgetState = {
    initialBudgets: [],
    unexpectedExpenses: [],
    currentEditingExpenseId: null,
    selectedYear: new Date().getFullYear(),
    selectedMonth: new Date().getMonth() + 1
};

// Initialize budget management
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/budget')) {
        console.log('🚀 Loading budget management...');
        
        // Get year and month from URL or form
        const urlParams = new URLSearchParams(window.location.search);
        budgetState.selectedYear = parseInt(urlParams.get('year')) || budgetState.selectedYear;
        budgetState.selectedMonth = parseInt(urlParams.get('month')) || budgetState.selectedMonth;
        
        loadInitialBudgets();
        loadUnexpectedExpenses();
    }
});

// Initial Budget Functions
function loadInitialBudgets() {
    console.log('📋 Loading initial budgets...');
    
    FinanceUtils.apiCall('/budget/api/templates')
        .then(data => {
            console.log('📋 Received budget templates:', data);
            budgetState.initialBudgets = data;
            hideLoadingMessage();
            renderInitialBudgetTable();
            populateCategoryDropdown();
            updateSummaryCards();
        })
        .catch(error => {
            console.error('Error loading initial budgets:', error);
            hideLoadingMessage();
            showErrorMessage('Error loading initial budgets: ' + error.message);
        });
}

function hideLoadingMessage() {
    const loadingEl = document.getElementById('loadingMessage');
    const tableEl = document.getElementById('budgetTableContainer');
    
    if (loadingEl) loadingEl.style.display = 'none';
    if (tableEl) tableEl.style.display = 'block';
}

function showErrorMessage(message) {
    const loadingEl = document.getElementById('loadingMessage');
    const errorEl = document.getElementById('errorMessage');
    
    if (loadingEl) loadingEl.style.display = 'none';
    if (errorEl) {
        errorEl.style.display = 'block';
        errorEl.innerHTML = `
            <h6>Error Loading Budget Data</h6>
            <p class="mb-0">${message}</p>
        `;
    }
}

function renderInitialBudgetTable() {
    const tbody = document.getElementById('initialBudgetTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (budgetState.initialBudgets.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4">
                    <p class="text-muted">No budget templates found. Budget templates will be created from your transaction categories.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    budgetState.initialBudgets.forEach((budget, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${budget.category}</td>
            <td class="text-success fw-bold">$${budget.budget_amount.toFixed(2)}</td>
            <td>
                <div class="input-group">
                    <span class="input-group-text">$</span>
                    <input type="number" 
                           class="form-control" 
                           value="${budget.budget_amount.toFixed(2)}" 
                           step="0.01" 
                           min="0"
                           id="initial_amount_${index}"
                           onchange="updateInitialBudget(${index}, this.value)">
                </div>
            </td>
            <td>
                <input type="text" 
                       class="form-control" 
                       value="${budget.notes || ''}" 
                       placeholder="Budget notes..."
                       id="initial_notes_${index}"
                       onchange="updateInitialNotes(${index}, this.value)">
            </td>
            <td>
                <button class="btn btn-success btn-sm" onclick="saveInitialBudget(${index})">
                    💾 Save
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateInitialBudget(index, amount) {
    budgetState.initialBudgets[index].budget_amount = parseFloat(amount) || 0;
    budgetState.initialBudgets[index].changed = true;
    updateSummaryCards();
}

function updateInitialNotes(index, notes) {
    budgetState.initialBudgets[index].notes = notes;
    budgetState.initialBudgets[index].changed = true;
}

function saveInitialBudget(index) {
    const budget = budgetState.initialBudgets[index];
    
    FinanceUtils.apiCall('/budget/api/update_template', {
        method: 'POST',
        body: JSON.stringify({
            category: budget.category,
            budget_amount: budget.budget_amount,
            notes: budget.notes
        })
    })
    .then(result => {
        if (result.success) {
            FinanceUtils.showAlert(`Initial budget for ${budget.category} saved successfully!`, 'success');
            budget.changed = false;
            updateSummaryCards();
        } else {
            FinanceUtils.showAlert(`Error saving budget: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving initial budget:', error);
        FinanceUtils.showAlert('Error saving initial budget', 'danger');
    });
}

function saveAllInitialBudgets() {
    const changedBudgets = budgetState.initialBudgets.filter(b => b.changed);
    
    if (changedBudgets.length === 0) {
        FinanceUtils.showAlert('No changes to save', 'info');
        return;
    }
    
    let savedCount = 0;
    const totalToSave = changedBudgets.length;
    
    changedBudgets.forEach(budget => {
        FinanceUtils.apiCall('/budget/api/update_template', {
            method: 'POST',
            body: JSON.stringify({
                category: budget.category,
                budget_amount: budget.budget_amount,
                notes: budget.notes
            })
        })
        .then(result => {
            if (result.success) {
                budget.changed = false;
                savedCount++;
                
                if (savedCount === totalToSave) {
                    FinanceUtils.showAlert(`All ${totalToSave} initial budgets saved successfully!`, 'success');
                    updateSummaryCards();
                }
            } else {
                FinanceUtils.showAlert(`Error saving ${budget.category}: ${result.error}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Error saving initial budget:', error);
            FinanceUtils.showAlert(`Error saving ${budget.category}`, 'danger');
        });
    });
}

function resetInitialBudgets() {
    if (confirm('Reset all initial budget changes? This will reload the original values.')) {
        loadInitialBudgets();
    }
}

// Unexpected Expenses Functions
function loadUnexpectedExpenses() {
    console.log('💸 Loading unexpected expenses...');
    
    const loadingEl = document.getElementById('unexpectedLoadingMessage');
    const tableEl = document.getElementById('unexpectedExpensesTableContainer');
    const noDataEl = document.getElementById('noUnexpectedExpenses');
    
    if (loadingEl) loadingEl.style.display = 'block';
    if (tableEl) tableEl.style.display = 'none';
    if (noDataEl) noDataEl.style.display = 'none';
    
    FinanceUtils.apiCall(`/budget/api/unexpected_expenses?month=${budgetState.selectedMonth}&year=${budgetState.selectedYear}`)
        .then(data => {
            console.log('💸 Received unexpected expenses:', data);
            budgetState.unexpectedExpenses = data;
            hideUnexpectedLoadingMessage();
            renderUnexpectedExpensesTable();
            updateSummaryCards();
        })
        .catch(error => {
            console.error('Error loading unexpected expenses:', error);
            hideUnexpectedLoadingMessage();
            showUnexpectedErrorMessage('Error loading unexpected expenses: ' + error.message);
        });
}

function hideUnexpectedLoadingMessage() {
    const loadingEl = document.getElementById('unexpectedLoadingMessage');
    const tableEl = document.getElementById('unexpectedExpensesTableContainer');
    const noDataEl = document.getElementById('noUnexpectedExpenses');
    
    if (loadingEl) loadingEl.style.display = 'none';
    
    if (budgetState.unexpectedExpenses.length === 0) {
        if (noDataEl) noDataEl.style.display = 'block';
    } else {
        if (tableEl) tableEl.style.display = 'block';
    }
}

function showUnexpectedErrorMessage(message) {
    const loadingEl = document.getElementById('unexpectedLoadingMessage');
    const errorEl = document.getElementById('unexpectedErrorMessage');
    
    if (loadingEl) loadingEl.style.display = 'none';
    if (errorEl) errorEl.style.display = 'block';
}

function renderUnexpectedExpensesTable() {
    const tbody = document.getElementById('unexpectedExpensesTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    budgetState.unexpectedExpenses.forEach(expense => {
        const row = document.createElement('tr');
        const createdDate = new Date(expense.created_at).toLocaleDateString();
        
        row.innerHTML = `
            <td><span class="badge bg-secondary">${expense.category}</span></td>
            <td class="fw-bold">${expense.description}</td>
            <td class="text-danger fw-bold">${expense.amount.toFixed(2)}</td>
            <td class="text-muted">${createdDate}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary btn-sm" 
                            onclick="editUnexpectedExpense(${expense.id})"
                            title="Edit">
                        ✏️
                    </button>
                    <button class="btn btn-outline-danger btn-sm" 
                            onclick="deleteUnexpectedExpense(${expense.id})"
                            title="Delete">
                        🗑️
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function populateCategoryDropdown() {
    const dropdown = document.getElementById('unexpectedCategory');
    if (!dropdown) return;
    
    dropdown.innerHTML = '<option value="">Select category...</option>';
    
    budgetState.initialBudgets.forEach(budget => {
        const option = document.createElement('option');
        option.value = budget.category;
        option.textContent = budget.category;
        dropdown.appendChild(option);
    });
}

function showAddUnexpectedExpenseModal() {
    budgetState.currentEditingExpenseId = null;
    const modal = document.getElementById('unexpectedExpenseModal');
    const titleEl = document.getElementById('unexpectedExpenseModalLabel');
    const saveTextEl = document.getElementById('saveUnexpectedExpenseText');
    
    if (titleEl) titleEl.textContent = 'Add Unexpected Expense';
    if (saveTextEl) saveTextEl.textContent = 'Save Expense';
    
    // Reset form
    const form = document.getElementById('unexpectedExpenseForm');
    if (form) form.reset();
    
    // Show modal
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function editUnexpectedExpense(expenseId) {
    const expense = budgetState.unexpectedExpenses.find(e => e.id === expenseId);
    if (!expense) return;
    
    budgetState.currentEditingExpenseId = expenseId;
    const modal = document.getElementById('unexpectedExpenseModal');
    const titleEl = document.getElementById('unexpectedExpenseModalLabel');
    const saveTextEl = document.getElementById('saveUnexpectedExpenseText');
    
    if (titleEl) titleEl.textContent = 'Edit Unexpected Expense';
    if (saveTextEl) saveTextEl.textContent = 'Update Expense';
    
    // Populate form
    const categoryEl = document.getElementById('unexpectedCategory');
    const descriptionEl = document.getElementById('unexpectedDescription');
    const amountEl = document.getElementById('unexpectedAmount');
    
    if (categoryEl) categoryEl.value = expense.category;
    if (descriptionEl) descriptionEl.value = expense.description;
    if (amountEl) amountEl.value = expense.amount;
    
    // Show modal
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function saveUnexpectedExpense() {
    const categoryEl = document.getElementById('unexpectedCategory');
    const descriptionEl = document.getElementById('unexpectedDescription');
    const amountEl = document.getElementById('unexpectedAmount');
    
    if (!categoryEl || !descriptionEl || !amountEl) return;
    
    const category = categoryEl.value;
    const description = descriptionEl.value;
    const amount = parseFloat(amountEl.value);
    
    if (!category || !description || !amount || amount <= 0) {
        FinanceUtils.showAlert('Please fill in all fields with valid values', 'danger');
        return;
    }
    
    const data = {
        category: category,
        description: description,
        amount: amount,
        month: budgetState.selectedMonth,
        year: budgetState.selectedYear
    };
    
    let url = '/budget/api/unexpected_expenses';
    let method = 'POST';
    
    if (budgetState.currentEditingExpenseId) {
        url = `/budget/api/unexpected_expenses/${budgetState.currentEditingExpenseId}`;
        method = 'PUT';
        delete data.month;
        delete data.year;
    }
    
    FinanceUtils.apiCall(url, {
        method: method,
        body: JSON.stringify(data)
    })
    .then(result => {
        if (result.success) {
            FinanceUtils.showAlert(result.message, 'success');
            loadUnexpectedExpenses();
            
            // Hide modal
            const modal = document.getElementById('unexpectedExpenseModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving unexpected expense:', error);
        FinanceUtils.showAlert('Error saving unexpected expense', 'danger');
    });
}

function deleteUnexpectedExpense(expenseId) {
    const expense = budgetState.unexpectedExpenses.find(e => e.id === expenseId);
    if (!expense) return;
    
    if (confirm(`Delete unexpected expense: ${expense.description} (${expense.amount.toFixed(2)})?`)) {
        FinanceUtils.apiCall(`/budget/api/unexpected_expenses/${expenseId}`, {
            method: 'DELETE'
        })
        .then(result => {
            if (result.success) {
                FinanceUtils.showAlert(result.message, 'success');
                loadUnexpectedExpenses();
            } else {
                FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Error deleting unexpected expense:', error);
            FinanceUtils.showAlert('Error deleting unexpected expense', 'danger');
        });
    }
}

function updateSummaryCards() {
    const totalInitial = budgetState.initialBudgets.reduce((sum, budget) => sum + budget.budget_amount, 0);
    const totalUnexpected = budgetState.unexpectedExpenses.reduce((sum, expense) => sum + expense.amount, 0);
    const totalEffective = totalInitial + totalUnexpected;
    
    const initialEl = document.getElementById('totalInitialBudget');
    const unexpectedEl = document.getElementById('totalUnexpectedExpenses');
    const effectiveEl = document.getElementById('totalEffectiveBudget');
    
    if (initialEl) initialEl.textContent = `${totalInitial.toFixed(2)}`;
    if (unexpectedEl) unexpectedEl.textContent = `${totalUnexpected.toFixed(2)}`;
    if (effectiveEl) effectiveEl.textContent = `${totalEffective.toFixed(2)}`;
}

// Budget chart functions for dashboard integration
function loadBudgetCharts() {
    const budgetData = getBudgetDataFromTemplate();
    
    if (budgetData && budgetData.length > 0) {
        createBudgetVsActualChart(budgetData);
        createBudgetImpactChart(budgetData);
    }
}

function createBudgetVsActualChart(data) {
    const traces = [
        {
            x: data.map(item => item.category),
            y: data.map(item => item.effectiveBudget),
            name: 'Effective Budget',
            type: 'bar',
            marker: { color: '#3498db', opacity: 0.8 },
            text: data.map(item => `${item.effectiveBudget.toFixed(0)}`),
            textposition: 'outside'
        },
        {
            x: data.map(item => item.category),
            y: data.map(item => item.actualSpending),
            name: 'Actual Spending',
            type: 'bar',
            marker: { 
                color: data.map(item => item.actualSpending <= item.effectiveBudget ? '#27ae60' : '#e74c3c'),
                opacity: 0.8 
            },
            text: data.map(item => `${item.actualSpending.toFixed(0)}`),
            textposition: 'outside'
        }
    ];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Effective Budget vs Actual Spending',
        barmode: 'group',
        xaxis: { 
            title: 'Category',
            tickangle: -45
        },
        yaxis: { title: 'Amount ($)' },
        height: 400,
        showlegend: true,
        legend: {
            orientation: 'h',
            x: 0,
            y: 1.02
        }
    };
    
    const element = document.getElementById('budgetVsActualChart');
    if (element) {
        Plotly.newPlot('budgetVsActualChart', traces, layout, chartConfig);
    }
}

function createBudgetImpactChart(data) {
    const traces = [
        {
            x: data.map(item => item.category),
            y: data.map(item => item.initialBudget),
            name: 'Initial Budget',
            type: 'bar',
            marker: { color: '#2c3e50', opacity: 0.6 }
        },
        {
            x: data.map(item => item.category),
            y: data.map(item => item.unexpectedExpenses),
            name: 'Unexpected Expenses',
            type: 'bar',
            marker: { color: '#f39c12', opacity: 0.8 }
        }
    ];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Budget Impact: Initial + Unexpected',
        barmode: 'stack',
        xaxis: { 
            title: 'Category',
            tickangle: -45
        },
        yaxis: { title: 'Amount ($)' },
        height: 400,
        showlegend: true,
        legend: {
            orientation: 'h',
            x: 0,
            y: 1.02
        }
    };
    
    const element = document.getElementById('budgetImpactChart');
    if (element) {
        Plotly.newPlot('budgetImpactChart', traces, layout, chartConfig);
    }
}

function getBudgetDataFromTemplate() {
    // This function will get budget data from template variables
    return window.budgetAnalysisData || [];
}

// Export budget functions
window.BudgetManager = {
    loadInitialBudgets,
    loadUnexpectedExpenses,
    saveAllInitialBudgets,
    resetInitialBudgets,
    showAddUnexpectedExpenseModal,
    saveUnexpectedExpense,
    loadBudgetCharts,
    exportBudgetReport
};