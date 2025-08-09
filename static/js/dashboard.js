/* Dashboard JavaScript - Enhanced Dashboard Functionality */

// Dashboard state management
let dashboardState = {
    currentView: 'overview',
    currentYear: new Date().getFullYear(),
    currentMonth: new Date().getMonth() + 1,
    currentOwner: 'all',
    categoriesData: {},
    chartData: {}
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Loading enhanced dashboard...');
    
    // Get current view from URL or default
    const urlParams = new URLSearchParams(window.location.search);
    dashboardState.currentView = getViewFromUrl();
    dashboardState.currentYear = parseInt(urlParams.get('year')) || dashboardState.currentYear;
    dashboardState.currentMonth = parseInt(urlParams.get('month')) || dashboardState.currentMonth;
    dashboardState.currentOwner = urlParams.get('owner') || 'all';
    
    loadViewSpecificContent();
});

function getViewFromUrl() {
    const path = window.location.pathname;
    const match = path.match(/\/dashboard\/(\w+)/);
    return match ? match[1] : 'overview';
}

function loadViewSpecificContent() {
    const view = dashboardState.currentView;
    console.log(`Loading content for view: ${view}`);
    
    switch(view) {
        case 'overview':
            loadOverviewCharts();
            break;
        case 'budget':
            loadBudgetCharts();
            break;
        case 'categories':
            loadCategoriesManagement();
            break;
        default:
            console.warn(`Unknown view: ${view}, defaulting to overview`);
            loadOverviewCharts();
            break;
    }
}
// Overview Charts
function loadOverviewCharts() {
    console.log('📊 Loading enhanced overview charts...');
    
    // Get data from template variables (if available)
    const monthlySpending = getTemplateData('monthlySpending') || [];
    const topCategories = getTemplateData('topCategories') || [];
    const monthlyTrend = getTemplateData('monthlyTrend') || [];
    
    console.log('📊 Monthly spending data:', monthlySpending);
    console.log('📊 Top categories data:', topCategories);
    console.log('📊 Monthly trend data:', monthlyTrend);
    
    // Create charts if data exists
    if (monthlySpending.length > 0) {
        createSpendingTypeChart(monthlySpending);
    } else {
        showNoDataMessage('spendingTypeChart', 'No spending data for current period');
    }
    
    if (topCategories.length > 0) {
        createTopCategoriesChart(topCategories);
    } else {
        showNoDataMessage('topCategoriesChart', 'No category data for current period');
    }
    
    if (monthlyTrend.length > 0) {
        createMonthlyTrendChart(monthlyTrend);
    } else {
        showNoDataMessage('monthlyTrendChart', 'Insufficient data for trend analysis');
    }
}

function createSpendingTypeChart(data) {
    console.log('Creating spending type chart with data:', data);
    
    const chartData = [{
        labels: data.map(item => item.type),
        values: data.map(item => item.amount),
        type: 'pie',
        hole: 0.4,
        textinfo: 'label+percent',
        textposition: 'outside',
        marker: {
            colors: ['#e74c3c', '#f39c12', '#27ae60', '#3498db']
        }
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Spending by Type',
        showlegend: false,
        height: 350
    };
    
    Plotly.newPlot('spendingTypeChart', chartData, layout, chartConfig);
}

function createTopCategoriesChart(data) {
    console.log('Creating top categories chart with data:', data);
    
    const chartData = [{
        x: data.map(item => item.total),
        y: data.map(item => item.category),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#3498db',
            opacity: 0.8
        },
        text: data.map(item => `$${item.total.toFixed(2)}`),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Amount: $%{x:.2f}<extra></extra>'
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Top 5 Categories',
        xaxis: { 
            title: 'Amount ($)',
            showgrid: true
        },
        yaxis: { 
            title: '',
            automargin: true
        },
        height: 350,
        showlegend: false
    };
    
    Plotly.newPlot('topCategoriesChart', chartData, layout, chartConfig);
}


// Monthly Trend Chart
function createMonthlyTrendChart(trendData) {
    console.log('Creating monthly trend chart with data:', trendData);
    
    if (!trendData || trendData.length === 0) {
        showNoDataMessage('monthlyTrendChart', 'No trend data available');
        return;
    }
    
    const chartData = [{
        x: trendData.map(item => item.month),
        y: trendData.map(item => item.total),
        type: 'scatter',
        mode: 'lines+markers',
        line: {
            color: '#3498db',
            width: 3
        },
        marker: {
            color: '#3498db',
            size: 8
        },
        text: trendData.map(item => `$${item.total.toFixed(2)}`),
        textposition: 'top center',
        hovertemplate: '<b>%{x}</b><br>Spending: $%{y:.2f}<extra></extra>'
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: '3-Month Spending Trend',
        xaxis: { 
            title: 'Month',
            showgrid: true
        },
        yaxis: { 
            title: 'Amount ($)',
            showgrid: true
        },
        height: 350,
        showlegend: false
    };
    
    Plotly.newPlot('monthlyTrendChart', chartData, layout, chartConfig);
}

// Categories Management
function loadCategoriesManagement() {
    console.log('⚙️ Loading categories management...');
    
    // Initialize categories data storage
    dashboardState.categoriesData = {};
    
    // Get current filters
    const yearSelect = document.querySelector('select[name="year"]');
    const monthSelect = document.querySelector('select[name="month"]');
    
    if (yearSelect && monthSelect) {
        dashboardState.currentFilter = {
            year: yearSelect.value,
            month: monthSelect.value
        };
        
        // Add event listeners for filter changes
        yearSelect.addEventListener('change', loadCategoriesData);
        monthSelect.addEventListener('change', loadCategoriesData);
    } else {
        dashboardState.currentFilter = {
            year: dashboardState.currentYear,
            month: dashboardState.currentMonth.toString()
        };
    }
    
    // Load initial data
    loadCategoriesData();
    
    // Add tab change listeners
    const tabButtons = document.querySelectorAll('#managementTabs button[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function(e) {
            const targetTab = e.target.getAttribute('data-bs-target').replace('#', '');
            loadTabData(targetTab);
        });
    });
}

