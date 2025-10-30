/* Analytics Page JavaScript */

// Analytics state management
let analyticsState = {
    currentFilters: {},
    chartData: {},
    isLoading: false
};

// Initialize analytics page
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/analytics')) {
        console.log('📊 Loading analytics functionality...');
        initializeAnalytics();
        loadMonthlySpendingMatrix();
    }
});

function initializeAnalytics() {
    console.log('📊 Initializing analytics page...');

    // Setup event listeners
    setupFilterEventListeners();
    setupPresetButtons();
    setupToggleFilters();
    setupYoYControls();

    // Load initial data
    loadInitialCharts();

    console.log('✅ Analytics page initialized');
}

// ============================================================================
// FILTER MANAGEMENT
// ============================================================================

function setupFilterEventListeners() {
    console.log('🔧 Setting up filter event listeners...');
    
    // Apply filters button
    const applyBtn = document.getElementById('applyFilters');
    if (applyBtn) {
        applyBtn.addEventListener('click', applyFilters);
    }
    
    // Reset filters button
    const resetBtn = document.getElementById('resetFilters');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetAllFilters);
    }
    
    // Clear filters button
    const clearBtn = document.getElementById('clearFilters');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAllFilters);
    }
    
    // Multi-select change handlers
    const selects = ['ownersFilter', 'categoriesFilter', 'subcategoriesFilter', 'accountsFilter', 'typesFilter'];
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            select.addEventListener('change', handleMultiSelectChange);
        }
    });
    
    // Special handler for categories to update subcategories
    const categoriesSelect = document.getElementById('categoriesFilter');
    if (categoriesSelect) {
        categoriesSelect.addEventListener('change', handleCategoriesChange);
    }
    
    console.log('✅ Filter event listeners set up');
}

