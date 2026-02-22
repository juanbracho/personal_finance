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
        console.log('Loading debt management...');
        loadFormData();

        // Initialize debt charts if Plotly is available
        if (typeof Plotly !== 'undefined') {
            setTimeout(loadDebtCharts, 500);
        }
    }
});

// Load form data for dropdowns
function loadFormData() {
    console.log('Loading form data for dropdowns...');

    fetch('/transactions/api/get_form_data')
        .then(response => response.json())
        .then(data => {
            debtState.formData = data;
            console.log('Form data loaded:', data);
        })
        .catch(error => {
            console.error('Error loading form data:', error);
            // Set defaults
            debtState.formData = {
                accounts: ['Venture', 'Cacas', 'Cata'],
                owners: ['Cata', 'Suricata', 'Cacas']
            };
        });
}

// Toggle debt detail expand
function toggleDebtDetails(debtId) {
    const details = document.getElementById(`debt-details-${debtId}`);
    const btn = document.querySelector(`.debt-item[data-debt-id="${debtId}"] .debt-expand-btn`);
    if (!details) return;
    const isOpen = details.style.display !== 'none';
    details.style.display = isOpen ? 'none' : 'block';
    if (btn) btn.classList.toggle('expanded', !isOpen);
}
window.toggleDebtDetails = toggleDebtDetails;

// Show payment modal
function showPaymentModal(debtId, debtName, currentBalance, minimumPayment) {
    console.log(`Opening payment modal for debt: ${debtName} (ID: ${debtId})`);

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
    console.log(`Loading unpaid charges for debt ID ${debtId}...`);

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
                console.log(`Loaded ${result.count} unpaid charges`);
                populateChargeDropdown(result.charges);
            } else {
                console.error('Error loading charges:', result.error);
                populateChargeDropdown([]);
            }
        })
        .catch(error => {
            console.error('Error fetching unpaid charges:', error);
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

        console.log(`Selected charge: ${chargeDescription} - $${chargeAmount}`);
    } else {
        // General payment - clear amount, keep default description
        amountInput.value = '';
        descriptionInput.value = `Payment to ${debtState.currentDebtName}`;
    }
}

// Populate payment form dropdowns
function populatePaymentDropdowns() {
    console.log('Populating payment dropdowns...');

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
    console.log('Submitting payment...');

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
        console.log(`Paying specific charge ID: ${paymentData.debt_charge_id}`);
    }

    console.log('Payment data:', paymentData);

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
            console.log('Payment successful:', result);

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
        console.error('Error submitting payment:', error);
        FinanceUtils.showAlert('Error processing payment', 'danger');
    })
    .finally(() => {
        // Re-enable submit button
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Submit Payment';
        }
    });
}

// Validate payment form with enhanced checks
function validatePaymentForm() {
    console.log('Validating payment form with enhanced checks...');

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
                warnings.push('This payment will pay off the entire debt!');
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
        const confirmed = confirm(`Warning:\n\n${warningMessage}\n\nDo you want to continue?`);
        if (!confirmed) {
            console.log('User cancelled payment after warning');
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
    console.log(`Updating debt display for ID ${debtId}, new balance: $${newBalance}`);

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
                const originalBalanceCell = row.querySelector('td:nth-child(4)');

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
    console.log(`Opening payment history for debt: ${debtName} (ID: ${debtId})`);

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
                <td colspan="5" class="text-center" style="padding:24px;">
                    <div class="spinner-border" role="status" style="width:20px;height:20px;">
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
                console.log('Loaded payment history:', result);
                populatePaymentHistory(result);
            } else {
                console.error('Error loading payment history:', result.error);
                showPaymentHistoryError(result.error || 'Failed to load payment history');
            }
        })
        .catch(error => {
            console.error('Error fetching payment history:', error);
            showPaymentHistoryError('Failed to load payment history');
        });
}

// Populate payment history table
function populatePaymentHistory(data) {
    console.log('Populating payment history with charges and payments');

    // Store data for view switching
    debtState.paymentHistory.data = data;

    // Update summary strip
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
    toggleDiv.className = 'history-view-toggle';
    toggleDiv.innerHTML =
        '<button type="button" class="history-toggle-btn" onclick="switchHistoryView(\'charges\')">Charges (' + (debtState.paymentHistory.data && debtState.paymentHistory.data.charge_count || 0) + ')</button>' +
        '<button type="button" class="history-toggle-btn" onclick="switchHistoryView(\'payments\')">Payments (' + (debtState.paymentHistory.data && debtState.paymentHistory.data.payment_count || 0) + ')</button>' +
        '<button type="button" class="history-toggle-btn active" onclick="switchHistoryView(\'all\')">All Activity</button>';

    // Insert before table
    const tableContainer = modalBody.querySelector('.table-responsive');
    if (tableContainer) {
        tableContainer.before(toggleDiv);
    }
}