function loadCategoriesData() {
    console.log('📊 Loading categories data...');
    
    // Update current filter
    const yearSelect = document.querySelector('select[name="year"]');
    const monthSelect = document.querySelector('select[name="month"]');
    
    if (yearSelect && monthSelect) {
        dashboardState.currentFilter = {
            year: yearSelect.value,
            month: monthSelect.value
        };
    }
    
    // Load data for the currently active tab
    const activeTab = document.querySelector('#managementTabs .nav-link.active');
    if (activeTab) {
        const targetTab = activeTab.getAttribute('data-bs-target').replace('#', '');
        loadTabData(targetTab);
    } else {
        // Load categories by default
        loadTabData('categories');
    }
    
    updateStatistics();
}

function loadTabData(tabName) {
    console.log(`📂 Loading data for tab: ${tabName}`);
    
    switch(tabName) {
        case 'categories':
            loadCategories();
            break;
        case 'subcategories':
            loadSubCategories();
            break;
        case 'owners':
            loadOwners();
            break;
        case 'accounts':
            loadAccounts();
            break;
        default:
            console.warn(`Unknown tab: ${tabName}`);
    }
}

function loadCategories() {
    console.log('📊 Loading categories...');
    
    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: 'all'  // Show all categories for the year
    });
    
    fetch(`/api/categories/categories?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('📊 Categories data:', data);
            if (Array.isArray(data)) {
                dashboardState.categoriesData.categories = data;
                renderCategoriesTable(data);
            } else {
                console.error('Categories data is not an array:', data);
                renderCategoriesTable([]);
            }
        })
        .catch(error => {
            console.error('Error loading categories:', error);
            FinanceUtils.showAlert('Error loading categories: ' + error.message, 'danger');
            renderCategoriesTable([]);
        });
}

function renderCategoriesTable(categories) {
    console.log('🎨 Rendering categories table with', categories.length, 'categories');
    
    const tableBody = document.getElementById('categoriesTableBody');
    if (!tableBody) {
        console.error('Categories table body not found');
        return;
    }
    
    if (categories.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <p class="text-muted">No categories found for the selected period.</p>
                    <button class="btn btn-primary btn-sm" onclick="showAddModal('category')">
                        ➕ Add Your First Category
                    </button>
                </td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    categories.forEach(category => {
        const typeClass = getTypeClass(category.type || '');
        html += `
            <tr>
                <td class="fw-bold">${category.name}</td>
                <td>
                    <span class="badge ${typeClass}">${category.type || 'Not Set'}</span>
                </td>
                <td>${category.transaction_count || 0}</td>
                <td class="fw-bold text-danger">$${(category.total_amount || 0).toFixed(2)}</td>
                <td>$${(category.avg_amount || 0).toFixed(2)}</td>
                <td class="text-primary">$${(category.budget_amount || 0).toFixed(2)}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-outline-primary btn-sm" 
                                onclick="editItem('category', '${category.name}')"
                                title="Edit Category">
                            ✏️
                        </button>
                        <button class="btn btn-outline-danger btn-sm" 
                                onclick="deleteItem('category', '${category.name}', ${category.transaction_count || 0})"
                                title="Delete Category">
                            🗑️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// Add this function to support category badge rendering
function getTypeClass(type) {
    switch ((type || '').toLowerCase()) {
        case 'living expenses':
            return 'bg-info';
        case 'debt':
            return 'bg-danger';
        case 'discretionary':
            return 'bg-success';
        case 'transport':
            return 'bg-warning';
        case 'travel':
            return 'bg-primary';
        default:
            return 'bg-secondary';
    }
}
// SubCategories Management
function loadSubCategories() {
    console.log('🏷️ Loading sub-categories...');
    
    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: 'all'  // Show all sub-categories
    });
    
    fetch(`/api/categories/subcategories?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('🏷️ Sub-categories data:', data);
            dashboardState.categoriesData.subcategories = data;
            renderSubCategoriesTable(data);
        })
        .catch(error => {
            console.error('Error loading sub-categories:', error);
            FinanceUtils.showAlert('Error loading sub-categories: ' + error.message, 'danger');
        });
}

function renderSubCategoriesTable(subcategories) {
    const tbody = document.getElementById('subcategoriesTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (subcategories.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <p class="text-muted">No sub-categories found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    subcategories.forEach(subcategory => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${subcategory.name}</td>
            <td><span class="badge bg-info">${subcategory.category}</span></td>
            <td>${subcategory.transaction_count}</td>
            <td class="fw-bold">$${subcategory.total_amount.toFixed(2)}</td>
            <td>$${subcategory.avg_amount.toFixed(2)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem('subcategory', '${subcategory.name}')" title="Edit">
                        ✏️
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem('subcategory', '${subcategory.name}', ${subcategory.transaction_count})" title="Delete">
                        🗑️
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Owners Management

function loadOwners() {
    console.log('👥 Loading owners...');
    
    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: 'all'  // Show all owners
    });
    
    fetch(`/api/categories/owners?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('👥 Owners data:', data);
            dashboardState.categoriesData.owners = data;
            renderOwnersTable(data);
        })
        .catch(error => {
            console.error('Error loading owners:', error);
            FinanceUtils.showAlert('Error loading owners: ' + error.message, 'danger');
        });
}