function setupPresetButtons() {
    console.log('⚡ Setting up preset buttons...');
    
    const presetButtons = document.querySelectorAll('[data-preset]');
    presetButtons.forEach(button => {
        button.addEventListener('click', function() {
            const preset = this.getAttribute('data-preset');
            applyDatePreset(preset);
            
            // Update button states
            presetButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function setupToggleFilters() {
    const toggleBtn = document.getElementById('toggleFilters');
    const filterPanel = document.getElementById('filterPanel');
    
    if (toggleBtn && filterPanel) {
        toggleBtn.addEventListener('click', function() {
            filterPanel.classList.toggle('collapsed');
            const icon = this.querySelector('i');
            if (filterPanel.classList.contains('collapsed')) {
                icon.className = 'fas fa-filter-circle-xmark';
                this.textContent = ' Show Filters';
                this.prepend(icon);
            } else {
                icon.className = 'fas fa-filter';
                this.textContent = ' Filters';
                this.prepend(icon);
            }
        });
    }
}

function applyDatePreset(preset) {
    console.log(`📅 Applying date preset: ${preset}`);

    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const today = new Date();

    let start, end = today;

    switch(preset) {
        case 'this-month':
            start = new Date(today.getFullYear(), today.getMonth(), 1); // First day of current month
            end = today; // Today
            break;
        case '90':
            start = new Date(today.getTime() - (90 * 24 * 60 * 60 * 1000));
            break;
        case '365':
            start = new Date(today.getFullYear(), 0, 1); // Jan 1st this year
            break;
        case 'last-year':
            start = new Date(today.getFullYear() - 1, 0, 1); // Jan 1st last year
            end = new Date(today.getFullYear() - 1, 11, 31); // Dec 31st last year
            break;
        default:
            return;
    }

    // Format dates in local timezone (avoid toISOString() which converts to UTC)
    const formatLocalDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    if (startDate) startDate.value = formatLocalDate(start);
    if (endDate) endDate.value = formatLocalDate(end);

    // Auto-apply filters after preset
    setTimeout(applyFilters, 100);
}

function handleMultiSelectChange(event) {
    const select = event.target;
    const allOption = select.querySelector('option[value="all"]');
    
    if (event.target.value === 'all') {
        // If "all" is selected, deselect others
        Array.from(select.options).forEach(option => {
            option.selected = option.value === 'all';
        });
    } else {
        // If individual option selected, deselect "all"
        if (allOption) allOption.selected = false;
    }
    
    // Update visual indicators
    updateFilterIndicators();
}

function handleCategoriesChange(event) {
    console.log('📂 Categories changed, updating subcategories...');
    
    // First handle normal multi-select behavior
    handleMultiSelectChange(event);
    
    // Then update subcategories based on selected categories
    updateSubcategoriesOptions();
}

function updateSubcategoriesOptions() {
    const categoriesSelect = document.getElementById('categoriesFilter');
    const subcategoriesSelect = document.getElementById('subcategoriesFilter');
    
    if (!categoriesSelect || !subcategoriesSelect) return;
    
    const selectedCategories = getSelectedValues('categoriesFilter');
    const hasAllCategories = selectedCategories.includes('all');
    
    // Get all subcategory options
    const allSubcategoryOptions = Array.from(subcategoriesSelect.options);
    
    // Show/hide subcategory options based on selected categories
    allSubcategoryOptions.forEach(option => {
        if (option.value === 'all') {
            option.style.display = ''; // Always show "All" option
            return;
        }
        
        const optionCategory = option.getAttribute('data-category');
        
        if (hasAllCategories || selectedCategories.includes(optionCategory)) {
            option.style.display = '';
        } else {
            option.style.display = 'none';
            option.selected = false; // Deselect hidden options
        }
    });
    
    // If no subcategories are visible (except "All"), select "All"
    const visibleSubcategories = allSubcategoryOptions.filter(opt => 
        opt.value !== 'all' && opt.style.display !== 'none'
    );
    
    if (visibleSubcategories.length === 0) {
        const allOption = subcategoriesSelect.querySelector('option[value="all"]');
        if (allOption) allOption.selected = true;
    }
    
    updateFilterIndicators();
}

function updateFilterIndicators() {
    const selects = ['ownersFilter', 'categoriesFilter', 'subcategoriesFilter', 'accountsFilter', 'typesFilter'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            const selectedCount = Array.from(select.selectedOptions).length;
            const hasAll = Array.from(select.selectedOptions).some(opt => opt.value === 'all');
            
            // Add indicator class if specific items are selected
            if (selectedCount > 0 && !hasAll) {
                select.classList.add('filter-active-indicator');
            } else {
                select.classList.remove('filter-active-indicator');
            }
        }
    });
}

// ============================================================================
// DATA LOADING AND CHART CREATION
// ============================================================================

function loadInitialCharts() {
    console.log('📊 Loading initial charts...');
    
    // Set default filters
    analyticsState.currentFilters = getCurrentFilters();
    
    // Load all charts
    loadAllCharts();
}

function getCurrentFilters() {
    return {
        start_date: document.getElementById('startDate')?.value,
        end_date: document.getElementById('endDate')?.value,
        owners: getSelectedValues('ownersFilter'),
        categories: getSelectedValues('categoriesFilter'),
        subcategories: getSelectedValues('subcategoriesFilter'),
        accounts: getSelectedValues('accountsFilter'),
        types: getSelectedValues('typesFilter'),
        min_amount: document.getElementById('minAmount')?.value || null,
        max_amount: document.getElementById('maxAmount')?.value || null
    };
}

function getSelectedValues(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return [];
    
    const selected = Array.from(select.selectedOptions).map(opt => opt.value);
    return selected.includes('all') ? ['all'] : selected;
}

function applyFilters() {
    console.log('🔍 Applying filters...');
    
    // Update current filters
    analyticsState.currentFilters = getCurrentFilters();
    
    // Show loading
    showLoading(true);
    
    // Load charts with new filters
    loadAllCharts();
}

function loadAllCharts() {
    console.log('📈 Loading all charts with current filters...');

    // Load charts and tables in sequence
    Promise.all([
        loadSpendingTrends(),
        loadCategoryTables(),
        loadSubcategoryTable(),
        loadTransactionTypesTable(),
        loadOwnerComparison()
    ]).then(() => {
        showLoading(false);
        updateSummaryStats();
        fetchFilteredTransactions(); // Add transaction list update
        console.log('✅ All charts loaded successfully');
    }).catch(error => {
        console.error('❌ Error loading charts:', error);
        showLoading(false);
        FinanceUtils.showAlert('Error loading chart data', 'danger');
    });
}

function loadSpendingTrends() {
    console.log('📈 Loading spending trends chart...');
    
    const params = new URLSearchParams();
    Object.keys(analyticsState.currentFilters).forEach(key => {
        const value = analyticsState.currentFilters[key];
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
        } else if (value !== null && value !== '') {
            params.append(key, value);
        }
    });
    
    return fetch(`/analytics/api/spending_trends?${params}`)
        .then(response => response.json())
        .then(data => {
            createSpendingTrendsChart(data);
            analyticsState.chartData.spendingTrends = data;
        })
        .catch(error => {
            console.error('Error loading spending trends:', error);
            showChartError('spendingTrendsChart', 'Error loading spending trends');
        });
}

function loadCategoryTables() {
    console.log('📊 Loading category tables...');
    
    const params = new URLSearchParams();
    Object.keys(analyticsState.currentFilters).forEach(key => {
        const value = analyticsState.currentFilters[key];
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
        } else if (value !== null && value !== '') {
            params.append(key, value);
        }
    });
    
    return fetch(`/analytics/api/category_breakdown?${params}`)
        .then(response => response.json())
        .then(data => {
            renderCategoryTables(data);
            analyticsState.chartData.categoryBreakdown = data;
        })
        .catch(error => {
            console.error('Error loading category breakdown:', error);
            showTableError('categoryAmountsTable', 'Error loading category data');
            showTableError('categoryCountsTable', 'Error loading category data');
        });
}

function loadSubcategoryTable() {
    console.log('🔍 Loading subcategory table...');
    
    const params = new URLSearchParams();
    Object.keys(analyticsState.currentFilters).forEach(key => {
        const value = analyticsState.currentFilters[key];
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
        } else if (value !== null && value !== '') {
            params.append(key, value);
        }
    });
    
    return fetch(`/analytics/api/subcategory_breakdown?${params}`)
        .then(response => response.json())
        .then(data => {
            renderSubcategoryTable(data);
            analyticsState.chartData.subcategoryBreakdown = data;
        })
        .catch(error => {
            console.error('Error loading subcategory breakdown:', error);
            showTableError('subcategoryAmountsTable', 'Error loading subcategory data');
        });
}

