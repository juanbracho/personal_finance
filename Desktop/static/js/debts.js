/* Debt Management JavaScript */

// Debt management state
let debtState = {
    currentDebtId: null,
    currentDebtName: null,
    formData: {
        accounts: [],
        owners: []
    },
    paymentHistory: {
        currentView: 'all',  // 'charges', 'payments', or 'all'
        data: null
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

    // Load unpaid charges
    loadUnpaidCharges(debtId);

    // Show modal
    const modal = document.getElementById('paymentModal');
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Load unpaid charges for payment modal
function loadUnpaidCharges(debtId) {
    console.log(`💳 Loading unpaid charges for debt ID ${debtId}...`);

    // Create/update charge selection dropdown
    const amountField = document.getElementById('paymentAmount').closest('.col-md-6');
    let chargeSelectContainer = document.getElementById('chargeSelectContainer');

    if (!chargeSelectContainer) {
        chargeSelectContainer = document.createElement('div');
        chargeSelectContainer.id = 'chargeSelectContainer';
        chargeSelectContainer.className = 'col-md-12 mb-3';
        amountField.parentNode.insertBefore(chargeSelectContainer, amountField);
    }

    chargeSelectContainer.innerHTML = `
        <label for="paymentChargeId" class="form-label">Pay Specific Charge (Optional)</label>
        <select class="form-select" id="paymentChargeId" onchange="handleChargeSelection()">
            <option value="">Loading charges...</option>
        </select>
        <div class="form-text">Select a specific charge to pay, or leave as "General Payment"</div>
    `;

    // Fetch unpaid charges
    FinanceUtils.apiCall(`/debts/api/unpaid_charges/${debtId}`)
        .then(result => {
            if (result.success) {
                console.log(`✅ Loaded ${result.count} unpaid charges`);
                populateChargeDropdown(result.charges);
            } else {
                console.error('❌ Error loading charges:', result.error);
                populateChargeDropdown([]);
            }
        })
        .catch(error => {
            console.error('❌ Error fetching unpaid charges:', error);
            populateChargeDropdown([]);
        });
}

// Populate charge dropdown
function populateChargeDropdown(charges) {
    const chargeSelect = document.getElementById('paymentChargeId');
    if (!chargeSelect) return;

    chargeSelect.innerHTML = '<option value="">General Payment (no specific charge)</option>';

    charges.forEach(charge => {
        const option = document.createElement('option');
        option.value = charge.id;
        option.dataset.amount = charge.charge_amount;
        option.dataset.description = charge.description;
        option.textContent = `${charge.description} - $${charge.charge_amount.toFixed(2)} (${charge.charge_date})`;
        chargeSelect.appendChild(option);
    });

    // If only one unpaid charge, auto-select it
    if (charges.length === 1) {
        chargeSelect.value = charges[0].id;
        handleChargeSelection();
    }
}

// Handle charge selection
function handleChargeSelection() {
    const chargeSelect = document.getElementById('paymentChargeId');
    const amountInput = document.getElementById('paymentAmount');
    const descriptionInput = document.getElementById('paymentDescription');

    if (!chargeSelect || !amountInput) return;

    const selectedOption = chargeSelect.options[chargeSelect.selectedIndex];

    if (selectedOption.value) {
        // Specific charge selected - auto-fill amount and update description
        const chargeAmount = parseFloat(selectedOption.dataset.amount);
        const chargeDescription = selectedOption.dataset.description;

        amountInput.value = chargeAmount.toFixed(2);
        descriptionInput.value = `Payment for ${chargeDescription}`;

        console.log(`💳 Selected charge: ${chargeDescription} - $${chargeAmount}`);
    } else {
        // General payment - clear amount, keep default description
        amountInput.value = '';
        descriptionInput.value = `Payment to ${debtState.currentDebtName}`;
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
    const chargeSelect = document.getElementById('paymentChargeId');
    const paymentData = {
        debt_id: debtState.currentDebtId,
        date: document.getElementById('paymentDate').value,
        amount: parseFloat(document.getElementById('paymentAmount').value),
        description: document.getElementById('paymentDescription').value,
        account_name: document.getElementById('paymentAccount').value,
        owner: document.getElementById('paymentOwner').value,
        type: document.getElementById('paymentType').value,
        is_business: document.getElementById('paymentType').value === 'Business'
    };

    // Add debt_charge_id if specific charge selected
    if (chargeSelect && chargeSelect.value) {
        paymentData.debt_charge_id = parseInt(chargeSelect.value);
        console.log(`💳 Paying specific charge ID: ${paymentData.debt_charge_id}`);
    }
    
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
            updateDebtDisplay(debtState.currentDebtId, result.new_balance, result.is_paid_off);

            // Show success message
            showDebtNotification(result.message, 'success');

            // Hide modal
            const modal = document.getElementById('paymentModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }

            // If debt is paid off and we're not showing paid-off debts, reload page
            if (result.is_paid_off) {
                const url = new URL(window.location.href);
                const showPaidOff = url.searchParams.get('show_paid_off') === 'true';

                if (!showPaidOff) {
                    // Reload page after a short delay to show the success message
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
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

// Validate payment form with enhanced checks
function validatePaymentForm() {
    console.log('🔍 Validating payment form with enhanced checks...');

    let isValid = true;
    const errors = [];
    const warnings = [];

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
                warnings.push('🎉 This payment will pay off the entire debt!');
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

    // Show warnings and ask for confirmation if any
    if (warnings.length > 0 && isValid) {
        const warningMessage = warnings.join('\n\n');
        const confirmed = confirm(`⚠️ Warning:\n\n${warningMessage}\n\nDo you want to continue?`);
        if (!confirmed) {
            console.log('❌ User cancelled payment after warning');
            return false;
        }
    }

    // Show errors if any
    if (!isValid && errors.length > 0) {
        showDebtNotification('Please fix the following errors:\n• ' + errors.join('\n• '), 'danger');
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

// Show payment history modal
function showPaymentHistory(debtId, debtName) {
    console.log(`📊 Opening payment history for debt: ${debtName} (ID: ${debtId})`);

    // Set modal title
    const modalTitle = document.getElementById('paymentHistoryModalLabel');
    if (modalTitle) {
        modalTitle.textContent = `Payment History - ${debtName}`;
    }

    // Show modal
    const modal = document.getElementById('paymentHistoryModal');
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    // Show loading state
    const tableBody = document.getElementById('paymentHistoryTableBody');
    const emptyState = document.getElementById('paymentHistoryEmpty');

    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
            </tr>
        `;
    }

    if (emptyState) {
        emptyState.style.display = 'none';
    }

    // Fetch payment history
    FinanceUtils.apiCall(`/debts/api/payment_history/${debtId}`)
        .then(result => {
            if (result.success) {
                console.log('✅ Loaded payment history:', result);
                populatePaymentHistory(result);
            } else {
                console.error('❌ Error loading payment history:', result.error);
                showPaymentHistoryError(result.error || 'Failed to load payment history');
            }
        })
        .catch(error => {
            console.error('❌ Error fetching payment history:', error);
            showPaymentHistoryError('Failed to load payment history');
        });
}

// Populate payment history table
function populatePaymentHistory(data) {
    console.log('📊 Populating payment history with charges and payments');

    // Store data for view switching
    debtState.paymentHistory.data = data;

    // Update summary cards
    document.getElementById('historyOriginalBalance').textContent = `$${data.original_balance.toFixed(2)}`;
    document.getElementById('historyCurrentBalance').textContent = `$${data.current_balance.toFixed(2)}`;
    document.getElementById('historyTotalPaid').textContent = `$${data.total_paid.toFixed(2)}`;
    document.getElementById('historyTotalCharges').textContent = `$${data.total_charges.toFixed(2)}`;

    // Add toggle buttons if they don't exist
    addHistoryToggleButtons();

    // Render current view
    renderPaymentHistoryView();
}

// Add toggle buttons to payment history modal
function addHistoryToggleButtons() {
    const modalBody = document.querySelector('#paymentHistoryModal .modal-body');
    if (!modalBody) return;

    // Check if buttons already exist
    if (document.getElementById('historyViewToggle')) return;

    // Create toggle button group
    const toggleDiv = document.createElement('div');
    toggleDiv.id = 'historyViewToggle';
    toggleDiv.className = 'btn-group mb-3 w-100';
    toggleDiv.setAttribute('role', 'group');
    toggleDiv.innerHTML = `
        <button type="button" class="btn btn-outline-primary" onclick="switchHistoryView('charges')">
            📦 Charges (${debtState.paymentHistory.data?.charge_count || 0})
        </button>
        <button type="button" class="btn btn-outline-success" onclick="switchHistoryView('payments')">
            💵 Payments (${debtState.paymentHistory.data?.payment_count || 0})
        </button>
        <button type="button" class="btn btn-outline-info active" onclick="switchHistoryView('all')">
            📊 All Activity
        </button>
    `;

    // Insert before table
    const tableContainer = modalBody.querySelector('.table-responsive');
    if (tableContainer) {
        tableContainer.before(toggleDiv);
    }
}

// Switch between history views
function switchHistoryView(view) {
    console.log(`🔄 Switching to ${view} view`);
    debtState.paymentHistory.currentView = view;

    // Update button states
    const buttons = document.querySelectorAll('#historyViewToggle button');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        const btnText = btn.textContent.toLowerCase();
        if ((view === 'charges' && btnText.includes('charges')) ||
            (view === 'payments' && btnText.includes('payments')) ||
            (view === 'all' && btnText.includes('all'))) {
            btn.classList.add('active');
        }
    });

    renderPaymentHistoryView();
}

// Render payment history based on current view
function renderPaymentHistoryView() {
    const data = debtState.paymentHistory.data;
    const view = debtState.paymentHistory.currentView;

    if (!data) return;

    const tableBody = document.getElementById('paymentHistoryTableBody');
    const emptyState = document.getElementById('paymentHistoryEmpty');
    const tableHead = document.querySelector('#paymentHistoryModal thead tr');

    if (!tableBody) return;

    // Update table headers based on view
    if (tableHead) {
        if (view === 'charges') {
            tableHead.innerHTML = `
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Type</th>
                <th>Status</th>
            `;
        } else if (view === 'payments') {
            tableHead.innerHTML = `
                <th>Date</th>
                <th>Amount</th>
                <th>Balance After</th>
                <th>Type</th>
                <th>Notes</th>
            `;
        } else {  // 'all'
            tableHead.innerHTML = `
                <th>Date</th>
                <th>Type</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Balance</th>
            `;
        }
    }

    // Format currency helper
    const formatCurrency = (value) => {
        if (value === null || value === undefined) return '<span class="text-muted">-</span>';
        return `$${parseFloat(value).toFixed(2)}`;
    };

    // Format date helper
    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    // Render based on view
    if (view === 'charges') {
        if (data.charges.length === 0) {
            tableBody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        tableBody.innerHTML = '';

        data.charges.forEach(charge => {
            const row = document.createElement('tr');
            const statusBadge = charge.is_paid ?
                '<span class="badge bg-success">Paid</span>' :
                '<span class="badge bg-warning">Unpaid</span>';

            row.innerHTML = `
                <td>${formatDate(charge.charge_date)}</td>
                <td>${charge.description}</td>
                <td><span class="badge bg-secondary">${charge.category || '-'}</span></td>
                <td class="fw-bold text-danger">${formatCurrency(charge.charge_amount)}</td>
                <td><span class="badge bg-info">${charge.charge_type}</span></td>
                <td>${statusBadge}</td>
            `;
            tableBody.appendChild(row);
        });

    } else if (view === 'payments') {
        if (data.payments.length === 0) {
            tableBody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        tableBody.innerHTML = '';

        data.payments.forEach(payment => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${formatDate(payment.payment_date)}</td>
                <td class="fw-bold text-success">${formatCurrency(payment.payment_amount)}</td>
                <td>${formatCurrency(payment.balance_after_payment)}</td>
                <td><span class="badge bg-info">${payment.payment_type || 'Regular'}</span></td>
                <td><small class="text-muted">${payment.notes || '-'}</small></td>
            `;
            tableBody.appendChild(row);
        });

    } else {  // 'all' - combined view
        // Combine charges and payments, sort by date
        const allActivity = [];

        data.charges.forEach(charge => {
            allActivity.push({
                date: charge.charge_date,
                type: 'charge',
                description: charge.description,
                amount: charge.charge_amount,
                balance: null,  // We don't track balance per charge
                data: charge
            });
        });

        data.payments.forEach(payment => {
            allActivity.push({
                date: payment.payment_date,
                type: 'payment',
                description: payment.notes || 'Payment',
                amount: payment.payment_amount,
                balance: payment.balance_after_payment,
                data: payment
            });
        });

        // Sort by date descending
        allActivity.sort((a, b) => new Date(b.date) - new Date(a.date));

        if (allActivity.length === 0) {
            tableBody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        tableBody.innerHTML = '';

        allActivity.forEach(activity => {
            const row = document.createElement('tr');
            const isCharge = activity.type === 'charge';
            const typeBadge = isCharge ?
                '<span class="badge bg-danger">Charge</span>' :
                '<span class="badge bg-success">Payment</span>';
            const amountClass = isCharge ? 'text-danger' : 'text-success';
            const amountPrefix = isCharge ? '+' : '-';

            row.innerHTML = `
                <td>${formatDate(activity.date)}</td>
                <td>${typeBadge}</td>
                <td>${activity.description}</td>
                <td class="fw-bold ${amountClass}">${amountPrefix}${formatCurrency(activity.amount).replace('$', '$')}</td>
                <td>${activity.balance !== null ? formatCurrency(activity.balance) : '<span class="text-muted">-</span>'}</td>
            `;
            tableBody.appendChild(row);
        });
    }
}

// Show payment history error
function showPaymentHistoryError(message) {
    const tableBody = document.getElementById('paymentHistoryTableBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </td>
            </tr>
        `;
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

    // Calculate new totals from the table (only active debts)
    let totalDebt = 0;
    let totalMinimumPayments = 0;
    let activeAccounts = 0;

    const debtRows = document.querySelectorAll('tbody tr');
    debtRows.forEach(row => {
        // Skip if no data
        if (!row.querySelector('td:nth-child(4)')) return;

        // Skip paid-off debts (check for "Paid Off" badge or table-success class)
        const isPaidOff = row.classList.contains('table-success') ||
                         row.querySelector('.badge.bg-success[textContent="Paid Off"]');
        if (isPaidOff) return;

        activeAccounts++;

        // Get current balance
        const balanceText = row.querySelector('td:nth-child(4)').textContent;
        const balance = parseFloat(balanceText.replace(/[$,]/g, ''));
        if (!isNaN(balance) && balance > 0) {
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
function updateDebtDisplayEnhanced(debtId, newBalance, isPaidOff = false) {
    console.log(`📊 Updating debt display for ID ${debtId}, new balance: $${newBalance}, paid off: ${isPaidOff}`);

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
                if (isPaidOff) {
                    balanceCell.innerHTML = `<span class="fw-bold text-success">$${newBalance.toFixed(2)}</span>`;
                } else {
                    balanceCell.innerHTML = `<span class="fw-bold text-danger">$${newBalance.toFixed(2)}</span>`;
                }
            }

            // Update progress bar
            if (progressBar && originalBalance > 0) {
                const progress = ((originalBalance - newBalance) / originalBalance * 100);
                progressBar.style.width = progress + '%';
                progressBar.setAttribute('aria-valuenow', progress);
                progressBar.textContent = progress.toFixed(1) + '%';

                // Change color based on progress
                progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
                if (progress >= 100 || isPaidOff) {
                    progressBar.classList.add('bg-success');
                } else if (progress >= 75) {
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

            // Handle paid-off status
            if (isPaidOff) {
                // Add success row styling
                row.classList.add('table-success');

                // Add "Paid Off" badge to name column if not already present
                const nameCell = row.querySelector('td:first-child');
                if (nameCell && !nameCell.querySelector('.badge.bg-success')) {
                    const badgeHtml = '<span class="badge bg-success ms-2">Paid Off</span>';
                    const nameDiv = nameCell.querySelector('div.d-flex') || nameCell.querySelector('div');
                    if (nameDiv) {
                        nameDiv.insertAdjacentHTML('beforeend', badgeHtml);
                    }
                }
            } else {
                // Remove success styling if not paid off
                row.classList.remove('table-success');

                // Remove "Paid Off" badge if present
                const badge = row.querySelector('.badge.bg-success');
                if (badge && badge.textContent === 'Paid Off') {
                    badge.remove();
                }
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

// Toggle paid-off debts visibility
function togglePaidOffDebts(showPaidOff) {
    console.log(`🔄 Toggling paid-off debts: ${showPaidOff}`);

    // Reload page with query parameter
    const url = new URL(window.location.href);
    if (showPaidOff) {
        url.searchParams.set('show_paid_off', 'true');
    } else {
        url.searchParams.delete('show_paid_off');
    }

    window.location.href = url.toString();
}

// Delete debt account
function deleteDebt(debtId, debtName) {
    console.log(`🗑️ Requesting delete for debt: ${debtName} (ID: ${debtId})`);

    // Confirmation dialog
    const confirmMessage = `⚠️ Are you sure you want to delete "${debtName}"?\n\nThis will permanently delete:\n• The debt account\n• All payment history records\n\nNote: Your transaction records will be preserved.\n\nThis action CANNOT be undone!`;

    if (!confirm(confirmMessage)) {
        console.log('❌ User cancelled deletion');
        return;
    }

    // Show loading notification
    showDebtNotification(`Deleting "${debtName}"...`, 'info');

    // Call delete API
    FinanceUtils.apiCall(`/debts/api/delete_debt/${debtId}`, {
        method: 'DELETE'
    })
    .then(result => {
        if (result.success) {
            console.log('✅ Debt deleted successfully:', result);
            showDebtNotification(result.message, 'success');

            // Reload page after short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showDebtNotification(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Error deleting debt:', error);
        showDebtNotification('Error deleting debt account', 'danger');
    });
}

// Export functions for global access
window.editDebt = editDebt;
window.saveDebtEdit = saveDebtEdit;
window.showPaymentModal = showPaymentModal;
window.submitPayment = submitPayment;
window.addNewPaymentAccount = addNewPaymentAccount;
window.addNewPaymentOwner = addNewPaymentOwner;
window.showPaymentHistory = showPaymentHistory;
window.switchHistoryView = switchHistoryView;
window.handleChargeSelection = handleChargeSelection;
window.clearPaymentValidation = clearPaymentValidation;
window.togglePaidOffDebts = togglePaidOffDebts;
window.deleteDebt = deleteDebt;