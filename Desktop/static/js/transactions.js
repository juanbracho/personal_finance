/* Transactions JavaScript - Complete Form Management */

// Transaction management state
let transactionState = {
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 50,
    filters: {},
    formData: {
        categories: [],
        sub_categories: [],
        accounts: [],
        owners: []
    },
    similarTransactions: []
};

// Initialize transactions functionality
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/transactions')) {
        console.log('📝 Loading transactions functionality...');
        
        if (window.location.pathname.includes('/add')) {
            initializeTransactionForm();
        } else {
            initializeTransactionsList();
        }
    }
});

// ============================================================================
// TRANSACTION FORM INITIALIZATION
// ============================================================================

function initializeTransactionForm() {
    console.log('📝 Initializing transaction form...');

    setupFormValidation();
    setTodaysDate();
    loadFormData();
    setupDynamicDropdowns();
    setupSimilarTransactionSearch();
    setupCreditHandling();  // NEW: Setup credit checkbox handling

    // Add event listeners
    const descriptionInput = document.getElementById('description');
    if (descriptionInput) {
        descriptionInput.addEventListener('input', debounce(searchSimilarTransactions, 300));
    }

    const amountInput = document.getElementById('amount');
    if (amountInput) {
        amountInput.addEventListener('input', validateAmount);
    }

    // Setup quick action handlers
    setupQuickActionHandlers();
}

function loadFormData() {
    console.log('📊 Loading form data from server...');

    fetch('/transactions/api/get_form_data')
        .then(response => response.json())
        .then(data => {
            transactionState.formData = data;
            console.log('📊 Form data loaded:', data);
        })
        .catch(error => {
            console.error('❌ Error loading form data:', error);
            FinanceUtils.showAlert('Error loading form data', 'warning');
        });
}

// ============================================================================
// CREDIT/DEBT ACCOUNT HANDLING (NEW - Phase 3)
// ============================================================================

function setupCreditHandling() {
    console.log('💳 Setting up credit checkbox handling...');

    const creditCheckbox = document.getElementById('is_credit');
    if (!creditCheckbox) return;

    // Listen to credit checkbox changes
    creditCheckbox.addEventListener('change', handleCreditToggle);
}

function handleCreditToggle() {
    const creditCheckbox = document.getElementById('is_credit');
    const creditWarning = document.getElementById('creditWarning');
    const accountSelect = document.getElementById('account_name');

    if (!creditCheckbox || !creditWarning || !accountSelect) return;

    if (creditCheckbox.checked) {
        // Credit mode: Load and show debt accounts
        creditWarning.style.display = 'block';
        console.log('💳 Credit mode enabled - loading debt accounts...');
        loadDebtAccounts();
    } else {
        // Regular mode: Show regular accounts from formData
        creditWarning.style.display = 'none';
        console.log('💵 Regular transaction mode - loading regular accounts...');
        loadRegularAccounts();
    }
}

function loadDebtAccounts() {
    console.log('💳 Loading debt accounts...');

    fetch('/api/accounts/list')
        .then(response => response.json())
        .then(data => {
            console.log('💳 Received accounts:', data);
            // Filter to only debt accounts
            const debtAccounts = data.filter(acc => acc.is_debt);
            console.log(`💳 Found ${debtAccounts.length} debt accounts`);
            populateAccountDropdown(debtAccounts, true);
        })
        .catch(error => {
            console.error('❌ Error loading debt accounts:', error);
            FinanceUtils.showAlert('Error loading debt accounts. Make sure you have debt accounts created.', 'warning');
        });
}

function loadRegularAccounts() {
    console.log('💵 Loading regular accounts...');

    // Use accounts from formData (existing transaction accounts)
    const regularAccounts = transactionState.formData.accounts || [];
    console.log(`💵 Found ${regularAccounts.length} regular accounts`);

    const accountSelect = document.getElementById('account_name');
    if (!accountSelect) return;

    // Save current selection
    const currentValue = accountSelect.value;

    // Clear existing options except the first one
    accountSelect.innerHTML = '<option value="">Select account...</option>';

    // Add regular accounts
    regularAccounts.forEach(accountName => {
        const option = document.createElement('option');
        option.value = accountName;
        option.textContent = accountName;
        accountSelect.appendChild(option);
    });

    // Restore selection if it still exists
    if (currentValue && regularAccounts.includes(currentValue)) {
        accountSelect.value = currentValue;
    }

    console.log(`💵 Added ${regularAccounts.length} regular accounts to dropdown`);
}

