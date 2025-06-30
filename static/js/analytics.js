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
    }
});

function initializeAnalytics() {
    console.log('📊 Initializing analytics page...');
    
    // Setup event listeners
    setupFilterEventListeners();
    setupPresetButtons();
    setupToggleFilters();
    
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
    const selects = ['ownersFilter', 'categoriesFilter', 'accountsFilter', 'typesFilter'];
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            select.addEventListener('change', handleMultiSelectChange);
        }
    });
    
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
        case '30':
            start = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));
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
    
    if (startDate) startDate.value = start.toISOString().split('T')[0];
    if (endDate) endDate.value = end.toISOString().split('T')[0];
    
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

function updateFilterIndicators() {
    const selects = ['ownersFilter', 'categoriesFilter', 'accountsFilter', 'typesFilter'];
    
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
    
    // Load charts in sequence
    Promise.all([
        loadSpendingTrends(),
        loadCategoryBreakdown(),
        loadOwnerComparison()
    ]).then(() => {
        showLoading(false);
        updateSummaryStats();
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

function loadCategoryBreakdown() {
    console.log('🥧 Loading category breakdown chart...');
    
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
            createCategoryPieChart(data);
            createCategoryBarChart(data);
            analyticsState.chartData.categoryBreakdown = data;
        })
        .catch(error => {
            console.error('Error loading category breakdown:', error);
            showChartError('categoryPieChart', 'Error loading category data');
            showChartError('categoryBarChart', 'Error loading category data');
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
    ['ownersFilter', 'categoriesFilter', 'accountsFilter', 'typesFilter'].forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            Array.from(select.options).forEach(option => {
                option.selected = option.value === 'all';
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
    ['ownersFilter', 'categoriesFilter', 'accountsFilter', 'typesFilter'].forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            Array.from(select.options).forEach(option => {
                option.selected = false;
            });
        }
    });
    
    // Clear amount inputs
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    
    // Apply filters
    applyFilters();
}

// Export analytics functions
window.Analytics = {
    applyFilters,
    resetAllFilters,
    clearAllFilters,
    loadAllCharts
};