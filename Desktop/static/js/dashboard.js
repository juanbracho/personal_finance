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

// Budget view - no charts needed, server-rendered
function loadBudgetCharts() {
    console.log('Budget view loaded (server-rendered)');
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

const CHART_COLORS = {
    'warm-ink': {
        needs: '#7BAF8E', wants: '#D4956A', business: '#6A8FBF', savings: '#A67FB5',
        primary: '#C49A5E', bg: '#201D18', text: '#F0EBE3', grid: '#332E28'
    },
    'indigo': {
        needs: '#7BAF8E', wants: '#D4956A', business: '#6A8FBF', savings: '#A67FB5',
        primary: '#7B9ED9', bg: '#1A1F2C', text: '#E8EDF7', grid: '#252B3B'
    },
    'washi': {
        needs: '#4A8B60', wants: '#B86A3A', business: '#3A6A9F', savings: '#7A5A9F',
        primary: '#8C6A3F', bg: '#FFFFFF', text: '#2C2622', grid: '#DDD9D2'
    }
};

function createSpendingTypeChart(data) {
    console.log('Creating spending type chart with data:', data);

    const theme = document.documentElement.dataset.theme || 'warm-ink';
    const colors = CHART_COLORS[theme] || CHART_COLORS['warm-ink'];

    const typeColorMap = { needs: colors.needs, wants: colors.wants, business: colors.business, savings: colors.savings };
    const chartColors = data.map(item => typeColorMap[(item.type || '').toLowerCase()] || colors.primary);

    const chartData = [{
        labels: data.map(item => item.type),
        values: data.map(item => item.amount),
        type: 'pie',
        hole: 0.4,
        textinfo: 'label+percent',
        textposition: 'outside',
        marker: { colors: chartColors }
    }];

    const layout = {
        ...chartConfig.layout,
        title: { text: 'Spending by Type', font: { color: colors.text, size: 13 } },
        showlegend: true,
        legend: { font: { color: colors.text } },
        paper_bgcolor: colors.bg,
        plot_bgcolor: colors.bg,
        font: { color: colors.text },
        height: 300
    };

    Plotly.newPlot('spendingTypeChart', chartData, layout, { responsive: true, displayModeBar: false });
}

function createTopCategoriesChart(data) {
    console.log('Creating top categories chart with data:', data);

    const theme = document.documentElement.dataset.theme || 'warm-ink';
    const colors = CHART_COLORS[theme] || CHART_COLORS['warm-ink'];

    const chartData = [{
        x: data.map(item => item.total),
        y: data.map(item => item.category),
        type: 'bar',
        orientation: 'h',
        marker: { color: colors.primary, opacity: 0.85 },
        text: data.map(item => `$${item.total.toFixed(2)}`),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Amount: $%{x:.2f}<extra></extra>'
    }];

    const layout = {
        ...chartConfig.layout,
        title: { text: 'Top 5 Categories', font: { color: colors.text, size: 13 } },
        xaxis: { title: 'Amount ($)', showgrid: true, gridcolor: colors.grid, color: colors.text },
        yaxis: { title: '', automargin: true, color: colors.text },
        paper_bgcolor: colors.bg,
        plot_bgcolor: colors.bg,
        font: { color: colors.text },
        height: 300,
        showlegend: false
    };

    Plotly.newPlot('topCategoriesChart', chartData, layout, { responsive: true, displayModeBar: false });
}


// Monthly Trend Chart
function createMonthlyTrendChart(trendData) {
    console.log('Creating monthly trend chart with data:', trendData);

    if (!trendData || trendData.length === 0) {
        showNoDataMessage('monthlyTrendChart', 'No trend data available');
        return;
    }

    const theme = document.documentElement.dataset.theme || 'warm-ink';
    const colors = CHART_COLORS[theme] || CHART_COLORS['warm-ink'];

    const chartData = [{
        x: trendData.map(item => item.month),
        y: trendData.map(item => item.total),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: colors.primary, width: 3 },
        marker: { color: colors.primary, size: 8 },
        text: trendData.map(item => `$${item.total.toFixed(2)}`),
        textposition: 'top center',
        hovertemplate: '<b>%{x}</b><br>Spending: $%{y:.2f}<extra></extra>'
    }];

    const layout = {
        ...chartConfig.layout,
        title: { text: '3-Month Trend', font: { color: colors.text, size: 13 } },
        xaxis: { title: 'Month', showgrid: true, gridcolor: colors.grid, color: colors.text },
        yaxis: { title: 'Amount ($)', showgrid: true, gridcolor: colors.grid, color: colors.text },
        paper_bgcolor: colors.bg,
        plot_bgcolor: colors.bg,
        font: { color: colors.text },
        height: 300,
        showlegend: false
    };

    Plotly.newPlot('monthlyTrendChart', chartData, layout, { responsive: true, displayModeBar: false });
}