function populateAccountDropdown(accounts, isDebtMode = false) {
    const accountSelect = document.getElementById('account_name');
    if (!accountSelect) return;

    // Save current selection
    const currentValue = accountSelect.value;

    // Clear existing options
    accountSelect.innerHTML = '<option value="">Select account...</option>';

    // Add accounts
    accounts.forEach(account => {
        const option = document.createElement('option');

        if (isDebtMode) {
            // Debt accounts with indicator
            option.value = account.name;
            option.textContent = `💳 ${account.name} (${account.account_type})`;
            option.dataset.isDebt = 'true';
            option.dataset.debtAccountId = account.debt_account_id || '';
        } else {
            // Regular accounts
            option.value = account;
            option.textContent = account;
        }

        accountSelect.appendChild(option);
    });

    // Try to restore selection
    if (currentValue) {
        accountSelect.value = currentValue;
    }

    console.log(`💳 Added ${accounts.length} accounts to dropdown (debt mode: ${isDebtMode})`);
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

function setupFormValidation() {
    const form = document.getElementById('transactionForm');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateTransactionForm()) {
            form.submit();
        }
    });
    
    // Setup reset button to clear validation states
    const resetButton = document.querySelector('button[type="reset"]');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            setTimeout(() => {
                resetFormValidation();
                setTodaysDate();
            }, 10);
        });
    }
}

function validateTransactionForm() {
    console.log('🔍 Validating transaction form...');
    
    const requiredFields = [
        { id: 'date', name: 'Date' },
        { id: 'description', name: 'Description' },
        { id: 'amount', name: 'Amount' },
        { id: 'category', name: 'Category' },
        { id: 'type', name: 'Type' },
        { id: 'account_name', name: 'Account' },
        { id: 'owner', name: 'Owner' }
    ];
    
    let isValid = true;
    let errors = [];
    
    // Check required fields
    requiredFields.forEach(field => {
        const element = document.getElementById(field.id);
        if (!element || !element.value.trim()) {
            errors.push(`${field.name} is required`);
            if (element) {
                element.classList.add('is-invalid');
            }
            isValid = false;
        } else if (element) {
            element.classList.remove('is-invalid');
            element.classList.add('is-valid');
        }
    });
    
    // Validate amount
    const amountInput = document.getElementById('amount');
    if (amountInput && amountInput.value) {
        const amount = parseFloat(amountInput.value);
        if (amount === 0 || isNaN(amount)) {
            errors.push('Amount cannot be zero or invalid');
            amountInput.classList.add('is-invalid');
            isValid = false;
        }
    }
    
    // Validate description length
    const descriptionInput = document.getElementById('description');
    if (descriptionInput && descriptionInput.value.trim().length < 3) {
        errors.push('Description must be at least 3 characters long');
        descriptionInput.classList.add('is-invalid');
        isValid = false;
    }
    
    // Show errors if any
    if (!isValid) {
        FinanceUtils.showAlert('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
    }
    
    return isValid;
}

function validateAmount() {
    const amountInput = document.getElementById('amount');
    if (!amountInput) return;
    
    const amount = parseFloat(amountInput.value);
    
    if (amount === 0) {
        amountInput.setCustomValidity('Amount cannot be zero');
        amountInput.classList.add('is-invalid');
    } else {
        amountInput.setCustomValidity('');
        amountInput.classList.remove('is-invalid');
        if (amountInput.value) {
            amountInput.classList.add('is-valid');
        }
    }
}

function setTodaysDate() {
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        dateInput.value = FinanceUtils.getTodaysDate();
    }
}

function setSaveAndAddAnother() {
    // Set the hidden field to indicate save and add another
    const saveAndAddAnotherInput = document.getElementById('saveAndAddAnother');
    if (saveAndAddAnotherInput) {
        saveAndAddAnotherInput.value = 'true';
    }
    console.log('💾 Set save and add another mode');
}

function resetFormValidation() {
    const form = document.getElementById('transactionForm');
    if (!form) return;
    
    // Clear all validation classes
    const validatedFields = form.querySelectorAll('.is-valid, .is-invalid');
    validatedFields.forEach(field => {
        field.classList.remove('is-valid', 'is-invalid');
    });
    
    // Reset save and add another flag
    const saveAndAddAnotherInput = document.getElementById('saveAndAddAnother');
    if (saveAndAddAnotherInput) {
        saveAndAddAnotherInput.value = 'false';
    }
    
    // Clear custom validation messages
    const customValidatedFields = form.querySelectorAll('input, select, textarea');
    customValidatedFields.forEach(field => {
        field.setCustomValidity('');
    });
    
    console.log('🔄 Reset form validation states');
}