function loadTransactionTypesTable() {
    console.log('💳 Loading transaction types table...');

    const params = new URLSearchParams();
    Object.keys(analyticsState.currentFilters).forEach(key => {
        const value = analyticsState.currentFilters[key];
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
        } else if (value !== null && value !== '') {
            params.append(key, value);
        }
    });

    return fetch(`/analytics/api/transaction_types_breakdown?${params}`)
        .then(response => response.json())
        .then(data => {
            renderTransactionTypesTable(data);
            analyticsState.chartData.transactionTypes = data;
        })
        .catch(error => {
            console.error('Error loading transaction types:', error);
            showTableError('transactionTypesTable', 'Error loading transaction types data');
        });
}

function loadOwnerComparison() {
    console.log('👥 Loading owner comparison chart...');

    const params = new URLSearchParams();
    Object.keys(analyticsState.currentFilters).forEach(key => {
        const value = analyticsState.currentFilters[key];
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v));
        } else if (value !== null && value !== '') {
            params.append(key, value);
        }
    });

    return fetch(`/analytics/api/owner_comparison?${params}`)
        .then(response => response.json())
        .then(data => {
            createOwnerComparisonChart(data);
            analyticsState.chartData.ownerComparison = data;
        })
        .catch(error => {
            console.error('Error loading owner comparison:', error);
            showChartError('ownerComparisonChart', 'Error loading owner comparison');
        });
}

// ============================================================================
// CHART CREATION FUNCTIONS
// ============================================================================

function createSpendingTrendsChart(data) {
    console.log('📈 Creating spending trends chart with data:', data);
    
    if (!data || data.length === 0) {
        showChartError('spendingTrendsChart', 'No data available for selected filters');
        return;
    }
    
    // Get all unique types
    const types = new Set();
    data.forEach(month => {
        Object.keys(month).forEach(key => {
            if (key !== 'month') types.add(key);
        });
    });
    
    const traces = Array.from(types).map((type, index) => ({
        x: data.map(item => item.month),
        y: data.map(item => item[type]?.total || 0),
        name: type,
        type: 'scatter',
        mode: 'lines+markers',
        line: { width: 3 },
        marker: { size: 8 },
        hovertemplate: '<b>%{fullData.name}</b><br>%{x}<br>Amount: $%{y:.2f}<extra></extra>'
    }));
    
    const layout = {
        ...chartConfig.layout,
        title: 'Spending Trends Over Time',
        xaxis: { 
            title: 'Month',
            showgrid: true
        },
        yaxis: { 
            title: 'Amount ($)',
            showgrid: true
        },
        height: 400,
        hovermode: 'x unified',
        showlegend: true
    };
    
    Plotly.newPlot('spendingTrendsChart', traces, layout, chartConfig);
}

