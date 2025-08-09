/* Global JavaScript Functions and Utilities */

// Global chart configuration for Plotly
const chartConfig = {
    responsive: true,
    displayModeBar: false,
    layout: {
        font: {
            family: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
            size: 12
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 40, r: 20, b: 40, l: 60 },
        showlegend: false
    }
};

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = 
            '<div class="loading"><i class="fas fa-spinner"></i>Loading chart...</div>';
    }
}

function showChartError(elementId, error) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = 
            `<div class="alert alert-warning">Error loading chart: ${error}</div>`;
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Format percentage
function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

// Show alert message
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }
}

// Common chart creation functions
function createPieChart(elementId, data, title, colors = null) {
    const chartData = [{
        labels: data.map(item => item.label),
        values: data.map(item => item.value),
        type: 'pie',
        hole: 0.4,
        textinfo: 'label+percent',
        textposition: 'outside',
        marker: {
            colors: colors || ['#e74c3c', '#f39c12', '#27ae60', '#3498db', '#9b59b6', '#e67e22', '#1abc9c', '#34495e']
        }
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: title,
        showlegend: true,
        legend: {
            orientation: 'h',
            x: 0,
            y: -0.2
        }
    };
    
    Plotly.newPlot(elementId, chartData, layout, chartConfig);
}

function createBarChart(elementId, data, title, xAxisTitle, yAxisTitle) {
    const chartData = [{
        x: data.map(item => item.x),
        y: data.map(item => item.y),
        type: 'bar',
        marker: {
            color: '#3498db',
            opacity: 0.8
        },
        text: data.map(item => `${item.y.toFixed(2)}`),
        textposition: 'outside'
    }];
    
    const layout = {
        ...chartConfig.layout,
        title: title,
        xaxis: { title: xAxisTitle },
        yaxis: { title: yAxisTitle }
    };
    
    Plotly.newPlot(elementId, chartData, layout, chartConfig);
}

function createLineChart(elementId, traces, title, xAxisTitle, yAxisTitle) {
    const layout = {
        ...chartConfig.layout,
        title: title,
        xaxis: { title: xAxisTitle },
        yaxis: { title: yAxisTitle },
        hovermode: 'x unified',
        showlegend: traces.length > 1
    };
    
    Plotly.newPlot(elementId, traces, layout, chartConfig);
}

// API call wrapper with error handling
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Form validation helpers
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
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
    
    return isValid;
}

function clearFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const fields = form.querySelectorAll('.is-valid, .is-invalid');
    fields.forEach(field => {
        field.classList.remove('is-valid', 'is-invalid');
    });
}

// Date utilities
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function getTodaysDate() {
    return new Date().toISOString().split('T')[0];
}

function getMonthName(monthNumber) {
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[monthNumber - 1] || '';
}

// Number utilities
function formatNumber(number, decimals = 2) {
    return parseFloat(number).toFixed(decimals);
}

function parseAmount(amountString) {
    // Remove any non-numeric characters except decimal point and minus sign
    const cleaned = amountString.replace(/[^-\d.]/g, '');
    return parseFloat(cleaned) || 0;
}

// Local storage helpers (with fallback for environments that don't support it)
function setLocalStorage(key, value) {
    try {
        if (typeof(Storage) !== "undefined") {
            localStorage.setItem(key, JSON.stringify(value));
        }
    } catch (error) {
        console.warn('Local storage not available:', error);
    }
}

function getLocalStorage(key, defaultValue = null) {
    try {
        if (typeof(Storage) !== "undefined") {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        }
    } catch (error) {
        console.warn('Local storage not available:', error);
    }
    return defaultValue;
}

// Loading state management
function setLoadingState(elementId, isLoading) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (isLoading) {
        element.innerHTML = `
            <div class="d-flex justify-content-center align-items-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-2">Loading...</span>
            </div>
        `;
    }
}

// Common event handlers
function handleFormSubmit(formId, callback) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateForm(formId)) {
            callback(form);
        } else {
            showAlert('Please fill in all required fields correctly.', 'danger');
        }
    });
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Main JavaScript loaded');
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
            }
        });
    });
});

// Export functions for use in other scripts
window.FinanceUtils = {
    formatCurrency,
    formatPercent,
    formatDate,
    formatNumber,
    parseAmount,
    showAlert,
    showLoading,
    showChartError,
    createPieChart,
    createBarChart,
    createLineChart,
    apiCall,
    validateForm,
    clearFormValidation,
    setLoadingState,
    getTodaysDate,
    getMonthName
};