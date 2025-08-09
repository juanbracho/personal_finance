/* Debt Management JavaScript */

// Debt management state
let debtState = {
    currentDebtId: null,
    currentDebtName: null,
    formData: {
        accounts: [],
        owners: []
    }
};

// Initialize debt management
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/debts')) {
        console.log('💳 Loading debt management...');
        loadFormData();
    }
});

// Load form data for dropdowns
function loadFormData() {
    console.log('📊 Loading form data for dropdowns...');
    
    fetch('/transactions/api/get_form_data')
        .then(response => response.json())
        .then(data => {
            debtState.formData = data;
            console.log('📊 Form data loaded:', data);
        })
        .catch(error => {
            console.error('❌ Error loading form data:', error);
            // Set defaults
            debtState.formData = {
                accounts: ['Venture', 'Cacas', 'Cata'],
                owners: ['Cata', 'Suricata', 'Cacas']
            };
        });
}

// Show payment modal
function showPaymentModal(debtId, debtName, currentBalance, minimumPayment) {
    console.log(`💰 Opening payment modal for debt: ${debtName} (ID: ${debtId})`);
    
    debtState.currentDebtId = debtId;
    debtState.currentDebtName = debtName;
    
    // Set modal title
    const modalTitle = document.getElementById('paymentModalLabel');
    if (modalTitle) {
        modalTitle.textContent = `Make Payment to ${debtName}`;
    }
    
    // Set debt name in the note section
    const debtNameDisplay = document.getElementById('debtNameDisplay');
    if (debtNameDisplay) {
        debtNameDisplay.textContent = debtName;
    }

    // Set current balance display
    const balanceDisplay = document.getElementById('currentBalanceDisplay');
    if (balanceDisplay) {
        balanceDisplay.textContent = `$${parseFloat(currentBalance).toFixed(2)}`;
    }
    
    // Set minimum payment display
    const minPaymentDisplay = document.getElementById('minimumPaymentDisplay');
    if (minPaymentDisplay && minimumPayment) {
        minPaymentDisplay.textContent = `Minimum: $${parseFloat(minimumPayment).toFixed(2)}`;
    }
    
    // Reset form
    const form = document.getElementById('paymentForm');
    if (form) {
        form.reset();
        
        // Set defaults
        document.getElementById('paymentDate').value = FinanceUtils.getTodaysDate();
        document.getElementById('paymentDescription').value = `Payment to ${debtName}`;
        document.getElementById('paymentType').value = 'Needs';
        
        // Populate dropdowns
        populatePaymentDropdowns();
    }
    
    // Show modal
    const modal = document.getElementById('paymentModal');
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Populate payment form dropdowns
function populatePaymentDropdowns() {
    console.log('📋 Populating payment dropdowns...');
    
    // Populate accounts
    const accountSelect = document.getElementById('paymentAccount');
    if (accountSelect && debtState.formData.accounts) {
        accountSelect.innerHTML = '<option value="">Select account...</option>';
        debtState.formData.accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account;
            option.textContent = account;
            accountSelect.appendChild(option);
        });
    }
    
    // Populate owners
    const ownerSelect = document.getElementById('paymentOwner');
    if (ownerSelect && debtState.formData.owners) {
        ownerSelect.innerHTML = '<option value="">Select owner...</option>';
        debtState.formData.owners.forEach(owner => {
            const option = document.createElement('option');
            option.value = owner;
            option.textContent = owner;
            ownerSelect.appendChild(option);
        });
    }
}