function createCategoryPieChart(data) {
    console.log('🥧 Creating category pie chart with data:', data);
    
    if (!data || data.length === 0) {
        showChartError('categoryPieChart', 'No category data available');
        return;
    }
    
    const chartData = [{
        labels: data.map(item => item.category),
        values: data.map(item => item.total),
        type: 'pie',
        hole: 0.4,
        textinfo: 'label+percent',
        textposition: 'outside',
        hovertemplate: '<b>%{label}</b><br>Amount: $%{value:.2f}<br>Percentage: %{percent}<extra></extra>'
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Category Distribution',
        height: 400,
        showlegend: false
    };
    
    Plotly.newPlot('categoryPieChart', chartData, layout, chartConfig);
}

function createCategoryBarChart(data) {
    console.log('📊 Creating category bar chart with data:', data);
    
    if (!data || data.length === 0) {
        showChartError('categoryBarChart', 'No category data available');
        return;
    }
    
    const chartData = [{
        x: data.map(item => item.total),
        y: data.map(item => item.category),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: data.map((_, i) => `hsl(${i * 360 / data.length}, 70%, 50%)`),
            opacity: 0.8
        },
        text: data.map(item => `$${item.total.toFixed(2)}`),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Amount: $%{x:.2f}<br>Transactions: %{customdata}<extra></extra>',
        customdata: data.map(item => item.transaction_count)
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: 'Category Amounts',
        xaxis: { 
            title: 'Amount ($)',
            showgrid: true
        },
        yaxis: { 
            title: '',
            automargin: true
        },
        height: 400,
        showlegend: false
    };
    
    Plotly.newPlot('categoryBarChart', chartData, layout, chartConfig);
}

// ============================================================================
// TABLE RENDERING FUNCTIONS
// ============================================================================

function renderCategoryTables(data) {
    console.log('📊 Rendering category tables with data:', data);
    
    if (!data || data.length === 0) {
        showTableError('categoryAmountsTable', 'No category data available');
        showTableError('categoryCountsTable', 'No category data available');
        return;
    }
    
    // Sort by amount for amounts table (top 10)
    const sortedByAmount = [...data].sort((a, b) => b.total - a.total).slice(0, 10);
    renderCategoryAmountsTable(sortedByAmount);
    
    // Sort by transaction count for counts table (top 10)
    const sortedByCount = [...data].sort((a, b) => b.transaction_count - a.transaction_count).slice(0, 10);
    renderCategoryCountsTable(sortedByCount);
}

function renderCategoryAmountsTable(data) {
    const tbody = document.getElementById('categoryAmountsTable');
    if (!tbody) return;
    
    const totalAmount = data.reduce((sum, item) => sum + item.total, 0);
    
    tbody.innerHTML = '';
    data.forEach((item, index) => {
        const percentage = ((item.total / totalAmount) * 100).toFixed(1);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${index + 1}</td>
            <td>${item.category}</td>
            <td class="text-end fw-bold">$${item.total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="text-end text-muted">${percentage}%</td>
        `;
        tbody.appendChild(row);
    });
}

function renderCategoryCountsTable(data) {
    const tbody = document.getElementById('categoryCountsTable');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    data.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${index + 1}</td>
            <td>${item.category}</td>
            <td class="text-end fw-bold">${item.transaction_count}</td>
            <td class="text-end text-muted">$${item.avg_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderSubcategoryTable(data) {
    console.log('🔍 Rendering subcategory table with data:', data);

    const tbody = document.getElementById('subcategoryAmountsTable');
    if (!tbody) return;

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No subcategory data available</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    data.slice(0, 10).forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${index + 1}</td>
            <td>
                ${item.subcategory}
                <br><small class="text-muted">${item.category}</small>
            </td>
            <td class="text-end fw-bold">$${item.total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="text-end text-muted">${item.transaction_count}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderTransactionTypesTable(data) {
    console.log('💳 Rendering transaction types table with data:', data);

    const tbody = document.getElementById('transactionTypesTable');
    if (!tbody) return;

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No transaction types data available</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    data.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-bold">${index + 1}</td>
            <td>${item.type}</td>
            <td class="text-end fw-bold">$${item.total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="text-end text-muted">${item.transaction_count}</td>
        `;
        tbody.appendChild(row);
    });
}

function showTableError(tableId, message) {
    const tbody = document.getElementById(tableId);
    if (!tbody) return;
    
    const columnCount = tbody.closest('table').querySelector('thead tr').children.length;
    tbody.innerHTML = `<tr><td colspan="${columnCount}" class="text-center text-danger">${message}</td></tr>`;
}

function createOwnerComparisonChart(data) {
    console.log('👥 Creating owner comparison chart with data:', data);
    
    if (!data || data.length === 0) {
        showChartError('ownerComparisonChart', 'No owner data available');
        return;
    }
    
    // Get all unique types
    const types = new Set();
    data.forEach(owner => {
        Object.keys(owner.types).forEach(type => types.add(type));
    });
    
    const traces = Array.from(types).map((type, index) => ({
        x: data.map(owner => owner.owner),
        y: data.map(owner => owner.types[type]?.total || 0),
        name: type,
        type: 'bar',
        marker: {
            color: ['#e74c3c', '#f39c12', '#27ae60', '#3498db'][index] || '#6c757d',
            opacity: 0.8
        },
        hovertemplate: '<b>%{fullData.name}</b><br>%{x}<br>Amount: $%{y:.2f}<extra></extra>'
    }));
    
    const layout = {
        ...chartConfig.layout,
        title: 'Owner Spending Comparison by Type',
        barmode: 'group',
        xaxis: { title: 'Owner' },
        yaxis: { 
            title: 'Amount ($)',
            showgrid: true
        },
        height: 400,
        showlegend: true
    };
    
    Plotly.newPlot('ownerComparisonChart', traces, layout, chartConfig);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'block' : 'none';
        if (show) {
            loadingIndicator.classList.add('fade-in');
        }
    }
    analyticsState.isLoading = show;
}

function showChartError(chartId, message) {
    const chartElement = document.getElementById(chartId);
    if (chartElement) {
        chartElement.innerHTML = `
            <div class="chart-error">
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p>${message}</p>
                </div>
            </div>
        `;
    }
}

function updateSummaryStats() {
    console.log('📊 Updating summary statistics...');
    
    // Calculate totals from chart data
    let totalTransactions = 0;
    let totalAmount = 0;
    
    if (analyticsState.chartData.categoryBreakdown) {
        analyticsState.chartData.categoryBreakdown.forEach(category => {
            totalTransactions += category.transaction_count;
            totalAmount += category.total;
        });
    }
    
    const avgTransaction = totalTransactions > 0 ? totalAmount / totalTransactions : 0;
    
    // Update DOM
    const totalTransactionsEl = document.getElementById('totalTransactions');
    const totalAmountEl = document.getElementById('totalAmount');
    const avgTransactionEl = document.getElementById('avgTransaction');
    const dateRangeEl = document.getElementById('dateRange');
    
    if (totalTransactionsEl) totalTransactionsEl.textContent = totalTransactions.toLocaleString();
    if (totalAmountEl) totalAmountEl.textContent = `$${totalAmount.toFixed(2)}`;
    if (avgTransactionEl) avgTransactionEl.textContent = `$${avgTransaction.toFixed(2)}`;
    
    if (dateRangeEl) {
        const start = analyticsState.currentFilters.start_date;
        const end = analyticsState.currentFilters.end_date;
        if (start && end) {
            const days = Math.ceil((new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24));
            dateRangeEl.textContent = `${days} days`;
        }
    }
}

function resetAllFilters() {
    console.log('🔄 Resetting all filters...');
    
    // Reset to defaults from window.analyticsData
    if (window.analyticsData) {
        document.getElementById('startDate').value = window.analyticsData.defaultStartDate;
        document.getElementById('endDate').value = window.analyticsData.defaultEndDate;
    }
    
    // Reset multi-selects to "all"
    ['ownersFilter', 'categoriesFilter', 'subcategoriesFilter', 'accountsFilter', 'typesFilter'].forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            Array.from(select.options).forEach(option => {
                option.selected = option.value === 'all';
                option.style.display = ''; // Show all options
            });
        }
    });
    
    // Clear amount inputs
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    
    // Clear preset button states
    document.querySelectorAll('[data-preset]').forEach(btn => btn.classList.remove('active'));
    
    // Apply filters
    applyFilters();
}