// Categories Management
function loadCategoriesManagement() {
    console.log('⚙️ Loading categories management...');
    
    // Initialize categories data storage
    dashboardState.categoriesData = {};
    
    // Get current filters
    const yearSelect = document.querySelector('select[name="year"]');
    const monthSelect = document.querySelector('select[name="month"]');
    
    const ownerSelect = document.querySelector('select[name="owner"]');

    if (yearSelect) {
        dashboardState.currentFilter = {
            year: yearSelect.value,
            month: monthSelect ? monthSelect.value : 'all',
            owner: ownerSelect ? ownerSelect.value : 'all'
        };

        // Add event listeners for filter changes
        yearSelect.addEventListener('change', loadCategoriesData);
        if (monthSelect) monthSelect.addEventListener('change', loadCategoriesData);
        if (ownerSelect) ownerSelect.addEventListener('change', loadCategoriesData);
    } else {
        dashboardState.currentFilter = {
            year: dashboardState.currentYear,
            month: 'all',
            owner: 'all'
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
    
    const ownerSelect2 = document.querySelector('select[name="owner"]');
    if (yearSelect) {
        dashboardState.currentFilter = {
            year: yearSelect.value,
            month: monthSelect ? monthSelect.value : 'all',
            owner: ownerSelect2 ? ownerSelect2.value : 'all'
        };
    }
    
    // Load data for the currently active tab
    const activeTab = document.querySelector('#managementTabs [data-bs-toggle="tab"].active');
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
        case 'types':
            loadTypes();
            break;
        default:
            console.warn(`Unknown tab: ${tabName}`);
    }
}

function loadCategories() {
    console.log('📊 Loading categories...');

    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: dashboardState.currentFilter.month || 'all',
        owner: dashboardState.currentFilter.owner || 'all'
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
    const tableBody = document.getElementById('categoriesTableBody');
    if (!tableBody) return;

    if (!categories || categories.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:32px;">
                    <div style="color:var(--text-muted);margin-bottom:12px;font-size:13px;">No categories found for the selected period.</div>
                    <button class="btn-kanso btn-kanso-primary btn-kanso-sm" onclick="showAddModal('category')">Add Your First Category</button>
                </td>
            </tr>`;
        return;
    }

    let html = '';
    categories.forEach(category => {
        html += `
            <tr>
                <td style="font-weight:600;">${category.name}</td>
                <td>${getTypeBadgeHtml(category.type || '')}</td>
                <td style="text-align:right;color:var(--text-muted);">${category.transaction_count || 0}</td>
                <td style="text-align:right;font-weight:600;color:var(--danger);">$${(category.total_amount || 0).toFixed(2)}</td>
                <td style="text-align:right;color:var(--text-muted);">$${(category.avg_amount || 0).toFixed(2)}</td>
                <td style="text-align:right;color:var(--primary);">$${(category.budget_amount || 0).toFixed(2)}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex;gap:4px;">
                        <button class="debt-action-btn edit" onclick="editItem('category','${category.name}')" title="Edit">${_SVG_EDIT}</button>
                        <button class="debt-action-btn delete" onclick="deleteItem('category','${category.name}',${category.transaction_count || 0})" title="Delete">${_SVG_DELETE}</button>
                    </div>
                </td>
            </tr>`;
    });
    tableBody.innerHTML = html;
}

// Kanso type badge helper
function getTypeBadgeHtml(type) {
    const colorMap = {
        'needs':    'var(--needs)',
        'wants':    'var(--wants)',
        'savings':  'var(--savings)',
        'business': 'var(--business)'
    };
    const color = colorMap[(type || '').toLowerCase()] || 'var(--text-muted)';
    if (!type) {
        return `<span class="kanso-badge" style="background:var(--surface-raised);color:var(--text-muted);border:1px solid var(--border);">Not Set</span>`;
    }
    return `<span class="kanso-badge" style="color:${color};background:color-mix(in srgb,${color} 15%,transparent);border:1px solid ${color};">${type}</span>`;
}

const _SVG_EDIT   = `<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" width="13" height="13"><path d="M9.5 2.5L11.5 4.5L5.5 10.5H3.5V8.5L9.5 2.5Z"/></svg>`;
const _SVG_DELETE = `<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" width="13" height="13"><polyline points="2 4 12 4"/><path d="M5 4V2h4v2"/><path d="M3 4l.8 8h6.4L11 4"/></svg>`;
// SubCategories Management
function loadSubCategories() {
    console.log('🏷️ Loading sub-categories...');

    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: dashboardState.currentFilter.month || 'all',
        owner: dashboardState.currentFilter.owner || 'all'
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

    if (!subcategories || subcategories.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">No sub-categories found</td></tr>`;
        return;
    }

    let html = '';
    subcategories.forEach(sub => {
        html += `
            <tr>
                <td style="font-weight:600;">${sub.name}</td>
                <td><span class="kanso-badge" style="background:var(--primary-dim);color:var(--primary);">${sub.category}</span></td>
                <td style="text-align:right;color:var(--text-muted);">${sub.transaction_count}</td>
                <td style="text-align:right;font-weight:600;">$${sub.total_amount.toFixed(2)}</td>
                <td style="text-align:right;color:var(--text-muted);">$${sub.avg_amount.toFixed(2)}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex;gap:4px;">
                        <button class="debt-action-btn edit" onclick="editItem('subcategory','${sub.name}')" title="Edit">${_SVG_EDIT}</button>
                        <button class="debt-action-btn delete" onclick="deleteItem('subcategory','${sub.name}',${sub.transaction_count})" title="Delete">${_SVG_DELETE}</button>
                    </div>
                </td>
            </tr>`;
    });
    tbody.innerHTML = html;
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

    if (!owners || owners.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">No owners found</td></tr>`;
        return;
    }

    let html = '';
    owners.forEach(owner => {
        html += `
            <tr>
                <td style="font-weight:600;">${owner.name}</td>
                <td style="text-align:right;color:var(--text-muted);">${owner.transaction_count}</td>
                <td style="text-align:right;font-weight:600;">$${owner.total_amount.toFixed(2)}</td>
                <td style="text-align:right;color:var(--text-muted);">$${owner.avg_amount.toFixed(2)}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex;gap:4px;">
                        <button class="debt-action-btn edit" onclick="editItem('owner','${owner.name}')" title="Edit">${_SVG_EDIT}</button>
                        <button class="debt-action-btn delete" onclick="deleteItem('owner','${owner.name}',${owner.transaction_count})" title="Delete">${_SVG_DELETE}</button>
                    </div>
                </td>
            </tr>`;
    });
    tbody.innerHTML = html;
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

    if (!accounts || accounts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">No accounts found</td></tr>`;
        return;
    }

    let html = '';
    accounts.forEach(account => {
        html += `
            <tr>
                <td style="font-weight:600;">${account.name}</td>
                <td style="text-align:right;color:var(--text-muted);">${account.transaction_count}</td>
                <td style="text-align:right;font-weight:600;">$${account.total_amount.toFixed(2)}</td>
                <td style="text-align:right;color:var(--text-muted);">$${account.avg_amount.toFixed(2)}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex;gap:4px;">
                        <button class="debt-action-btn edit" onclick="editItem('account','${account.name}')" title="Edit">${_SVG_EDIT}</button>
                        <button class="debt-action-btn delete" onclick="deleteItem('account','${account.name}',${account.transaction_count})" title="Delete">${_SVG_DELETE}</button>
                    </div>
                </td>
            </tr>`;
    });
    tbody.innerHTML = html;
}

// Types Management

function loadTypes() {
    console.log('🔖 Loading types...');

    const params = new URLSearchParams({
        year: dashboardState.currentFilter.year,
        month: dashboardState.currentFilter.month || 'all',
        owner: dashboardState.currentFilter.owner || 'all'
    });

    fetch(`/api/categories/types?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('🔖 Types data:', data);
            dashboardState.categoriesData.types = data;
            renderTypesTable(data);
        })
        .catch(error => {
            console.error('Error loading types:', error);
            renderTypesTable([]);
        });
}

function renderTypesTable(types) {
    const tbody = document.getElementById('typesTableBody');
    if (!tbody) return;

    if (!types || types.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">No types found. Add a custom type to get started.</td></tr>`;
        return;
    }

    let html = '';
    types.forEach(t => {
        const amtStr = t.total_amount > 0 ? `$${t.total_amount.toFixed(2)}` : '—';
        const avgStr = t.avg_amount > 0 ? `$${t.avg_amount.toFixed(2)}` : '—';
        html += `
            <tr>
                <td>${getTypeBadgeHtml(t.name)}</td>
                <td style="text-align:right;color:var(--text-muted);">${t.transaction_count}</td>
                <td style="text-align:right;font-weight:600;color:var(--danger);">${amtStr}</td>
                <td style="text-align:right;color:var(--text-muted);">${avgStr}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex;gap:4px;">
                        <button class="debt-action-btn edit" onclick="editItem('type','${t.name}')" title="Edit">${_SVG_EDIT}</button>
                        <button class="debt-action-btn delete" onclick="deleteItem('type','${t.name}',${t.transaction_count})" title="Delete">${_SVG_DELETE}</button>
                    </div>
                </td>
            </tr>`;
    });
    tbody.innerHTML = html;
}

// Placeholder functions for categories management

function populateTypeSelect(selectedValue) {
    const select = document.getElementById('itemType');
    if (!select) return;
    const defaults = ['Needs', 'Wants', 'Savings', 'Business'];
    const custom = (dashboardState.categoriesData.types || [])
        .map(t => t.name)
        .filter(n => !defaults.includes(n));
    const all = [...defaults, ...custom];
    select.innerHTML = '<option value="">Select type…</option>' +
        all.map(n => `<option value="${n}"${n === selectedValue ? ' selected' : ''}>${n}</option>`).join('');
}

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
            populateTypeSelect();
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

        case 'type':
            modalLabel.textContent = 'Add New Type';
            nameField.querySelector('label').textContent = 'Type Name *';
            nameField.querySelector('input').placeholder = 'e.g., Investments, Education, etc.';
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
            populateTypeSelect();

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

        case 'type':
            modalLabel.textContent = `Edit Type: ${name}`;
            nameField.querySelector('label').textContent = 'Type Name *';
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
            const activeTab = document.querySelector('#managementTabs [data-bs-toggle="tab"].active');
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
            const activeTab = document.querySelector('#managementTabs [data-bs-toggle="tab"].active');
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
                      type === 'type' ? dashboardState.categoriesData.types :
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
            const activeTab = document.querySelector('#managementTabs [data-bs-toggle="tab"].active');
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
        month: dashboardState.currentFilter.month || 'all',
        owner: dashboardState.currentFilter.owner || 'all'
    });

    fetch(`/api/categories/statistics?${params}`)
        .then(response => response.json())
        .then(stats => {
            const categoriesEl = document.getElementById('totalCategories');
            const subCategoriesEl = document.getElementById('totalSubCategories');
            const typesEl = document.getElementById('totalTypes');
            const ownersEl = document.getElementById('totalOwners');
            const accountsEl = document.getElementById('totalAccounts');

            if (categoriesEl) categoriesEl.textContent = stats.categories || 0;
            if (subCategoriesEl) subCategoriesEl.textContent = stats.subcategories || 0;
            if (typesEl) typesEl.textContent = stats.types || 0;
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
        element.innerHTML = `<div class="kanso-feedback info" style="text-align:center; padding:32px; margin:8px;">${message}</div>`;
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

// ── Theme-change chart refresh ─────────────────────────────────
// Patch setTheme (defined in base.html) so charts re-render whenever
// the user switches themes. setTheme is already defined before this
// script loads (it's in a <script> block above extra_js).
(function() {
    var _orig = window.setTheme;
    if (typeof _orig !== 'function') return;
    window.setTheme = function(name) {
        _orig(name);
        refreshChartsForTheme(name);
    };
})();

function refreshChartsForTheme(theme) {
    var colors = CHART_COLORS[theme] || CHART_COLORS['warm-ink'];

    // Overview view: re-create charts — they read theme at creation time
    var overviewEl = document.getElementById('spendingTypeChart');
    if (overviewEl && overviewEl._fullLayout) {
        loadOverviewCharts();
        return;
    }

    // Budget view: relayout existing Plotly figures with new bg/text colors
    var layoutUpdate = {
        paper_bgcolor: colors.bg,
        plot_bgcolor:  colors.bg,
        'font.color':          colors.text,
        'legend.font.color':   colors.text,
        'xaxis.color':         colors.text,
        'xaxis.gridcolor':     colors.grid,
        'yaxis.color':         colors.text,
        'yaxis.gridcolor':     colors.grid
    };

    ['budgetVsActualChart', 'budgetImpactChart'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el && el._fullLayout && typeof Plotly !== 'undefined') {
            Plotly.relayout(id, layoutUpdate);
        }
    });
}