// Submit payment
function submitPayment() {
    console.log('💸 Submitting payment...');
    
    // Get form values
    const form = document.getElementById('paymentForm');
    if (!form) return;
    
    // Validate form
    if (!validatePaymentForm()) {
        return;
    }
    
    // Prepare payment data
    const paymentData = {
        debt_id: debtState.currentDebtId,
        date: document.getElementById('paymentDate').value,
        amount: parseFloat(document.getElementById('paymentAmount').value),
        description: document.getElementById('paymentDescription').value,
        account_name: document.getElementById('paymentAccount').value,
        owner: document.getElementById('paymentOwner').value,
        type: document.getElementById('paymentType').value,
        is_business: document.getElementById('paymentIsBusiness').checked
    };
    
    console.log('💸 Payment data:', paymentData);
    
    // Disable submit button
    const submitBtn = document.getElementById('submitPaymentBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
    }
    
    // Submit payment
    FinanceUtils.apiCall(`/debts/api/make_payment/${debtState.currentDebtId}`, {
        method: 'POST',
        body: JSON.stringify(paymentData)
    })
    .then(result => {
        if (result.success) {
            console.log('✅ Payment successful:', result);
            
            // Update UI
            updateDebtDisplay(debtState.currentDebtId, result.new_balance);
            
            // Show success message
            showDebtNotification(result.message, 'success');
            
            // Hide modal
            const modal = document.getElementById('paymentModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
        } else {
            showDebtNotification(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Error submitting payment:', error);
        FinanceUtils.showAlert('Error processing payment', 'danger');
    })
    .finally(() => {
        // Re-enable submit button
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '💰 Submit Payment';
        }
    });
}

// Validate payment form
function validatePaymentForm() {
    console.log('🔍 Validating payment form...');
    
    let isValid = true;
    const errors = [];
    
    // Check required fields
    const requiredFields = [
        { id: 'paymentDate', name: 'Date' },
        { id: 'paymentAmount', name: 'Amount' },
        { id: 'paymentDescription', name: 'Description' },
        { id: 'paymentAccount', name: 'Account' },
        { id: 'paymentOwner', name: 'Owner' }
    ];
    
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
    const amountInput = document.getElementById('paymentAmount');
    if (amountInput && amountInput.value) {
        const amount = parseFloat(amountInput.value);
        if (amount <= 0 || isNaN(amount)) {
            errors.push('Payment amount must be greater than zero');
            amountInput.classList.add('is-invalid');
            isValid = false;
        }
        
        // Check if amount exceeds current balance
        const currentBalance = parseFloat(document.getElementById('currentBalanceDisplay').textContent.replace('$', ''));
        if (amount > currentBalance) {
            if (!confirm(`Payment amount ($${amount.toFixed(2)}) exceeds current balance ($${currentBalance.toFixed(2)}). Continue anyway?`)) {
                errors.push('Payment amount exceeds current balance');
                amountInput.classList.add('is-invalid');
                isValid = false;
            }
        }
    }
    
    // Show errors if any
    if (!isValid) {
        FinanceUtils.showAlert('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
    }
    
    return isValid;
}

// Update debt display after payment
function updateDebtDisplay(debtId, newBalance) {
    console.log(`📊 Updating debt display for ID ${debtId}, new balance: $${newBalance}`);
    
    // Find the debt row
    const debtRows = document.querySelectorAll('tbody tr');
    debtRows.forEach(row => {
        const paymentBtn = row.querySelector(`button[onclick*="showPaymentModal(${debtId}"]`);
        if (paymentBtn) {
            // Update current balance
            const balanceCell = row.querySelector('td:nth-child(4)');
            if (balanceCell) {
                balanceCell.innerHTML = `<span class="fw-bold text-danger">$${parseFloat(newBalance).toFixed(2)}</span>`;
            }
            
            // Update progress bar
            const progressCell = row.querySelector('td:nth-child(8)');
            if (progressCell) {
                const progressBar = progressCell.querySelector('.progress-bar');
                const originalBalanceCell = row.querySelector('td:nth-child(4)'); // This needs to be extracted from button onclick
                
                // Extract original balance from payment button onclick
                const onclickStr = paymentBtn.getAttribute('onclick');
                const match = onclickStr.match(/showPaymentModal\(\d+,\s*'[^']+',\s*[\d.]+,\s*[\d.]+,\s*([\d.]+)\)/);
                if (match) {
                    const originalBalance = parseFloat(match[1]);
                    const progress = ((originalBalance - newBalance) / originalBalance * 100);
                    
                    if (progressBar) {
                        progressBar.style.width = progress + '%';
                        progressBar.setAttribute('aria-valuenow', progress);
                        progressBar.textContent = progress.toFixed(1) + '%';
                    }
                    
                    // Update paid off amount
                    const paidOffSmall = progressCell.querySelector('small');
                    if (paidOffSmall) {
                        paidOffSmall.textContent = `$${(originalBalance - newBalance).toFixed(2)} paid off`;
                    }
                }
            }
            
            // Update payment button with new balance
            paymentBtn.setAttribute('onclick', 
                paymentBtn.getAttribute('onclick').replace(/showPaymentModal\((\d+),\s*'([^']+)',\s*[\d.]+/, 
                `showPaymentModal($1, '$2', ${newBalance}`)
            );
        }
    });
}

// Add new account option
function addNewPaymentAccount() {
    const newAccount = prompt('Enter new account name:');
    if (newAccount && newAccount.trim()) {
        const accountSelect = document.getElementById('paymentAccount');
        if (accountSelect) {
            const option = new Option(newAccount.trim(), newAccount.trim());
            accountSelect.add(option);
            accountSelect.value = newAccount.trim();
            accountSelect.classList.add('is-valid');
        }
        debtState.formData.accounts.push(newAccount.trim());
        FinanceUtils.showAlert(`Account "${newAccount.trim()}" added`, 'success');
    }
}

// Add new owner option
function addNewPaymentOwner() {
    const newOwner = prompt('Enter new owner name:');
    if (newOwner && newOwner.trim()) {
        const ownerSelect = document.getElementById('paymentOwner');
        if (ownerSelect) {
            const option = new Option(newOwner.trim(), newOwner.trim());
            ownerSelect.add(option);
            ownerSelect.value = newOwner.trim();
            ownerSelect.classList.add('is-valid');
        }
        debtState.formData.owners.push(newOwner.trim());
        FinanceUtils.showAlert(`Owner "${newOwner.trim()}" added`, 'success');
    }
}

// Clear form validation
function clearPaymentValidation() {
    const form = document.getElementById('paymentForm');
    if (form) {
        const fields = form.querySelectorAll('.is-valid, .is-invalid');
        fields.forEach(field => {
            field.classList.remove('is-valid', 'is-invalid');
        });
    }
}

// Edit debt account
function editDebt(debtId) {
    console.log(`✏️ Editing debt ID: ${debtId}`);
    
    // Set the debt ID
    document.getElementById('editDebtId').value = debtId;
    
    // Set modal title
    const modalTitle = document.getElementById('editDebtModalLabel');
    modalTitle.textContent = 'Loading debt details...';
    
    // Show modal first
    const modal = document.getElementById('editDebtModal');
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
    
    // Load debt details
    FinanceUtils.apiCall(`/debts/api/get_debt/${debtId}`)
        .then(result => {
            if (result.success) {
                console.log('✅ Loaded debt details:', result.debt);
                populateEditForm(result.debt);
                modalTitle.textContent = `Edit Debt Account: ${result.debt.name}`;
            } else {
                FinanceUtils.showAlert(`Error loading debt: ${result.error}`, 'danger');
                // Close modal on error
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
        })
        .catch(error => {
            console.error('❌ Error loading debt:', error);
            FinanceUtils.showAlert('Error loading debt details', 'danger');
            // Close modal on error
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        });
}

// Populate edit form with debt data
function populateEditForm(debt) {
    console.log('📝 Populating edit form with debt data');
    
    // Basic Information
    document.getElementById('editName').value = debt.name;
    document.getElementById('editDebtType').value = debt.debt_type;
    document.getElementById('editOwner').value = debt.owner;
    document.getElementById('editAccountNumberLast4').value = debt.account_number_last4 || '';
    
    // Financial Details
    document.getElementById('editOriginalBalance').value = debt.original_balance;
    document.getElementById('editCurrentBalance').value = debt.current_balance;
    
    // Interest rate - convert from decimal to percentage for display
    if (debt.interest_rate) {
        document.getElementById('editInterestRate').value = (debt.interest_rate * 100).toFixed(2);
    } else {
        document.getElementById('editInterestRate').value = '';
    }
    
    document.getElementById('editMinimumPayment').value = debt.minimum_payment || '';
    
    // Payment & Category
    document.getElementById('editDueDate').value = debt.due_date || '';
    document.getElementById('editCategory').value = debt.category;
}

// Save debt edits
function saveDebtEdit() {
    console.log('💾 Saving debt edits...');
    
    // Validate form
    if (!validateEditForm()) {
        return;
    }
    
    const debtId = document.getElementById('editDebtId').value;
    
    // Prepare update data
    const updateData = {
        name: document.getElementById('editName').value.trim(),
        debt_type: document.getElementById('editDebtType').value,
        owner: document.getElementById('editOwner').value,
        account_number_last4: document.getElementById('editAccountNumberLast4').value.trim() || null,
        original_balance: parseFloat(document.getElementById('editOriginalBalance').value),
        current_balance: parseFloat(document.getElementById('editCurrentBalance').value),
        interest_rate: document.getElementById('editInterestRate').value ? 
            parseFloat(document.getElementById('editInterestRate').value) / 100 : null,
        minimum_payment: document.getElementById('editMinimumPayment').value ? 
            parseFloat(document.getElementById('editMinimumPayment').value) : null,
        due_date: document.getElementById('editDueDate').value ? 
            parseInt(document.getElementById('editDueDate').value) : null,
        category: document.getElementById('editCategory').value
    };
    
    console.log('📊 Update data:', updateData);
    
    // Disable save button
    const saveBtn = document.getElementById('saveDebtEditBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    }
    
    // Submit update
    FinanceUtils.apiCall(`/debts/api/update_debt/${debtId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
    })
    .then(result => {
        if (result.success) {
            console.log('✅ Debt updated successfully');
            FinanceUtils.showAlert(result.message, 'success');
            
            // Hide modal
            const modal = document.getElementById('editDebtModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
            
            // Reload page to show updates
            refreshDebtRow(debtId, updateData);
            showDebtNotification(`Debt account "${updateData.name}" updated successfully!`, 'success');;
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Error updating debt:', error);
        FinanceUtils.showAlert('Error updating debt account', 'danger');
    })
    .finally(() => {
        // Re-enable save button
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '💾 Save Changes';
        }
    });
}

// Validate edit form
function validateEditForm() {
    console.log('🔍 Validating edit form...');
    
    let isValid = true;
    const errors = [];
    
    // Check required fields
    const requiredFields = [
        { id: 'editName', name: 'Account Name' },
        { id: 'editDebtType', name: 'Debt Type' },
        { id: 'editOwner', name: 'Owner' },
        { id: 'editOriginalBalance', name: 'Original Balance' },
        { id: 'editCurrentBalance', name: 'Current Balance' },
        { id: 'editCategory', name: 'Category' }
    ];
    
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
    
    // Validate balances
    const originalBalance = parseFloat(document.getElementById('editOriginalBalance').value);
    const currentBalance = parseFloat(document.getElementById('editCurrentBalance').value);
    
    if (isNaN(originalBalance) || originalBalance < 0) {
        errors.push('Original balance must be a valid positive number');
        document.getElementById('editOriginalBalance').classList.add('is-invalid');
        isValid = false;
    }
    
    if (isNaN(currentBalance) || currentBalance < 0) {
        errors.push('Current balance must be a valid positive number');
        document.getElementById('editCurrentBalance').classList.add('is-invalid');
        isValid = false;
    }
    
    // Validate interest rate if provided
    const interestRateInput = document.getElementById('editInterestRate');
    if (interestRateInput.value) {
        const interestRate = parseFloat(interestRateInput.value);
        if (isNaN(interestRate) || interestRate < 0 || interestRate > 100) {
            errors.push('Interest rate must be between 0 and 100');
            interestRateInput.classList.add('is-invalid');
            isValid = false;
        }
    }
    
    // Show errors if any
    if (!isValid) {
        FinanceUtils.showAlert('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
    }
    
    return isValid;
}

// Update the debt summary cards after payment/edit
function updateDebtSummaryCards() {
    console.log('📊 Updating debt summary cards...');
    
    // Calculate new totals from the table
    let totalDebt = 0;
    let totalMinimumPayments = 0;
    let activeAccounts = 0;
    
    const debtRows = document.querySelectorAll('tbody tr');
    debtRows.forEach(row => {
        // Skip if no data
        if (!row.querySelector('td:nth-child(4)')) return;
        
        activeAccounts++;
        
        // Get current balance
        const balanceText = row.querySelector('td:nth-child(4)').textContent;
        const balance = parseFloat(balanceText.replace(/[$,]/g, ''));
        if (!isNaN(balance)) {
            totalDebt += balance;
        }
        
        // Get minimum payment
        const minPaymentText = row.querySelector('td:nth-child(5)').textContent;
        const minPayment = parseFloat(minPaymentText.replace(/[$,]/g, ''));
        if (!isNaN(minPayment)) {
            totalMinimumPayments += minPayment;
        }
    });
    
    // Update the metric cards
    const totalDebtCard = document.querySelector('.metric-card.debt-card .metric-value');
    if (totalDebtCard) {
        totalDebtCard.textContent = `$${totalDebt.toFixed(2)}`;
    }
    
    const minPaymentsCard = document.querySelector('.metric-card:nth-child(2) .metric-value');
    if (minPaymentsCard) {
        minPaymentsCard.textContent = `$${totalMinimumPayments.toFixed(2)}`;
    }
    
    const accountsCard = document.querySelector('.metric-card:nth-child(3) .metric-value');
    if (accountsCard) {
        accountsCard.textContent = activeAccounts;
    }
}

// Enhanced updateDebtDisplay function
function updateDebtDisplayEnhanced(debtId, newBalance) {
    console.log(`📊 Updating debt display for ID ${debtId}, new balance: $${newBalance}`);
    
    // Find the debt row
    const debtRows = document.querySelectorAll('tbody tr');
    debtRows.forEach(row => {
        const paymentBtn = row.querySelector(`button[onclick*="showPaymentModal(${debtId}"]`);
        if (paymentBtn) {
            // Get original balance from the row data
            const progressBar = row.querySelector('.progress-bar');
            const originalBalanceText = row.querySelector('small').textContent;
            const paidMatch = originalBalanceText.match(/\$([\d,]+\.?\d*) paid off/);
            const paidAmount = paidMatch ? parseFloat(paidMatch[1].replace(/,/g, '')) : 0;
            const originalBalance = newBalance + paidAmount;
            
            // Update current balance with formatting
            const balanceCell = row.querySelector('td:nth-child(4)');
            if (balanceCell) {
                balanceCell.innerHTML = `<span class="fw-bold text-danger">$${newBalance.toFixed(2)}</span>`;
            }
            
            // Update progress bar
            if (progressBar && originalBalance > 0) {
                const progress = ((originalBalance - newBalance) / originalBalance * 100);
                progressBar.style.width = progress + '%';
                progressBar.setAttribute('aria-valuenow', progress);
                progressBar.textContent = progress.toFixed(1) + '%';
                
                // Change color based on progress
                progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
                if (progress >= 75) {
                    progressBar.classList.add('bg-success');
                } else if (progress >= 50) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-danger');
                }
            }
            
            // Update paid off amount
            const paidOffSmall = row.querySelector('td:nth-child(8) small');
            if (paidOffSmall) {
                paidOffSmall.textContent = `$${(originalBalance - newBalance).toFixed(2)} paid off`;
            }
            
            // Update payment button with new balance
            const onclickStr = paymentBtn.getAttribute('onclick');
            const newOnclick = onclickStr.replace(/showPaymentModal\(\d+,\s*'[^']+',\s*[\d.]+/, 
                `showPaymentModal(${debtId}, '${paymentBtn.getAttribute('onclick').match(/'([^']+)'/)[1]}', ${newBalance}`);
            paymentBtn.setAttribute('onclick', newOnclick);
            
            // Check if debt is paid off
            if (newBalance <= 0) {
                row.classList.add('table-success');
                balanceCell.innerHTML = `<span class="fw-bold text-success">$0.00 - PAID OFF! 🎉</span>`;
            }
        }
    });
    
    // Update summary cards
    updateDebtSummaryCards();
}

// Replace the original updateDebtDisplay with this enhanced version
updateDebtDisplay = updateDebtDisplayEnhanced;

// Initialize debt charts on page load
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/debts')) {
        console.log('💳 Loading debt management...');
        loadFormData();
        
        // Initialize debt charts if Plotly is available
        if (typeof Plotly !== 'undefined') {
            setTimeout(loadDebtCharts, 500);
        }
    }
});

// Load debt charts
function loadDebtCharts() {
    console.log('📊 Loading debt charts...');
    
    // Get data from the table
    const debtData = [];
    const debtRows = document.querySelectorAll('tbody tr');
    
    debtRows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 8) {
            const type = cells[1].textContent.trim();
            const owner = cells[2].textContent.trim();
            const balanceText = cells[3].textContent.trim();
            const balance = parseFloat(balanceText.replace(/[$,]/g, ''));
            
            if (!isNaN(balance) && balance > 0) {
                debtData.push({ type, owner, balance });
            }
        }
    });
    
    if (debtData.length > 0) {
        createDebtByTypeChart(debtData);
        createDebtByOwnerChart(debtData);
    }
}