function clearAllFilters() {
    console.log('🗑️ Clearing all filters...');
    
    // Clear date inputs
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    
    // Clear all multi-selects
    ['ownersFilter', 'categoriesFilter', 'subcategoriesFilter', 'accountsFilter', 'typesFilter'].forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            Array.from(select.options).forEach(option => {
                option.selected = false;
                option.style.display = ''; // Show all options
            });
        }
    });
    
    // Clear amount inputs
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    
    // Apply filters
    applyFilters();
}

// Fetch and render filtered transactions for the summary table
function fetchFilteredTransactions() {
    const filters = analyticsState.currentFilters || getCurrentFilters();
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.owners && filters.owners.length) filters.owners.forEach(o => params.append('owners', o));
    if (filters.categories && filters.categories.length) filters.categories.forEach(c => params.append('categories', c));
    if (filters.subcategories && filters.subcategories.length) filters.subcategories.forEach(s => params.append('subcategories', s));
    if (filters.accounts && filters.accounts.length) filters.accounts.forEach(a => params.append('accounts', a));
    if (filters.types && filters.types.length) filters.types.forEach(t => params.append('types', t));
    if (filters.min_amount) params.append('min_amount', filters.min_amount);
    if (filters.max_amount) params.append('max_amount', filters.max_amount);
    const tbody = document.getElementById('filteredTransactionsBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Loading...</td></tr>';
    fetch(`/analytics/api/filtered_transactions?${params}`)
        .then(res => res.json())
        .then(data => {
            renderFilteredTransactionsTable(data);
        })
        .catch(err => {
            if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-danger text-center">Error loading transactions</td></tr>`;
        });
}

