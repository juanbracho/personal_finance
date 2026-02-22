/**
 * Bulk Transactions JavaScript
 * Handles dynamic row management, validation, and form submission
 */

let rowCounter = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize with one row
    addRow();

    // Form submit handler
    document.getElementById('bulkTransactionForm').addEventListener('submit', handleSubmit);
});

/**
 * Add a new transaction row to the table
 */
function addRow() {
    rowCounter++;
    const tbody = document.getElementById('itemsTableBody');
    const today = new Date().toISOString().split('T')[0];

    const row = document.createElement('div');
    row.id = `row-${rowCounter}`;
    row.className = 'bulk-item-row';
    row.innerHTML = `
        <div style="flex:0 0 160px;">
            <input type="date"
                   class="kanso-input item-date"
                   value="${today}"
                   data-row="${rowCounter}"
                   required>
        </div>
        <div style="flex:1;">
            <input type="text"
                   class="kanso-input item-description"
                   placeholder="Enter description..."
                   data-row="${rowCounter}"
                   required>
        </div>
        <div style="flex:0 0 160px;">
            <div class="kanso-input-group">
                <span class="kanso-input-affix prefix">$</span>
                <input type="number"
                       class="kanso-input has-prefix item-amount"
                       step="0.01"
                       placeholder="0.00"
                       data-row="${rowCounter}"
                       onchange="updateTotals()"
                       oninput="updateTotals()"
                       required>
            </div>
        </div>
        <div style="flex:0 0 36px; display:flex; align-items:center; justify-content:center;">
            <button type="button"
                    class="debt-action-btn delete"
                    onclick="removeRow(${rowCounter})"
                    title="Remove row">
                <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 10h8l1-10"/>
                </svg>
            </button>
        </div>
    `;

    tbody.appendChild(row);
    updateUI();

    // Focus on the description field of the new row
    row.querySelector('.item-description').focus();
}

/**
 * Remove a transaction row
 */
function removeRow(rowId) {
    const row = document.getElementById(`row-${rowId}`);
    if (row) {
        row.remove();
        updateUI();
        updateTotals();
    }
}

/**
 * Update UI elements based on current state
 */
function updateUI() {
    const rows = document.querySelectorAll('.bulk-item-row');
    const emptyMessage = document.getElementById('emptyMessage');
    const summarySection = document.getElementById('summarySection');
    const submitBtn = document.getElementById('submitBtn');

    if (rows.length === 0) {
        emptyMessage.style.display = 'block';
        summarySection.style.display = 'none';
        submitBtn.disabled = true;
    } else {
        emptyMessage.style.display = 'none';
        summarySection.style.display = 'block';
        submitBtn.disabled = false;
    }

    document.getElementById('itemCount').textContent = rows.length;
}

/**
 * Calculate and update totals
 */
function updateTotals() {
    const amounts = document.querySelectorAll('.item-amount');
    let total = 0;

    amounts.forEach(input => {
        const value = parseFloat(input.value) || 0;
        total += value;
    });

    const totalElement = document.getElementById('totalAmount');
    if (total < 0) {
        totalElement.textContent = `-$${Math.abs(total).toFixed(2)}`;
        totalElement.className = 'txn-amount income';
    } else {
        totalElement.textContent = `$${total.toFixed(2)}`;
        totalElement.className = 'txn-amount expense';
    }
}

/**
 * Collect all transaction items into JSON
 */
function collectItems() {
    const rows = document.querySelectorAll('.bulk-item-row');
    const items = [];

    rows.forEach(row => {
        const date = row.querySelector('.item-date').value;
        const description = row.querySelector('.item-description').value.trim();
        const amount = parseFloat(row.querySelector('.item-amount').value) || 0;

        if (date && description && amount !== 0) {
            items.push({
                date: date,
                description: description,
                amount: amount
            });
        }
    });

    return items;
}

/**
 * Validate the form before submission
 */
function validateForm() {
    const items = collectItems();
    const errors = [];

    // Check common fields
    const category = document.getElementById('category').value;
    const type = document.getElementById('type').value;
    const account = document.getElementById('account_name').value;
    const owner = document.getElementById('owner').value;

    if (!category) errors.push('Category is required');
    if (!type) errors.push('Type is required');
    if (!account) errors.push('Account is required');
    if (!owner) errors.push('Owner is required');

    // Check items
    if (items.length === 0) {
        errors.push('At least one valid transaction item is required');
    }

    // Validate each row
    const rows = document.querySelectorAll('.bulk-item-row');
    rows.forEach((row, index) => {
        const date = row.querySelector('.item-date').value;
        const description = row.querySelector('.item-description').value.trim();
        const amount = parseFloat(row.querySelector('.item-amount').value);

        if (!date) {
            errors.push(`Row ${index + 1}: Date is required`);
            row.querySelector('.item-date').classList.add('is-invalid');
        } else {
            row.querySelector('.item-date').classList.remove('is-invalid');
        }

        if (!description) {
            errors.push(`Row ${index + 1}: Description is required`);
            row.querySelector('.item-description').classList.add('is-invalid');
        } else {
            row.querySelector('.item-description').classList.remove('is-invalid');
        }

        if (isNaN(amount) || amount === 0) {
            errors.push(`Row ${index + 1}: Valid non-zero amount is required`);
            row.querySelector('.item-amount').classList.add('is-invalid');
        } else {
            row.querySelector('.item-amount').classList.remove('is-invalid');
        }
    });

    return errors;
}

/**
 * Handle form submission
 */
function handleSubmit(event) {
    const errors = validateForm();

    if (errors.length > 0) {
        event.preventDefault();
        alert('Please fix the following errors:\n\n' + errors.join('\n'));
        return false;
    }

    // Collect items and set hidden field
    const items = collectItems();
    document.getElementById('transactionItems').value = JSON.stringify(items);

    return true;
}

/**
 * Reset the form to initial state
 */
function resetForm() {
    if (confirm('Are you sure you want to reset the form? All entered data will be lost.')) {
        // Clear common fields
        document.getElementById('category').selectedIndex = 0;
        document.getElementById('sub_category').selectedIndex = 0;
        document.getElementById('type').selectedIndex = 0;
        document.getElementById('account_name').selectedIndex = 0;
        document.getElementById('owner').selectedIndex = 0;

        // Clear all rows
        document.getElementById('itemsTableBody').innerHTML = '';
        rowCounter = 0;

        // Add one fresh row
        addRow();
        updateTotals();
    }
}