// Create debt by type chart
function createDebtByTypeChart(debtData) {
    const typeData = {};
    debtData.forEach(debt => {
        if (!typeData[debt.type]) {
            typeData[debt.type] = 0;
        }
        typeData[debt.type] += debt.balance;
    });
    
    const data = [{
        labels: Object.keys(typeData),
        values: Object.values(typeData),
        type: 'pie',
        hole: 0.4,
        textinfo: 'label+percent',
        textposition: 'outside',
        marker: {
            colors: ['#e74c3c', '#f39c12', '#27ae60', '#3498db', '#9b59b6', '#e67e22']
        }
    }];
    
    const layout = {
        showlegend: true,
        height: 300,
        margin: { t: 20, r: 20, b: 20, l: 20 }
    };
    
    Plotly.newPlot('debtByTypeChart', data, layout, { responsive: true });
}

// Create debt by owner chart
function createDebtByOwnerChart(debtData) {
    const ownerData = {};
    debtData.forEach(debt => {
        if (!ownerData[debt.owner]) {
            ownerData[debt.owner] = 0;
        }
        ownerData[debt.owner] += debt.balance;
    });
    
    const data = [{
        x: Object.keys(ownerData),
        y: Object.values(ownerData),
        type: 'bar',
        marker: {
            color: '#3498db',
            opacity: 0.8
        },
        text: Object.values(ownerData).map(val => `$${val.toFixed(2)}`),
        textposition: 'outside'
    }];
    
    const layout = {
        xaxis: { title: 'Owner' },
        yaxis: { title: 'Total Debt ($)' },
        height: 300,
        margin: { t: 20, r: 20, b: 40, l: 60 }
    };
    
    Plotly.newPlot('debtByOwnerChart', data, layout, { responsive: true });
}