// ============================================================================
// DYNAMIC DROPDOWN MANAGEMENT
// ============================================================================

function setupDynamicDropdowns() {
    console.log('🔧 Setting up dynamic dropdowns...');
    
    // Setup add new buttons
    const addCategoryBtn = document.querySelector('[onclick="addNewCategory()"]');
    const addSubCategoryBtn = document.querySelector('[onclick="addNewSubCategory()"]');
    const addAccountBtn = document.querySelector('[onclick="addNewAccount()"]');
    const addOwnerBtn = document.querySelector('[onclick="addNewOwner()"]');
    
    if (addCategoryBtn) addCategoryBtn.onclick = () => addNewCategory();
    if (addSubCategoryBtn) addSubCategoryBtn.onclick = () => addNewSubCategory();
    if (addAccountBtn) addAccountBtn.onclick = () => addNewAccount();
    if (addOwnerBtn) addOwnerBtn.onclick = () => addNewOwner();
}

function addNewCategory() {
    console.log('➕ Adding new category...');
    
    const newCategory = prompt('Enter new category name:');
    if (!newCategory || !newCategory.trim()) {
        return;
    }
    
    const categoryName = newCategory.trim();
    
    // Validate category name
    if (categoryName.length < 2) {
        FinanceUtils.showAlert('Category name must be at least 2 characters long', 'danger');
        return;
    }
    
    // Check if category already exists
    if (transactionState.formData.categories.includes(categoryName)) {
        FinanceUtils.showAlert('Category already exists', 'warning');
        return;
    }
    
    // Add to server
    fetch('/transactions/api/add_category', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: categoryName })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Add to local state
            transactionState.formData.categories.push(categoryName);
            
            // Add to dropdown
            const categorySelect = document.getElementById('category');
            if (categorySelect) {
                const option = new Option(categoryName, categoryName);
                categorySelect.add(option);
                categorySelect.value = categoryName;
                categorySelect.classList.add('is-valid');
            }
            
            FinanceUtils.showAlert(`Category "${categoryName}" added successfully!`, 'success');
        } else {
            FinanceUtils.showAlert(`Error adding category: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Error adding category:', error);
        FinanceUtils.showAlert('Error adding category', 'danger');
    });
}

function addNewSubCategory() {
    console.log('➕ Adding new sub-category...');
    
    const newSubCategory = prompt('Enter new sub-category name:');
    if (!newSubCategory || !newSubCategory.trim()) {
        return;
    }
    
    const subCategoryName = newSubCategory.trim();
    
    // Validate sub-category name
    if (subCategoryName.length < 2) {
        FinanceUtils.showAlert('Sub-category name must be at least 2 characters long', 'danger');
        return;
    }
    
    // Check if sub-category already exists
    if (transactionState.formData.sub_categories.includes(subCategoryName)) {
        FinanceUtils.showAlert('Sub-category already exists', 'warning');
        return;
    }
    
    // Add to local state
    transactionState.formData.sub_categories.push(subCategoryName);
    
    // Add to dropdown
    const subCategorySelect = document.getElementById('sub_category');
    if (subCategorySelect) {
        const option = new Option(subCategoryName, subCategoryName);
        subCategorySelect.add(option);
        subCategorySelect.value = subCategoryName;
        subCategorySelect.classList.add('is-valid');
    }
    
    FinanceUtils.showAlert(`Sub-category "${subCategoryName}" will be saved with the transaction`, 'success');
}

function addNewAccount() {
    console.log('➕ Adding new account...');
    
    const newAccount = prompt('Enter new account name:');
    if (!newAccount || !newAccount.trim()) {
        return;
    }
    
    const accountName = newAccount.trim();
    
    // Validate account name
    if (accountName.length < 2) {
        FinanceUtils.showAlert('Account name must be at least 2 characters long', 'danger');
        return;
    }
    
    // Check if account already exists
    if (transactionState.formData.accounts.includes(accountName)) {
        FinanceUtils.showAlert('Account already exists', 'warning');
        return;
    }
    
    // Add to local state
    transactionState.formData.accounts.push(accountName);
    
    // Add to dropdown
    const accountSelect = document.getElementById('account_name');
    if (accountSelect) {
        const option = new Option(accountName, accountName);
        accountSelect.add(option);
        accountSelect.value = accountName;
        accountSelect.classList.add('is-valid');
    }
    
    FinanceUtils.showAlert(`Account "${accountName}" will be saved with the transaction`, 'success');
}

function addNewOwner() {
    console.log('➕ Adding new owner...');
    
    const newOwner = prompt('Enter new owner name:');
    if (!newOwner || !newOwner.trim()) {
        return;
    }
    
    const ownerName = newOwner.trim();
    
    // Validate owner name
    if (ownerName.length < 2) {
        FinanceUtils.showAlert('Owner name must be at least 2 characters long', 'danger');
        return;
    }
    
    // Check if owner already exists
    if (transactionState.formData.owners.includes(ownerName)) {
        FinanceUtils.showAlert('Owner already exists', 'warning');
        return;
    }
    
    // Add to local state
    transactionState.formData.owners.push(ownerName);
    
    // Add to dropdown
    const ownerSelect = document.getElementById('owner');
    if (ownerSelect) {
        const option = new Option(ownerName, ownerName);
        ownerSelect.add(option);
        ownerSelect.value = ownerName;
        ownerSelect.classList.add('is-valid');
    }
    
    FinanceUtils.showAlert(`Owner "${ownerName}" will be saved with the transaction`, 'success');
}

// ============================================================================
// QUICK ACTIONS AND TEMPLATES
// ============================================================================

function setupQuickActionHandlers() {
    console.log('⚡ Setting up quick action handlers...');
    
    // Setup quick action buttons
    const quickActionButtons = document.querySelectorAll('.quick-action-button');
    quickActionButtons.forEach(button => {
        button.removeAttribute('onclick');
        
        const buttonText = button.textContent.trim();
        
        button.addEventListener('click', function() {
            handleQuickAction(buttonText, button);
        });
    });
    
    // Setup template buttons
    const templateButtons = document.querySelectorAll('[data-template]');
    templateButtons.forEach(button => {
        button.addEventListener('click', function() {
            const template = this.getAttribute('data-template');
            if (template === 'income') {
                fillIncomeTemplate();
            } else if (template === 'business-income') {
                fillBusinessIncomeTemplate();
            }
        });
    });
    
    // Setup add new buttons
    const addButtons = document.querySelectorAll('[data-action]');
    addButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            switch(action) {
                case 'add-category':
                    addNewCategory();
                    break;
                case 'add-subcategory':
                    addNewSubCategory();
                    break;
                case 'add-account':
                    addNewAccount();
                    break;
                case 'add-owner':
                    addNewOwner();
                    break;
            }
        });
    });
}

function handleQuickAction(buttonText, button) {
    console.log(`⚡ Quick action: ${buttonText}`);
    
    // Define quick action mappings
    const quickActions = {
        '🛒 Groceries': { category: 'Groceries', type: 'Needs', avgAmount: 60 },
        '👕 Clothes': { category: 'Shopping', type: 'Wants', avgAmount: 50 },
        '🏠 Rent': { category: 'Living Expenses', type: 'Needs', avgAmount: 2500 },
        '📱 Subscriptions': { category: 'Subscriptions', type: 'Wants', avgAmount: 20 },
        '🍽️ Restaurant': { category: 'Dining Out', type: 'Wants', avgAmount: 40 },
        '🍿 Snacks': { category: 'Dining Out', type: 'Wants', avgAmount: 8 },
        '🎬 Entertainment': { category: 'Entertainment', type: 'Wants', avgAmount: 45 },
        '💊 Pharmacy': { category: 'Medical', type: 'Needs', avgAmount: 20 },
        '🏠 Home Supplies': { category: 'Home', type: 'Needs', avgAmount: 35 },
        '⛽ Gas': { category: 'Transport', type: 'Needs', avgAmount: 50 }
    };
    
    const actionData = quickActions[buttonText];
    if (actionData) {
        fillQuickAction(
            actionData.category, 
            actionData.category, 
            actionData.type, 
            actionData.avgAmount, 
            false
        );
    }
}

function fillQuickAction(subCategory, category, type, avgAmount, isBusiness) {
    console.log(`⚡ Quick action: ${subCategory} (${category}, ${type})`);

    // Fill form fields
    const descriptionInput = document.getElementById('description');
    const categorySelect = document.getElementById('category');
    const subCategorySelect = document.getElementById('sub_category');
    const typeSelect = document.getElementById('type');
    const businessCheckbox = document.getElementById('is_business');
    const amountInput = document.getElementById('amount');
    
    if (descriptionInput) descriptionInput.value = subCategory;
    if (categorySelect) categorySelect.value = category;
    if (subCategorySelect) subCategorySelect.value = subCategory;
    if (typeSelect) typeSelect.value = type;
    if (businessCheckbox) businessCheckbox.checked = isBusiness;
    
    // Set suggested amount (rounded to nearest dollar)
    if (amountInput) {
        const suggestedAmount = Math.round(Math.abs(avgAmount));
        amountInput.placeholder = `${suggestedAmount}.00`;
        amountInput.focus();
    }
    
    // Flash the form to indicate it was filled
    const form = document.getElementById('transactionForm');
    if (form) {
        form.style.backgroundColor = 'rgba(52, 152, 219, 0.1)';
        setTimeout(() => {
            form.style.backgroundColor = '';
        }, 500);
    }
}

function fillIncomeTemplate() {
    console.log('💰 Filling income template...');

    const descriptionInput = document.getElementById('description');
    const categorySelect = document.getElementById('category');
    const typeSelect = document.getElementById('type');
    const businessCheckbox = document.getElementById('is_business');
    const amountInput = document.getElementById('amount');

    if (descriptionInput) descriptionInput.value = 'Income/Refund';
    if (categorySelect) categorySelect.value = 'Savings';
    if (typeSelect) typeSelect.value = 'Savings';
    if (businessCheckbox) businessCheckbox.checked = false;
    if (amountInput) {
        amountInput.placeholder = '-200.00';
        amountInput.focus();
    }
}

function fillBusinessIncomeTemplate() {
    console.log('💼 Filling business income template...');

    const descriptionInput = document.getElementById('description');
    const categorySelect = document.getElementById('category');
    const subCategorySelect = document.getElementById('sub_category');
    const typeSelect = document.getElementById('type');
    const businessCheckbox = document.getElementById('is_business');
    const amountInput = document.getElementById('amount');

    if (descriptionInput) descriptionInput.value = 'Girasoul Revenue';
    if (categorySelect) categorySelect.value = 'Business';
    if (subCategorySelect) subCategorySelect.value = 'Girasoul';
    if (typeSelect) typeSelect.value = 'Business';
    if (businessCheckbox) businessCheckbox.checked = true;
    if (amountInput) {
        amountInput.placeholder = '-500.00';
        amountInput.focus();
    }
}

// ============================================================================
// SIMILAR TRANSACTIONS SEARCH
// ============================================================================

function setupSimilarTransactionSearch() {
    console.log('🔍 Setting up similar transaction search...');
    
    const descriptionInput = document.getElementById('description');
    const similarContainer = document.getElementById('similarTransactions');
    
    if (!descriptionInput || !similarContainer) {
        console.log('⚠️ Similar transaction elements not found');
        return;
    }
    
    // Initial state
    similarContainer.innerHTML = '<p class="text-muted">Start typing description to see similar transactions...</p>';
}

function searchSimilarTransactions() {
    const descriptionInput = document.getElementById('description');
    const similarContainer = document.getElementById('similarTransactions');
    
    if (!descriptionInput || !similarContainer) return;
    
    const searchTerm = descriptionInput.value.trim();
    
    if (searchTerm.length < 3) {
        similarContainer.innerHTML = '<p class="text-muted">Start typing description to see similar transactions...</p>';
        return;
    }
    
    // Show loading
    similarContainer.innerHTML = '<p class="text-muted">Searching for similar transactions...</p>';
    
    // Search for similar transactions
    fetch('/transactions/api/search_similar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description: searchTerm })
    })
    .then(response => response.json())
    .then(transactions => {
        displaySimilarTransactions(transactions);
    })
    .catch(error => {
        console.error('❌ Error searching similar transactions:', error);
        similarContainer.innerHTML = '<p class="text-muted text-danger">Error searching transactions</p>';
    });
}

function displaySimilarTransactions(transactions) {
    const similarContainer = document.getElementById('similarTransactions');
    if (!similarContainer) return;
    
    if (transactions.length === 0) {
        similarContainer.innerHTML = '<p class="text-muted">No similar transactions found.</p>';
        return;
    }
    
    let html = '<div class="similar-transactions-list">';
    html += '<h6 class="text-muted mb-2">Similar transactions:</h6>';
    
    transactions.forEach(transaction => {
        const amountDisplay = transaction.amount < 0 ? 
            `<span class="text-success">-${Math.abs(transaction.amount).toFixed(2)}</span>` :
            `<span class="text-danger">${transaction.amount.toFixed(2)}</span>`;
        
        html += `
            <div class="similar-transaction-item" onclick="applySimilarTransaction(${JSON.stringify(transaction).replace(/"/g, '&quot;')})">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${transaction.description}</strong><br>
                        <small class="text-muted">${transaction.category}${transaction.sub_category ? ' > ' + transaction.sub_category : ''}</small>
                    </div>
                    <div class="text-end">
                        ${amountDisplay}<br>
                        <small class="text-muted">${transaction.owner} • ${transaction.account_name}</small>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    similarContainer.innerHTML = html;
}