// Switch between history views
function switchHistoryView(view) {
    console.log(`Switching to ${view} view`);
    debtState.paymentHistory.currentView = view;

    // Update button states
    document.querySelectorAll('#historyViewToggle button').forEach(function(btn) {
        btn.classList.remove('active');
        var t = btn.textContent.toLowerCase();
        if ((view === 'charges' && t.includes('charges')) ||
            (view === 'payments' && t.includes('payments')) ||
            (view === 'all' && t.includes('all'))) {
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
                '<span class="kanso-badge kanso-badge-payment">Paid</span>' :
                '<span class="kanso-badge kanso-badge-charge">Unpaid</span>';

            row.innerHTML = `
                <td>${formatDate(charge.charge_date)}</td>
                <td>${charge.description}</td>
                <td><span class="kanso-badge kanso-badge-type">${charge.category || '-'}</span></td>
                <td style="font-weight:600;color:var(--danger);">${formatCurrency(charge.charge_amount)}</td>
                <td><span class="kanso-badge kanso-badge-type">${charge.charge_type}</span></td>
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
                <td style="font-weight:600;color:var(--success);">${formatCurrency(payment.payment_amount)}</td>
                <td>${formatCurrency(payment.balance_after_payment)}</td>
                <td><span class="kanso-badge kanso-badge-type">${payment.payment_type || 'Regular'}</span></td>
                <td style="font-size:12px;color:var(--text-muted);">${payment.notes || '-'}</td>
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
                balance: null,
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
                '<span class="kanso-badge kanso-badge-charge">Charge</span>' :
                '<span class="kanso-badge kanso-badge-payment">Payment</span>';
            const amountStyle = isCharge ? 'color:var(--danger);' : 'color:var(--success);';
            const amountPrefix = isCharge ? '+' : '-';

            row.innerHTML = `
                <td>${formatDate(activity.date)}</td>
                <td>${typeBadge}</td>
                <td>${activity.description}</td>
                <td style="font-weight:600;${amountStyle}">${amountPrefix}${formatCurrency(activity.amount).replace('$', '$')}</td>
                <td>${activity.balance !== null ? formatCurrency(activity.balance) : '<span style="color:var(--text-faint);">-</span>'}</td>
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
                <td colspan="5" class="text-center" style="color:var(--danger);padding:24px;">
                    ${message}
                </td>
            </tr>
        `;
    }
}

// Edit debt account
function editDebt(debtId) {
    console.log(`Editing debt ID: ${debtId}`);

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
                console.log('Loaded debt details:', result.debt);
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
            console.error('Error loading debt:', error);
            FinanceUtils.showAlert('Error loading debt details', 'danger');
            // Close modal on error
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        });
}

// Populate edit form with debt data
function populateEditForm(debt) {
    console.log('Populating edit form with debt data');

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
    console.log('Saving debt edits...');

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

    console.log('Update data:', updateData);

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
            console.log('Debt updated successfully');
            FinanceUtils.showAlert(result.message, 'success');

            // Hide modal
            const modal = document.getElementById('editDebtModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }

            // Reload page to show updates
            refreshDebtRow(debtId, updateData);
            showDebtNotification(`Debt account "${updateData.name}" updated successfully!`, 'success');
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error updating debt:', error);
        FinanceUtils.showAlert('Error updating debt account', 'danger');
    })
    .finally(() => {
        // Re-enable save button
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = 'Save Changes';
        }
    });
}

// Validate edit form
function validateEditForm() {
    console.log('Validating edit form...');

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
    var totalDebt = 0;
    var totalMinimumPayments = 0;

    document.querySelectorAll('.debt-item').forEach(function(row) {
        if (row.classList.contains('debt-paid-off')) return;
        var balance = parseFloat(row.dataset.debtBalance);
        if (!isNaN(balance)) totalDebt += balance;
        var minPay = parseFloat(row.dataset.minPayment);
        if (!isNaN(minPay)) totalMinimumPayments += minPay;
    });

    var totalDebtEl = document.getElementById('totalDebtValue');
    if (totalDebtEl) totalDebtEl.textContent = '$' + totalDebt.toFixed(2);
    var totalMinEl = document.getElementById('totalMinimumsValue');
    if (totalMinEl) totalMinEl.textContent = '$' + totalMinimumPayments.toFixed(2);
}

// Enhanced updateDebtDisplay function
function updateDebtDisplayEnhanced(debtId, newBalance, isPaidOff) {
    if (isPaidOff === undefined) isPaidOff = false;
    console.log(`Updating debt display for ID ${debtId}, new balance: $${newBalance}, paid off: ${isPaidOff}`);

    var row = document.querySelector('.debt-item[data-debt-id="' + debtId + '"]');
    if (!row) return;

    row.dataset.debtBalance = newBalance;
    var originalBalance = parseFloat(row.dataset.originalBalance) || 0;
    var progress = originalBalance > 0 ? ((originalBalance - newBalance) / originalBalance * 100) : 0;
    progress = Math.max(0, Math.min(100, progress));

    // Balance display
    var balanceEl = row.querySelector('.debt-balance-value');
    if (balanceEl) {
        balanceEl.textContent = '$' + newBalance.toFixed(2);
        if (isPaidOff) balanceEl.classList.add('paid-off'); else balanceEl.classList.remove('paid-off');
    }

    // Mini progress
    var miniBar = row.querySelector('.debt-progress-mini-fill');
    if (miniBar) miniBar.style.width = progress + '%';
    var miniLabel = row.querySelector('.debt-progress-mini-label');
    if (miniLabel) miniLabel.textContent = Math.round(progress) + '% paid';

    // Details: paid amount
    var paidDetail = row.querySelector('.debt-detail-paid');
    if (paidDetail) paidDetail.textContent = '$' + (originalBalance - newBalance).toFixed(2);

    // Full progress bar
    var fullBar = row.querySelector('.debt-progress-full-fill');
    if (fullBar) {
        fullBar.style.width = progress + '%';
        fullBar.textContent = progress.toFixed(1) + '%';
        fullBar.classList.remove('mid', 'high');
        if (progress >= 70) fullBar.classList.add('high');
        else if (progress >= 30) fullBar.classList.add('mid');
    }

    // Payment button onclick
    var payBtn = row.querySelector('.debt-action-btn.payment');
    if (payBtn) {
        var nameEl = row.querySelector('.debt-item-name-text');
        var debtName = nameEl ? nameEl.textContent : '';
        var minPay = row.dataset.minPayment || 'null';
        payBtn.setAttribute('onclick', 'showPaymentModal(' + debtId + ', \'' + debtName + '\', ' + newBalance + ', ' + minPay + ')');
    }

    // Paid-off visual
    if (isPaidOff) {
        row.classList.add('debt-paid-off');
        var nameArea = row.querySelector('.debt-item-name-text');
        if (nameArea && !row.querySelector('.debt-paid-badge')) {
            nameArea.insertAdjacentHTML('afterend', '<span class="debt-paid-badge">Paid Off</span>');
        }
    } else {
        row.classList.remove('debt-paid-off');
        var badge = row.querySelector('.debt-paid-badge');
        if (badge) badge.remove();
    }

    updateDebtSummaryCards();
}
updateDebtDisplay = updateDebtDisplayEnhanced;

// Load debt charts
function loadDebtCharts() {
    console.log('Loading debt charts...');

    // Read from data attributes on .debt-item elements
    const debtData = [];
    document.querySelectorAll('.debt-item').forEach(function(row) {
        var type = row.dataset.debtType;
        var owner = row.dataset.debtOwner;
        var balance = parseFloat(row.dataset.debtBalance);
        if (type && owner && !isNaN(balance) && balance > 0) {
            debtData.push({ type: type, owner: owner, balance: balance });
        }
    });

    if (debtData.length > 0) {
        createDebtByTypeChart(debtData);
        createDebtByOwnerChart(debtData);
    }
}

// Create debt by type chart
function createDebtByTypeChart(debtData) {
    var isDark = ['warm-ink','indigo'].includes(document.documentElement.dataset.theme || 'warm-ink');
    var textColor = isDark ? '#8A8278' : '#7A6F65';
    var paperBg = 'rgba(0,0,0,0)';
    var plotBg = 'rgba(0,0,0,0)';

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
            colors: ['#7BAF8E', '#C49A5E', '#6A8FBF', '#A67FB5', '#D4956A', '#E8761F']
        }
    }];

    const layout = {
        showlegend: true,
        height: 280,
        margin: { t: 20, r: 20, b: 20, l: 20 },
        font: { color: textColor, family: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif' },
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        legend: { font: { color: textColor } },
        xaxis: { color: textColor, gridcolor: isDark ? '#332E28' : '#DDD9D2' },
        yaxis: { color: textColor, gridcolor: isDark ? '#332E28' : '#DDD9D2' }
    };

    Plotly.newPlot('debtByTypeChart', data, layout, { responsive: true });
}

// Create debt by owner chart
function createDebtByOwnerChart(debtData) {
    var isDark = ['warm-ink','indigo'].includes(document.documentElement.dataset.theme || 'warm-ink');
    var textColor = isDark ? '#8A8278' : '#7A6F65';
    var paperBg = 'rgba(0,0,0,0)';
    var plotBg = 'rgba(0,0,0,0)';

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
            color: '#C49A5E',
            opacity: 0.8
        },
        text: Object.values(ownerData).map(val => `$${val.toFixed(2)}`),
        textposition: 'outside'
    }];

    const layout = {
        xaxis: { title: 'Owner', color: textColor, gridcolor: isDark ? '#332E28' : '#DDD9D2' },
        yaxis: { title: 'Total Debt ($)', color: textColor, gridcolor: isDark ? '#332E28' : '#DDD9D2' },
        height: 280,
        margin: { t: 20, r: 20, b: 40, l: 60 },
        font: { color: textColor, family: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif' },
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        legend: { font: { color: textColor } }
    };

    Plotly.newPlot('debtByOwnerChart', data, layout, { responsive: true });
}

// Kanso-styled toast notification
function showDebtNotification(message, type) {
    type = type || 'success';
    document.querySelectorAll('.debt-notification').forEach(function(el) { el.remove(); });

    var div = document.createElement('div');
    div.className = 'kanso-feedback debt-notification ' + (type === 'danger' ? 'error' : (type === 'info' ? 'info' : 'success'));
    div.style.cssText = 'position:fixed;top:70px;right:20px;z-index:9999;min-width:280px;max-width:400px;box-shadow:0 4px 24px rgba(0,0,0,0.3);';

    var icon = type === 'success' ? '\u2713' : type === 'danger' ? '\u2717' : '\u2139';
    div.innerHTML = icon + ' ' + message + ' <button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:inherit;font-size:16px;line-height:1;">\u00d7</button>';
    div.style.display = 'flex';
    div.style.alignItems = 'center';
    div.style.gap = '8px';

    document.body.appendChild(div);
    setTimeout(function() {
        if (div.parentNode) {
            div.style.opacity = '0';
            div.style.transition = 'opacity 0.3s ease';
            setTimeout(function() { div.remove(); }, 300);
        }
    }, 5000);
}

// Refresh debt row after edit
function refreshDebtRow(debtId, debtData) {
    console.log(`Refreshing debt row for ID ${debtId}`);

    var row = document.querySelector('.debt-item[data-debt-id="' + debtId + '"]');
    if (!row) return;

    row.dataset.debtType = debtData.debt_type;
    row.dataset.debtOwner = debtData.owner;
    row.dataset.debtBalance = debtData.current_balance;
    row.dataset.originalBalance = debtData.original_balance;
    row.dataset.minPayment = debtData.minimum_payment || 0;

    var nameEl = row.querySelector('.debt-item-name-text');
    if (nameEl) nameEl.textContent = debtData.name;

    var last4El = row.querySelector('.debt-item-last4');
    if (last4El) last4El.textContent = debtData.account_number_last4 ? '****' + debtData.account_number_last4 : '';

    var typeEl = row.querySelector('.debt-type-badge');
    if (typeEl) typeEl.textContent = debtData.debt_type;

    var ownerEl = row.querySelector('.debt-item-owner');
    if (ownerEl) ownerEl.textContent = debtData.owner;

    var minPayEl = row.querySelector('.debt-min-payment');
    if (minPayEl) minPayEl.textContent = debtData.minimum_payment ? '$' + parseFloat(debtData.minimum_payment).toFixed(2) : '\u2014';

    var dueStr = debtData.due_date ? ' \u00b7 due ' + debtData.due_date + 'th' : '';
    var minLabelEl = row.querySelector('.debt-min-label');
    if (minLabelEl) minLabelEl.textContent = 'min' + dueStr;

    // Flash
    row.style.background = 'var(--success-dim)';
    setTimeout(function() { row.style.background = ''; }, 1200);

    updateDebtSummaryCards();
    if (typeof Plotly !== 'undefined') loadDebtCharts();
}

// Toggle paid-off debts visibility
function togglePaidOffDebts(showPaidOff) {
    console.log(`Toggling paid-off debts: ${showPaidOff}`);

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
    console.log(`Requesting delete for debt: ${debtName} (ID: ${debtId})`);

    // Confirmation dialog
    const confirmMessage = `Are you sure you want to delete "${debtName}"?\n\nThis will permanently delete:\n- The debt account\n- All payment history records\n\nNote: Your transaction records will be preserved.\n\nThis action CANNOT be undone!`;

    if (!confirm(confirmMessage)) {
        console.log('User cancelled deletion');
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
            console.log('Debt deleted successfully:', result);
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
        console.error('Error deleting debt:', error);
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
window.toggleDebtDetails = toggleDebtDetails;