// Enhanced notification function
function showDebtNotification(message, type = 'success') {
    // Remove any existing notifications
    const existingAlerts = document.querySelectorAll('.debt-notification');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new notification
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show debt-notification`;
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    const icon = type === 'success' ? '✅' : type === 'danger' ? '❌' : 'ℹ️';
    alertDiv.innerHTML = `
        ${icon} ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }
    }, 5000);
}

// Enhanced payment validation
function validatePaymentFormEnhanced() {
    console.log('🔍 Validating payment form with enhanced checks...');
    
    let isValid = true;
    const errors = [];
    const warnings = [];
    
    // Check required fields (existing code)
    const requiredFields = [
        { id: 'paymentDate', name: 'Date' },
        { id: 'paymentAmount', name: 'Amount' },
        { id: 'paymentDescription', name: 'Description' },
        { id: 'paymentAccount', name: 'Account' },
        { id: 'paymentOwner', name: 'Owner' }
    ];
    
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
    
    // Enhanced amount validation
    const amountInput = document.getElementById('paymentAmount');
    if (amountInput && amountInput.value) {
        const amount = parseFloat(amountInput.value);
        const currentBalance = parseFloat(document.getElementById('currentBalanceDisplay').textContent.replace('$', ''));
        const minimumPaymentText = document.getElementById('minimumPaymentDisplay').textContent;
        const minimumPayment = minimumPaymentText ? parseFloat(minimumPaymentText.replace(/[^0-9.-]+/g, '')) : 0;
        
        if (amount <= 0 || isNaN(amount)) {
            errors.push('Payment amount must be greater than zero');
            amountInput.classList.add('is-invalid');
            isValid = false;
        } else {
            // Check for overpayment
            if (amount > currentBalance) {
                const overpayment = amount - currentBalance;
                warnings.push(`This payment will overpay by $${overpayment.toFixed(2)}. The balance will become -$${overpayment.toFixed(2)}.`);
            }
            
            // Check for minimum payment
            if (minimumPayment > 0 && amount < minimumPayment) {
                warnings.push(`This payment is less than the minimum payment of $${minimumPayment.toFixed(2)}.`);
            }
            
            // Check if this will pay off the debt
            if (Math.abs(amount - currentBalance) < 0.01) {
                warnings.push('This payment will pay off the entire debt! 🎉');
            }
        }
    }
    
    // Date validation - check if payment date is in the future
    const dateInput = document.getElementById('paymentDate');
    if (dateInput && dateInput.value) {
        const paymentDate = new Date(dateInput.value);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        if (paymentDate > today) {
            warnings.push('Payment date is in the future. This payment will be recorded as a future payment.');
        }
    }
    
    // Show warnings if any
    if (warnings.length > 0 && isValid) {
        const warningMessage = warnings.join('\n\n');
        if (!confirm(`⚠️ Warning:\n\n${warningMessage}\n\nDo you want to continue?`)) {
            isValid = false;
        }
    }
    
    // Show errors if any
    if (!isValid && errors.length > 0) {
        showDebtNotification('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
    }
    
    return isValid;
}

// Refresh debt row after edit
function refreshDebtRow(debtId, debtData) {
    console.log(`🔄 Refreshing debt row for ID ${debtId}`);
    
    const debtRows = document.querySelectorAll('tbody tr');
    debtRows.forEach(row => {
        const editBtn = row.querySelector(`button[onclick*="editDebt(${debtId})"]`);
        if (editBtn) {
            // Update name
            const nameCell = row.querySelector('td:first-child');
            if (nameCell) {
                let nameHtml = `<div class="fw-bold">${debtData.name}</div>`;
                if (debtData.account_number_last4) {
                    nameHtml += `<small class="text-muted">****${debtData.account_number_last4}</small>`;
                }
                nameCell.innerHTML = nameHtml;
            }
            
            // Update type
            const typeCell = row.querySelector('td:nth-child(2)');
            if (typeCell) {
                typeCell.innerHTML = `<span class="badge bg-secondary">${debtData.debt_type}</span>`;
            }
            
            // Update owner
            const ownerCell = row.querySelector('td:nth-child(3)');
            if (ownerCell) {
                ownerCell.textContent = debtData.owner;
            }
            
            // Update current balance
            const balanceCell = row.querySelector('td:nth-child(4)');
            if (balanceCell) {
                balanceCell.innerHTML = `<span class="fw-bold text-danger">$${parseFloat(debtData.current_balance).toFixed(2)}</span>`;
            }
            
            // Update minimum payment
            const minPaymentCell = row.querySelector('td:nth-child(5)');
            if (minPaymentCell) {
                if (debtData.minimum_payment) {
                    minPaymentCell.textContent = `$${parseFloat(debtData.minimum_payment).toFixed(2)}`;
                } else {
                    minPaymentCell.innerHTML = '<span class="text-muted">Not set</span>';
                }
            }
            
            // Update interest rate
            const interestCell = row.querySelector('td:nth-child(6)');
            if (interestCell) {
                if (debtData.interest_rate) {
                    interestCell.textContent = `${(parseFloat(debtData.interest_rate) * 100).toFixed(2)}%`;
                } else {
                    interestCell.innerHTML = '<span class="text-muted">Not set</span>';
                }
            }
            
            // Update due date
            const dueDateCell = row.querySelector('td:nth-child(7)');
            if (dueDateCell) {
                if (debtData.due_date) {
                    const suffix = debtData.due_date == 1 || debtData.due_date == 21 || debtData.due_date == 31 ? 'st' :
                                  debtData.due_date == 2 || debtData.due_date == 22 ? 'nd' :
                                  debtData.due_date == 3 || debtData.due_date == 23 ? 'rd' : 'th';
                    dueDateCell.textContent = `${debtData.due_date}${suffix}`;
                } else {
                    dueDateCell.innerHTML = '<span class="text-muted">Not set</span>';
                }
            }
            
            // Flash the row to indicate update
            row.style.backgroundColor = 'rgba(39, 174, 96, 0.1)';
            setTimeout(() => {
                row.style.backgroundColor = '';
            }, 1000);
        }
    });
    
    // Update summary cards
    updateDebtSummaryCards();
    
    // Reload charts
    if (typeof Plotly !== 'undefined') {
        loadDebtCharts();
    }
}



// Replace the original validatePaymentForm with this enhanced version
validatePaymentForm = validatePaymentFormEnhanced;

// Export functions for global access
window.editDebt = editDebt;
window.saveDebtEdit = saveDebtEdit;

// Export functions for global access
window.showPaymentModal = showPaymentModal;
window.submitPayment = submitPayment;
window.addNewPaymentAccount = addNewPaymentAccount;
window.addNewPaymentOwner = addNewPaymentOwner;