function applySimilarTransaction(transaction) {
    console.log('📋 Applying similar transaction:', transaction);
    
    // Fill form with similar transaction data
    const categorySelect = document.getElementById('category');
    const subCategorySelect = document.getElementById('sub_category');
    const typeSelect = document.getElementById('type');
    const accountSelect = document.getElementById('account_name');
    const ownerSelect = document.getElementById('owner');
    const amountInput = document.getElementById('amount');
    
    if (categorySelect) categorySelect.value = transaction.category;
    if (subCategorySelect) subCategorySelect.value = transaction.sub_category;
    if (typeSelect) typeSelect.value = transaction.type;
    if (accountSelect) accountSelect.value = transaction.account_name;
    if (ownerSelect) ownerSelect.value = transaction.owner;
    if (amountInput) {
        amountInput.placeholder = `${Math.abs(transaction.amount).toFixed(2)}`;
        amountInput.focus();
    }
    
    // Highlight that data was applied
    const form = document.getElementById('transactionForm');
    if (form) {
        form.style.backgroundColor = 'rgba(39, 174, 96, 0.1)';
        setTimeout(() => {
            form.style.backgroundColor = '';
        }, 1000);
    }
    
    FinanceUtils.showAlert('Applied similar transaction data!', 'success');
}

// ============================================================================
// TRANSACTIONS LIST FUNCTIONALITY
// ============================================================================