function renderOwnersTable(owners) {
    const tbody = document.getElementById('ownersTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (owners.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4">
                    <p class="text-muted">No owners found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    owners.forEach(owner => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${owner.name}</td>
            <td>${owner.transaction_count}</td>
            <td class="fw-bold">$${owner.total_amount.toFixed(2)}</td>
            <td>$${owner.avg_amount.toFixed(2)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem('owner', '${owner.name}')" title="Edit">
                        ✏️
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem('owner', '${owner.name}', ${owner.transaction_count})" title="Delete">
                        🗑️
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Account Management

function loadAccounts() {
    console.log('💳 Loading accounts...');
    
    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: 'all'  // Show all accounts
    });
    
    fetch(`/api/categories/accounts?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('💳 Accounts data:', data);
            dashboardState.categoriesData.accounts = data;
            renderAccountsTable(data);
        })
        .catch(error => {
            console.error('Error loading accounts:', error);
            FinanceUtils.showAlert('Error loading accounts: ' + error.message, 'danger');
        });
}

function renderAccountsTable(accounts) {
    const tbody = document.getElementById('accountsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (accounts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4">
                    <p class="text-muted">No accounts found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    accounts.forEach(account => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${account.name}</td>
            <td>${account.transaction_count}</td>
            <td class="fw-bold">$${account.total_amount.toFixed(2)}</td>
            <td>$${account.avg_amount.toFixed(2)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem('account', '${account.name}')" title="Edit">
                        ✏️
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem('account', '${account.name}', ${account.transaction_count})" title="Delete">
                        🗑️
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}
// Placeholder functions for categories management

function showAddModal(type) {
    console.log(`➕ Showing add modal for ${type}`);
    
    const modal = document.getElementById('addEditModal');
    const modalLabel = document.getElementById('addEditModalLabel');
    const nameField = document.getElementById('nameField');
    const parentCategoryField = document.getElementById('parentCategoryField');
    const typeField = document.getElementById('typeField');
    const saveButton = document.getElementById('saveButtonText');
    
    // Reset form
    const form = document.getElementById('addEditForm');
    if (form) form.reset();
    
    document.getElementById('editItemType').value = type;
    document.getElementById('editItemId').value = '';
    
    // Configure modal based on type
    switch(type) {
        case 'category':
            modalLabel.textContent = 'Add New Category';
            nameField.querySelector('label').textContent = 'Category Name *';
            nameField.querySelector('input').placeholder = 'e.g., Entertainment, Food, etc.';
            parentCategoryField.classList.add('d-none');
            typeField.classList.remove('d-none');
            break;
            
        case 'subcategory':
            modalLabel.textContent = 'Add New Sub-Category';
            nameField.querySelector('label').textContent = 'Sub-Category Name *';
            nameField.querySelector('input').placeholder = 'e.g., Movies, Fast Food, etc.';
            parentCategoryField.classList.remove('d-none');
            typeField.classList.add('d-none');
            
            // Populate parent categories
            const categorySelect = document.getElementById('parentCategory');
            categorySelect.innerHTML = '<option value="">Select category...</option>';
            if (dashboardState.categoriesData.categories) {
                dashboardState.categoriesData.categories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.name;
                    option.textContent = cat.name;
                    categorySelect.appendChild(option);
                });
            }
            break;
            
        case 'owner':
            modalLabel.textContent = 'Add New Owner';
            nameField.querySelector('label').textContent = 'Owner Name *';
            nameField.querySelector('input').placeholder = 'e.g., John, Jane, etc.';
            parentCategoryField.classList.add('d-none');
            typeField.classList.add('d-none');
            break;
            
        case 'account':
            modalLabel.textContent = 'Add New Account';
            nameField.querySelector('label').textContent = 'Account Name *';
            nameField.querySelector('input').placeholder = 'e.g., Chase Checking, Cash, etc.';
            parentCategoryField.classList.add('d-none');
            typeField.classList.add('d-none');
            break;
    }
    
    saveButton.textContent = 'Save';
    
    // Show modal
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function editItem(type, name) {
    console.log(`✏️ Editing ${type}: ${name}`);
    
    const modal = document.getElementById('addEditModal');
    const modalLabel = document.getElementById('addEditModalLabel');
    const nameField = document.getElementById('nameField');
    const parentCategoryField = document.getElementById('parentCategoryField');
    const typeField = document.getElementById('typeField');
    const saveButton = document.getElementById('saveButtonText');
    
    document.getElementById('editItemType').value = type;
    document.getElementById('editItemId').value = name;
    document.getElementById('itemName').value = name;
    
    // Configure modal based on type
    switch(type) {
        case 'category':
            modalLabel.textContent = `Edit Category: ${name}`;
            nameField.querySelector('label').textContent = 'Category Name *';
            parentCategoryField.classList.add('d-none');
            typeField.classList.remove('d-none');
            
            // Set current type if available
            const category = dashboardState.categoriesData.categories?.find(c => c.name === name);
            if (category && category.type) {
                document.getElementById('itemType').value = category.type;
            }
            break;
            
        case 'subcategory':
            modalLabel.textContent = `Edit Sub-Category: ${name}`;
            nameField.querySelector('label').textContent = 'Sub-Category Name *';
            parentCategoryField.classList.remove('d-none');
            typeField.classList.add('d-none');
            
            // Populate parent categories and set current
            const categorySelect = document.getElementById('parentCategory');
            categorySelect.innerHTML = '<option value="">Select category...</option>';
            if (dashboardState.categoriesData.categories) {
                dashboardState.categoriesData.categories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.name;
                    option.textContent = cat.name;
                    categorySelect.appendChild(option);
                });
            }
            
            const subcategory = dashboardState.categoriesData.subcategories?.find(s => s.name === name);
            if (subcategory) {
                categorySelect.value = subcategory.category;
            }
            break;
            
        case 'owner':
            modalLabel.textContent = `Edit Owner: ${name}`;
            nameField.querySelector('label').textContent = 'Owner Name *';
            parentCategoryField.classList.add('d-none');
            typeField.classList.add('d-none');
            break;
            
        case 'account':
            modalLabel.textContent = `Edit Account: ${name}`;
            nameField.querySelector('label').textContent = 'Account Name *';
            parentCategoryField.classList.add('d-none');
            typeField.classList.add('d-none');
            break;
    }
    
    saveButton.textContent = 'Update';
    
    // Show modal
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function saveItem() {
    console.log('💾 Saving item...');
    
    const type = document.getElementById('editItemType').value;
    const originalName = document.getElementById('editItemId').value;
    const newName = document.getElementById('itemName').value.trim();
    const parentCategory = document.getElementById('parentCategory').value;
    const itemType = document.getElementById('itemType').value;
    
    if (!newName) {
        FinanceUtils.showAlert('Name is required', 'danger');
        return;
    }
    
    if (type === 'subcategory' && !parentCategory) {
        FinanceUtils.showAlert('Parent category is required for sub-categories', 'danger');
        return;
    }
    
    const isEdit = originalName !== '';
    const data = { name: newName };
    
    if (type === 'subcategory') {
        data.category = parentCategory;
    }
    if (type === 'category' && itemType) {
        data.type = itemType;
    }
    
    // Determine endpoint and method
    let url = `/api/categories/${type === 'category' ? 'categories' : type + 's'}`;
    let method = 'POST';
    
    if (isEdit) {
        url += `/${encodeURIComponent(originalName)}`;
        method = 'PUT';
    }
    
    FinanceUtils.apiCall(url, {
        method: method,
        body: JSON.stringify(data)
    })
    .then(result => {
        if (result.success) {
            FinanceUtils.showAlert(result.message, 'success');
            
            // Hide modal
            const modal = document.getElementById('addEditModal');
            if (typeof bootstrap !== 'undefined' && modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
            
            // Reload current tab data
            const activeTab = document.querySelector('#managementTabs .nav-link.active');
            if (activeTab) {
                const targetTab = activeTab.getAttribute('data-bs-target').replace('#', '');
                loadTabData(targetTab);
            }
            
            // Update statistics
            updateStatistics();
            
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving item:', error);
        FinanceUtils.showAlert('Error saving item', 'danger');
    });
}

function deleteItem(type, name, transactionCount) {
    console.log(`🗑️ Deleting ${type}: ${name}`);
    
    if (transactionCount > 0) {
        if (!confirm(`This ${type} has ${transactionCount} transactions. Deleting it will require migrating these transactions. Do you want to proceed?`)) {
            return;
        }
        showMigrationModal(type, name, transactionCount);
        return;
    }
    
    if (!confirm(`Are you sure you want to delete this ${type}: ${name}?`)) {
        return;
    }
    
    const url = `/api/categories/${type === 'category' ? 'categories' : type + 's'}/${encodeURIComponent(name)}`;
    
    FinanceUtils.apiCall(url, {
        method: 'DELETE'
    })
    .then(result => {
        if (result.success) {
            FinanceUtils.showAlert(result.message, 'success');
            
            // Reload current tab data
            const activeTab = document.querySelector('#managementTabs .nav-link.active');
            if (activeTab) {
                const targetTab = activeTab.getAttribute('data-bs-target').replace('#', '');
                loadTabData(targetTab);
            }
            
            // Update statistics
            updateStatistics();
            
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting item:', error);
        FinanceUtils.showAlert('Error deleting item', 'danger');
    });
}

function showMigrationModal(type, name, transactionCount) {
    console.log(`🔄 Showing migration modal for ${type}: ${name}`);
    
    const modal = document.getElementById('migrationModal');
    const titleEl = document.getElementById('migrationModalLabel');
    const countEl = document.getElementById('migrationTransactionCount');
    const targetField = document.getElementById('migrationTargetField');
    const targetSelect = document.getElementById('migrationTarget');
    const previewEl = document.getElementById('migrationPreview');
    
    titleEl.textContent = `Migrate ${type}: ${name}`;
    countEl.textContent = transactionCount;
    
    document.getElementById('migrationItemType').value = type;
    document.getElementById('migrationItemName').value = name;
    
    // Populate target options
    targetSelect.innerHTML = '<option value="">Select target...</option>';
    targetField.querySelector('label').textContent = `Migrate to ${type} *`;
    
    const dataSource = type === 'category' ? dashboardState.categoriesData.categories :
                      type === 'subcategory' ? dashboardState.categoriesData.subcategories :
                      type === 'owner' ? dashboardState.categoriesData.owners :
                      dashboardState.categoriesData.accounts;
    
    if (dataSource) {
        dataSource.forEach(item => {
            if (item.name !== name) { // Don't include the item being deleted
                const option = document.createElement('option');
                option.value = item.name;
                option.textContent = item.name;
                targetSelect.appendChild(option);
            }
        });
    }
    
    // Load transaction preview
    previewEl.innerHTML = 'Loading affected transactions...';
    
    fetch(`/api/categories/migration_preview?type=${type}&name=${encodeURIComponent(name)}`)
        .then(response => response.json())
        .then(transactions => {
            let html = '';
            transactions.slice(0, 10).forEach(transaction => {
                html += `
                    <div class="border-bottom py-1">
                        <small><strong>${transaction.date}</strong> - ${transaction.description} - $${Math.abs(transaction.amount).toFixed(2)}</small>
                    </div>
                `;
            });
            if (transactions.length > 10) {
                html += `<div class="text-muted mt-2"><small>...and ${transactions.length - 10} more transactions</small></div>`;
            }
            previewEl.innerHTML = html || '<div class="text-muted">No transactions found</div>';
        })
        .catch(error => {
            previewEl.innerHTML = '<div class="text-danger">Error loading preview</div>';
        });
    
    // Show modal
    if (typeof bootstrap !== 'undefined' && modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

function executeMigration() {
    console.log('🔄 Executing migration...');
    
    const type = document.getElementById('migrationItemType').value;
    const source = document.getElementById('migrationItemName').value;
    const target = document.getElementById('migrationTarget').value;
    
    if (!target) {
        FinanceUtils.showAlert('Please select a target for migration', 'danger');
        return;
    }
    
    FinanceUtils.apiCall('/api/categories/migrate', {
        method: 'POST',
        body: JSON.stringify({
            type: type,
            source: source,
            target: target
        })
    })
    .then(result => {
        if (result.success) {
            FinanceUtils.showAlert(result.message, 'success');
            
            // Hide migration modal
            const migrationModal = document.getElementById('migrationModal');
            if (typeof bootstrap !== 'undefined' && migrationModal) {
                const bsModal = bootstrap.Modal.getInstance(migrationModal);
                if (bsModal) bsModal.hide();
            }
            
            // Reload current tab data
            const activeTab = document.querySelector('#managementTabs .nav-link.active');
            if (activeTab) {
                const targetTab = activeTab.getAttribute('data-bs-target').replace('#', '');
                loadTabData(targetTab);
            }
            
            // Update statistics
            updateStatistics();
            
        } else {
            FinanceUtils.showAlert(`Error: ${result.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error executing migration:', error);
        FinanceUtils.showAlert('Error executing migration', 'danger');
    });
}

function updateStatistics() {
    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: dashboardState.currentFilter.month
    });
    
    fetch(`/api/categories/statistics?${params}`)
        .then(response => response.json())
        .then(stats => {
            const categoriesEl = document.getElementById('totalCategories');
            const subCategoriesEl = document.getElementById('totalSubCategories');
            const ownersEl = document.getElementById('totalOwners');
            const accountsEl = document.getElementById('totalAccounts');
            
            if (categoriesEl) categoriesEl.textContent = stats.categories || 0;
            if (subCategoriesEl) subCategoriesEl.textContent = stats.subcategories || 0;
            if (ownersEl) ownersEl.textContent = stats.owners || 0;
            if (accountsEl) accountsEl.textContent = stats.accounts || 0;
        })
        .catch(error => {
            console.error('Error updating statistics:', error);
        });
}