function renderFilteredTransactionsTable(transactions) {
    const tbody = document.getElementById('filteredTransactionsBody');
    if (!tbody) return;
    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No transactions found for current filters.</td></tr>';
        return;
    }
    tbody.innerHTML = '';
    transactions.forEach(tx => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${tx.date}</td>
            <td>${tx.description || ''}</td>
            <td class="text-end">$${parseFloat(tx.amount).toFixed(2)}</td>
            <td>${tx.category || ''}</td>
            <td>${tx.sub_category || '-'}</td>
            <td>${tx.owner || ''}</td>
            <td>${tx.account_name || ''}</td>
            <td>${tx.type || ''}</td>
        `;
        tbody.appendChild(row);
    });
}

function setupYoYControls() {
    console.log('📅 Setting up Year-over-Year controls...');

    // Setup toggle event listeners
    const yearlyRadio = document.getElementById('yoyViewYearly');
    const categoryRadio = document.getElementById('yoyViewCategory');
    const categorySelector = document.getElementById('yoyCategorySelector');
    const categorySelect = document.getElementById('yoyCategorySelect');

    if (yearlyRadio && categoryRadio && categorySelector) {
        // Handle toggle change
        const handleToggleChange = () => {
            const viewType = document.querySelector('input[name="yoyViewType"]:checked')?.value;
            if (viewType === 'category') {
                categorySelector.style.display = 'block';
                populateYoYCategorySelect();
            } else {
                categorySelector.style.display = 'none';
            }
            loadMonthlySpendingMatrix();
        };

        yearlyRadio.addEventListener('change', handleToggleChange);
        categoryRadio.addEventListener('change', handleToggleChange);

        // Handle category selection change
        if (categorySelect) {
            categorySelect.addEventListener('change', () => {
                loadMonthlySpendingMatrix();
            });
        }
    }
}

function populateYoYCategorySelect() {
    const categorySelect = document.getElementById('yoyCategorySelect');
    if (!categorySelect) return;

    // Fetch categories, subcategories, and owners from the database
    fetch('/analytics/api/filtered_transactions')
        .then(res => res.json())
        .then(data => {
            // Extract unique categories, subcategories, and owners
            const categories = new Set();
            const subcategories = new Set();
            const owners = new Set();

            data.forEach(txn => {
                if (txn.category) categories.add(txn.category);
                if (txn.sub_category) subcategories.add(txn.sub_category);
                if (txn.owner) owners.add(txn.owner);
            });

            // Build options
            let options = '<option value="">Select Filter...</option>';

            // Add category options
            if (categories.size > 0) {
                options += '<optgroup label="Categories">';
                Array.from(categories).sort().forEach(cat => {
                    options += `<option value="category:${cat}">${cat}</option>`;
                });
                options += '</optgroup>';
            }

            // Add subcategory options
            if (subcategories.size > 0) {
                options += '<optgroup label="Subcategories">';
                Array.from(subcategories).sort().forEach(subcat => {
                    options += `<option value="subcategory:${subcat}">${subcat}</option>`;
                });
                options += '</optgroup>';
            }

            // Add owner options
            if (owners.size > 0) {
                options += '<optgroup label="Owners">';
                Array.from(owners).sort().forEach(owner => {
                    options += `<option value="owner:${owner}">${owner}</option>`;
                });
                options += '</optgroup>';
            }

            categorySelect.innerHTML = options;
        })
        .catch(err => {
            console.error('Error loading filter options:', err);
        });
}

function loadMonthlySpendingMatrix() {
    const container = document.getElementById('monthlySpendingMatrixContainer');
    if (!container) return;

    // Get current view type and selected category
    const viewType = document.querySelector('input[name="yoyViewType"]:checked')?.value || 'yearly';
    const categoryValue = document.getElementById('yoyCategorySelect')?.value || '';

    container.innerHTML = '<div class="text-center text-muted">Loading table...</div>';

    // Build API URL with parameters
    let apiUrl = '/analytics/api/monthly_spending_matrix';
    const params = new URLSearchParams();

    if (viewType === 'category' && categoryValue) {
        // Parse category value (format: "category:value" or "subcategory:value")
        const [filterType, filterValue] = categoryValue.split(':');
        params.append('filter_type', filterType);
        params.append('filter_value', filterValue);
    }

    if (params.toString()) {
        apiUrl += '?' + params.toString();
    }

    fetch(apiUrl)
        .then(res => res.json())
        .then(matrix => {
            if (!matrix || Object.keys(matrix).length === 0) {
                container.innerHTML = '<div class="text-center text-muted">No data available.</div>';
                return;
            }
            container.innerHTML = renderMonthlySpendingMatrixTable(matrix);
        })
        .catch(() => {
            container.innerHTML = '<div class="text-center text-danger">Error loading table.</div>';
        });
}

function renderMonthlySpendingMatrixTable(matrix) {
    // Get all months present in the data
    const months = [
        '01','02','03','04','05','06','07','08','09','10','11','12'
    ];
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const years = Object.keys(matrix).sort();
    let html = '<div class="table-responsive"><table class="table table-bordered table-sm align-middle text-center">';
    // Header row
    html += '<thead><tr><th>Year</th>';
    months.forEach((m,i) => {
        html += `<th>${monthNames[i]}</th><th>%</th>`;
    });
    html += '</tr></thead><tbody>';
    // Data rows
    years.forEach((year, yIdx) => {
        html += `<tr><th>${year}</th>`;
        months.forEach(m => {
            const cell = matrix[year][m] || {total: 0, pct_change: null};
            html += `<td>$${cell.total.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>`;
            if (yIdx === 0) {
                html += '<td>-</td>';
            } else {
                const pct = cell.pct_change;
                let pctStr = pct === null ? '-' : (pct > 0 ? '+' : '') + pct.toFixed(1) + '%';
                let pctClass = pct > 0 ? 'text-success' : (pct < 0 ? 'text-danger' : 'text-muted');
                html += `<td class="${pctClass}">${pctStr}</td>`;
            }
        });
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
}

// Hook into filter application to update the table
const origApplyFilters = applyFilters;
applyFilters = function() {
    if (typeof origApplyFilters === 'function') origApplyFilters();
    fetchFilteredTransactions();
};
// Also fetch on initial load
if (window.location.pathname.includes('/analytics')) {
    document.addEventListener('DOMContentLoaded', fetchFilteredTransactions);
}

// Export analytics functions
window.Analytics = {
    applyFilters,
    resetAllFilters,
    clearAllFilters,
    loadAllCharts
};