function initializeTransactionsList() {
    console.log('📝 Initializing transactions list...');
    
    setupPagination();
    setupFilters();
}

function setupPagination() {
    const urlParams = new URLSearchParams(window.location.search);
    transactionState.currentPage = parseInt(urlParams.get('page')) || 1;
    
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('📄 Navigating to page:', this.href);
        });
    });
}

function setupFilters() {
    console.log('🔍 Transaction filters ready');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatTransactionAmount(amount) {
    if (amount < 0) {
        return `<span class="transaction-amount-income">-${Math.abs(amount).toFixed(2)}</span>`;
    } else {
        return `<span class="transaction-amount-expense">${amount.toFixed(2)}</span>`;
    }
}

function getTransactionBadgeClass(type) {
    const badgeClasses = {
        'Needs': 'bg-danger',
        'Wants': 'bg-warning',
        'Savings': 'bg-success',
        'Business': 'bg-info'
    };
    return badgeClasses[type] || 'bg-secondary';
}

// ============================================================================
// TRANSACTION EDIT/DELETE FUNCTIONALITY
// ============================================================================

function editTransaction(transactionId) {
    console.log(`✏️ Editing transaction ID: ${transactionId}`);
    
    // Show loading state
    const modal = document.getElementById('editTransactionModal');
    const modalLabel = document.getElementById('editTransactionModalLabel');
    modalLabel.textContent = 'Loading transaction...';
    
    // Load form data first
    loadEditFormData().then(() => {
        // Then load transaction details
        fetch(`/transactions/api/get_transaction/${transactionId}`)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    populateEditForm(result.transaction);
                    modalLabel.textContent = `Edit Transaction: ${result.transaction.description}`;
                    
                    // Show modal
                    if (typeof bootstrap !== 'undefined' && modal) {
                        const bsModal = new bootstrap.Modal(modal);
                        bsModal.show();
                    }
                } else {
                    FinanceUtils.showAlert(`Error loading transaction: ${result.error}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error loading transaction:', error);
                FinanceUtils.showAlert('Error loading transaction for editing', 'danger');
            });
    });
}

function deleteTransaction(transactionId, description) {
    console.log(`🗑️ Deleting transaction ID: ${transactionId}`);

    // Show confirmation dialog
    const confirmMessage = `Are you sure you want to delete this transaction?\n\n"${description}"`;

    if (!confirm(confirmMessage)) {
        return;
    }

    // Find and fade out the row immediately for smooth UX
    const row = document.querySelector(`button[onclick*="deleteTransaction(${transactionId}"]`)?.closest('tr');
    if (row) {
        row.style.transition = 'opacity 0.3s ease';
        row.style.opacity = '0.5';
    }

    // Delete the transaction
    fetch(`/transactions/api/delete_transaction/${transactionId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Remove the row with animation
            if (row) {
                row.style.opacity = '0';
                setTimeout(() => {
                    row.remove();
                }, 300);
            }
            // Refresh page after brief delay to update counts
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            // Restore row opacity on error
            if (row) row.style.opacity = '1';
            FinanceUtils.showAlert(`Error deleting transaction: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting transaction:', error);
        if (row) row.style.opacity = '1';
        FinanceUtils.showAlert('Error deleting transaction', 'danger');
    });
}

function loadEditFormData() {
    console.log('📊 Loading edit form data...');
    
    return fetch('/transactions/api/get_form_data')
        .then(response => response.json())
        .then(data => {
            // Populate categories
            const categorySelect = document.getElementById('editCategory');
            categorySelect.innerHTML = '<option value="">Select category...</option>';
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
            
            // Populate sub-categories
            const subCategorySelect = document.getElementById('editSubCategory');
            subCategorySelect.innerHTML = '<option value="">Select sub-category...</option>';
            data.sub_categories.forEach(subCategory => {
                const option = document.createElement('option');
                option.value = subCategory;
                option.textContent = subCategory;
                subCategorySelect.appendChild(option);
            });
            
            // Populate accounts
            const accountSelect = document.getElementById('editAccountName');
            accountSelect.innerHTML = '<option value="">Select account...</option>';
            data.accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account;
                option.textContent = account;
                accountSelect.appendChild(option);
            });
            
            // Populate owners
            const ownerSelect = document.getElementById('editOwner');
            ownerSelect.innerHTML = '<option value="">Select owner...</option>';
            data.owners.forEach(owner => {
                const option = document.createElement('option');
                option.value = owner;
                option.textContent = owner;
                ownerSelect.appendChild(option);
            });
            
            console.log('📊 Edit form data loaded successfully');
        })
        .catch(error => {
            console.error('Error loading edit form data:', error);
            throw error;
        });
}

function populateEditForm(transaction) {
    console.log('📝 Populating edit form with transaction data:', transaction);

    // Set form values
    document.getElementById('editTransactionId').value = transaction.id;
    document.getElementById('editDate').value = transaction.date;
    document.getElementById('editDescription').value = transaction.description;
    document.getElementById('editAmount').value = transaction.amount;
    document.getElementById('editCategory').value = transaction.category;
    document.getElementById('editSubCategory').value = transaction.sub_category || '';
    document.getElementById('editType').value = transaction.type;
    document.getElementById('editAccountName').value = transaction.account_name;
    document.getElementById('editOwner').value = transaction.owner;

    // Set is_business checkbox if it exists
    const editIsBusiness = document.getElementById('editIsBusiness');
    if (editIsBusiness) {
        editIsBusiness.checked = transaction.is_business;
    }
}

function saveTransactionEdit() {
    console.log('💾 Saving transaction edit...');

    // Get form data
    const transactionId = document.getElementById('editTransactionId').value;
    const editIsBusiness = document.getElementById('editIsBusiness');

    const formData = {
        account_name: document.getElementById('editAccountName').value,
        date: document.getElementById('editDate').value,
        description: document.getElementById('editDescription').value,
        amount: document.getElementById('editAmount').value,
        sub_category: document.getElementById('editSubCategory').value,
        category: document.getElementById('editCategory').value,
        type: document.getElementById('editType').value,
        owner: document.getElementById('editOwner').value,
        is_business: editIsBusiness ? editIsBusiness.checked : false
    };
    
    // Validate required fields
    const requiredFields = ['account_name', 'date', 'description', 'amount', 'category', 'type', 'owner'];
    let isValid = true;
    let errors = [];
    
    requiredFields.forEach(field => {
        if (!formData[field] || formData[field].toString().trim() === '') {
            errors.push(`${field.replace('_', ' ')} is required`);
            isValid = false;
        }
    });
    
    // Validate amount
    if (formData.amount && parseFloat(formData.amount) === 0) {
        errors.push('Amount cannot be zero');
        isValid = false;
    }
    
    if (!isValid) {
        FinanceUtils.showAlert('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
        return;
    }
    
    // Save the transaction
    fetch(`/transactions/api/update_transaction/${transactionId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Hide modal immediately
            const modal = document.getElementById('editTransactionModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }

            // Refresh page to show changes
            window.location.reload();
        } else {
            FinanceUtils.showAlert(`Error updating transaction: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error updating transaction:', error);
        FinanceUtils.showAlert('Error updating transaction', 'danger');
    });
}

function validateEditForm() {
    const form = document.getElementById('editTransactionForm');
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });
    
    // Validate amount
    const amountInput = document.getElementById('editAmount');
    if (amountInput && amountInput.value) {
        const amount = parseFloat(amountInput.value);
        if (amount === 0 || isNaN(amount)) {
            amountInput.classList.add('is-invalid');
            isValid = false;
        } else {
            amountInput.classList.remove('is-invalid');
            amountInput.classList.add('is-valid');
        }
    }
    
    return isValid;
}

// Add form validation listeners for edit form
document.addEventListener('DOMContentLoaded', function() {
    // Add validation to edit form if it exists
    const editForm = document.getElementById('editTransactionForm');
    if (editForm) {
        const requiredFields = editForm.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', validateEditForm);
            field.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    validateEditForm();
                }
            });
        });
    }
});

// ============================================================================
// GLOBAL FUNCTIONS (for HTML onclick compatibility)
// ============================================================================

// These functions are kept for any remaining HTML onclick handlers
window.fillQuickAction = fillQuickAction;
window.fillIncomeTemplate = fillIncomeTemplate;
window.fillBusinessIncomeTemplate = fillBusinessIncomeTemplate;
window.addNewCategory = addNewCategory;
window.addNewSubCategory = addNewSubCategory;
window.addNewAccount = addNewAccount;
window.addNewOwner = addNewOwner;
window.applySimilarTransaction = applySimilarTransaction;

// Export transaction functions
window.Transactions = {
    fillQuickAction,
    fillIncomeTemplate,
    fillBusinessIncomeTemplate,
    addNewCategory,
    addNewSubCategory,
    addNewAccount,
    addNewOwner,
    formatTransactionAmount,
    getTransactionBadgeClass,
    searchSimilarTransactions,
    applySimilarTransaction
};


// Export functions for global access
window.editTransaction = editTransaction;
window.deleteTransaction = deleteTransaction;
window.saveTransactionEdit = saveTransactionEdit;
window.setSaveAndAddAnother = setSaveAndAddAnother;

// Fetch and render dynamic quick actions
function loadQuickActions() {
    const container = document.getElementById('quickActionsContainer');
    if (!container) return;
    container.innerHTML = '<div class="text-center text-muted">Loading quick actions...</div>';
    fetch('/transactions/api/transactions/common_patterns')
        .then(res => res.json())
        .then(patterns => {
            if (!Array.isArray(patterns) || patterns.length === 0) {
                container.innerHTML = '<div class="text-center text-muted">No quick actions found.</div>';
                return;
            }
            container.innerHTML = '';
            patterns.forEach((pattern, idx) => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-outline-primary btn-sm quick-action-button';
                btn.innerHTML =
                    (pattern.category ? `<span class='fw-bold'>${pattern.category}</span> ` : '') +
                    (pattern.sub_category ? `<span>${pattern.sub_category}</span> ` : '') +
                    (pattern.type ? `<span class='text-muted'>${pattern.type}</span>` : '');
                btn.addEventListener('click', function() {
                    fillQuickActionFromPattern(pattern);
                });
                container.appendChild(btn);
            });
        })
        .catch(() => {
            container.innerHTML = '<div class="text-center text-danger">Error loading quick actions.</div>';
        });
}

function fillQuickActionFromPattern(pattern) {
    // Set today's date
    const dateInput = document.getElementById('date');
    if (dateInput) dateInput.value = FinanceUtils.getTodaysDate();
    // Fill form fields
    const categorySelect = document.getElementById('category');
    const subCategorySelect = document.getElementById('sub_category');
    const typeSelect = document.getElementById('type');
    if (categorySelect) categorySelect.value = pattern.category || '';
    if (subCategorySelect) subCategorySelect.value = pattern.sub_category || '';
    if (typeSelect) typeSelect.value = pattern.type || '';
    // Flash the form to indicate it was filled
    const form = document.getElementById('transactionForm');
    if (form) {
        form.style.backgroundColor = 'rgba(52, 152, 219, 0.1)';
        setTimeout(() => {
            form.style.backgroundColor = '';
        }, 500);
    }
}
// Call loadQuickActions on page load
document.addEventListener('DOMContentLoaded', loadQuickActions);

// Export handleCreditToggle for global access (called from HTML)
window.handleCreditToggle = handleCreditToggle;