// Utility functions
function getTemplateData(variableName) {
    // This function will be used to get data passed from templates
    // In real implementation, data will be passed via script tags or data attributes
    return window.templateData && window.templateData[variableName] || null;
}

function showNoDataMessage(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="alert alert-info">${message}</div>`;
    }
}

// Budget Management Functions (moved from templates)
function copyTemplateBudget() {
    const month = dashboardState.currentMonth;
    const year = dashboardState.currentYear;
    
    if (confirm(`Copy template budget to ${year}-${month.toString().padStart(2, '0')}?`)) {
        FinanceUtils.apiCall('/api/copy_template_budget', {
            method: 'POST',
            body: JSON.stringify({
                month: month,
                year: year
            })
        })
        .then(result => {
            if (result.success) {
                FinanceUtils.showAlert(result.message, 'success');
                location.reload();
            } else {
                FinanceUtils.showAlert('Error copying template budget: ' + result.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error copying template budget:', error);
            FinanceUtils.showAlert('Error copying template budget', 'danger');
        });
    }
}

window.showAddModal = showAddModal;
window.editItem = editItem;
window.deleteItem = deleteItem;
window.saveItem = saveItem;
window.executeMigration = executeMigration;

// Export dashboard functions
window.Dashboard = {
    loadViewSpecificContent,
    loadOverviewCharts,
    loadCategoriesManagement,
    copyTemplateBudget
};