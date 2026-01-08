// State management
let contractsTable = null;
let allContracts = [];
let allCustomers = [];
let allProducts = [];
let selectedContracts = new Set();

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initDataTable();
    loadCustomers();
    loadProducts();
    loadContracts();
});

function initDataTable() {
    contractsTable = $('#contractsTable').DataTable({
        order: [[5, 'desc']], // Sort by date descending (adjusted for checkbox column)
        columns: [
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    return `<input type="checkbox" class="contract-checkbox" data-contract-id="${row.id}" onchange="toggleContractSelection(${row.id}, this.checked)">`;
                }
            },
            {
                data: 'id',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'status',
                render: function(data) {
                    if (data === 'draft') {
                        return '<span style="color: orange; font-weight: bold;">DRAFT</span>';
                    } else if (data === 'active') {
                        return '<span style="color: green; font-weight: bold;">ACTIVE</span>';
                    } else if (data === 'terminated') {
                        return '<span style="color: red;">TERMINATED</span>';
                    } else if (data === 'replaced') {
                        return '<span style="color: gray;">REPLACED</span>';
                    }
                    return data || 'N/A';
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    return row.customer ? row.customer.company_name : 'N/A';
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    if (!row.customer || !row.customer.category) return 'N/A';
                    return row.customer.category.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    if (!row.contract_products || row.contract_products.length === 0) {
                        return 'N/A';
                    }
                    const productList = row.contract_products.map(cp => {
                        if (!cp.product) return 'Unknown';
                        const p = cp.product;
                        let text = p.product_type;
                        if (p.volume_tb) text += ` ${p.volume_tb}TB`;
                        if (p.subtype) text += ` (${p.subtype})`;
                        if (cp.quantity > 1) text += ` ×${cp.quantity}`;
                        return text;
                    }).join(', ');
                    return productList;
                }
            },
            {
                data: 'contract_date',
                render: function(data) {
                    return data ? formatDate(data) : 'N/A';
                }
            },
            {
                data: 'contract_duration',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'contract_value',
                render: function(data) {
                    return data ? formatNumber(data) : 'N/A';
                }
            },
            {
                data: 'arr',
                render: function(data) {
                    return data ? formatNumber(data) : 'N/A';
                }
            },
            {
                data: 'original_filename',
                orderable: false,
                render: function(data, type, row) {
                    if (!data) return 'N/A';
                    return `<a href="/api/files/${encodeURIComponent(data)}" target="_blank" title="View PDF" style="font-size: 16px; text-decoration: none;">📄</a>`;
                }
            },
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    return `
                        <button onclick="editContract(${row.id})" title="Edit contract" style="background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px;">✏️</button>
                        <button onclick="deleteContract(${row.id})" title="Delete contract" style="background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px;">🗑️</button>
                    `;
                }
            }
        ]
    });
}

async function loadContracts() {
    try {
        const response = await fetch('/api/contracts');

        if (!response.ok) {
            throw new Error('Failed to load contracts');
        }

        allContracts = await response.json();

        // Clear selection when reloading
        clearSelection();

        // Update DataTable
        contractsTable.clear();
        contractsTable.rows.add(allContracts);
        contractsTable.draw();

        // Populate filter dropdowns with unique values
        populateFilterDropdowns();

    } catch (error) {
        console.error('Error loading contracts:', error);
        showMessage('Error loading contracts.', 'error');
    }
}

async function loadCustomers() {
    try {
        const response = await fetch('/api/customers');
        if (response.ok) {
            allCustomers = await response.json();
        }
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        if (response.ok) {
            allProducts = await response.json();
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

function editContract(contractId) {
    // Redirect to main page with contract ID to edit
    window.location.href = `/?edit=${contractId}`;
}

async function deleteContract(contractId) {
    if (!confirm('Are you sure you want to delete this contract?')) {
        return;
    }

    try {
        const response = await fetch(`/api/contracts/${contractId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete contract');
        }

        showMessage('Contract deleted successfully.', 'success');
        await loadContracts();

    } catch (error) {
        console.error('Error deleting contract:', error);
        showMessage('Error deleting contract.', 'error');
    }
}

function showMessage(text, type) {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type} show`;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 5000);
}

function formatDate(dateString) {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB');
}

function formatNumber(num) {
    if (num === null || num === undefined) return null;
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function populateFilterDropdowns() {
    // Populate customer filter
    const customerSelect = document.getElementById('filterCustomer');
    const currentCustomerValue = customerSelect.value;

    // Get unique customers from contracts
    const uniqueCustomers = new Set();
    allContracts.forEach(contract => {
        if (contract.customer && contract.customer.company_name) {
            uniqueCustomers.add(JSON.stringify({
                id: contract.customer.id,
                name: contract.customer.company_name
            }));
        }
    });

    customerSelect.innerHTML = '<option value="">All Customers</option>';
    Array.from(uniqueCustomers)
        .map(str => JSON.parse(str))
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(customer => {
            const option = document.createElement('option');
            option.value = customer.id;
            option.textContent = customer.name;
            customerSelect.appendChild(option);
        });

    if (currentCustomerValue) {
        customerSelect.value = currentCustomerValue;
    }

    // Populate product filter
    const productSelect = document.getElementById('filterProduct');
    const currentProductValue = productSelect.value;

    // Get unique product types from contracts
    const uniqueProductTypes = new Set();
    allContracts.forEach(contract => {
        if (contract.contract_products) {
            contract.contract_products.forEach(cp => {
                if (cp.product && cp.product.product_type) {
                    uniqueProductTypes.add(cp.product.product_type);
                }
            });
        }
    });

    productSelect.innerHTML = '<option value="">All Products</option>';
    Array.from(uniqueProductTypes)
        .sort()
        .forEach(productType => {
            const option = document.createElement('option');
            option.value = productType;
            option.textContent = productType;
            productSelect.appendChild(option);
        });

    if (currentProductValue) {
        productSelect.value = currentProductValue;
    }
}

function applyFilters() {
    const contractIdFilter = document.getElementById('filterContractId').value;
    const statusFilter = document.getElementById('filterStatus').value;
    const customerFilter = document.getElementById('filterCustomer').value;
    const productFilter = document.getElementById('filterProduct').value;
    const dateFromFilter = document.getElementById('filterDateFrom').value;
    const dateToFilter = document.getElementById('filterDateTo').value;
    const durationMinFilter = document.getElementById('filterDurationMin').value;
    const durationMaxFilter = document.getElementById('filterDurationMax').value;

    // Clear selection when filtering
    clearSelection();

    const filteredContracts = allContracts.filter(contract => {
        // Contract ID filter
        if (contractIdFilter && contract.id != contractIdFilter) {
            return false;
        }

        // Status filter
        if (statusFilter && contract.status !== statusFilter) {
            return false;
        }

        // Customer filter
        if (customerFilter && (!contract.customer || contract.customer.id != customerFilter)) {
            return false;
        }

        // Product filter
        if (productFilter) {
            const hasProduct = contract.contract_products && contract.contract_products.some(cp =>
                cp.product && cp.product.product_type === productFilter
            );
            if (!hasProduct) {
                return false;
            }
        }

        // Date from filter
        if (dateFromFilter && contract.contract_date) {
            if (contract.contract_date < dateFromFilter) {
                return false;
            }
        }

        // Date to filter
        if (dateToFilter && contract.contract_date) {
            if (contract.contract_date > dateToFilter) {
                return false;
            }
        }

        // Duration min filter
        if (durationMinFilter && contract.contract_duration) {
            if (contract.contract_duration < parseInt(durationMinFilter)) {
                return false;
            }
        }

        // Duration max filter
        if (durationMaxFilter && contract.contract_duration) {
            if (contract.contract_duration > parseInt(durationMaxFilter)) {
                return false;
            }
        }

        return true;
    });

    // Update DataTable
    contractsTable.clear();
    contractsTable.rows.add(filteredContracts);
    contractsTable.draw();
}

function clearFilters() {
    document.getElementById('filterContractId').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterCustomer').value = '';
    document.getElementById('filterProduct').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    document.getElementById('filterDurationMin').value = '';
    document.getElementById('filterDurationMax').value = '';

    // Reset to show all contracts
    contractsTable.clear();
    contractsTable.rows.add(allContracts);
    contractsTable.draw();
}

// Bulk selection functions
function toggleContractSelection(contractId, isChecked) {
    if (isChecked) {
        selectedContracts.add(contractId);
    } else {
        selectedContracts.delete(contractId);
    }
    updateBulkActionsToolbar();
}

function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.contract-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        const contractId = parseInt(cb.getAttribute('data-contract-id'));
        if (checkbox.checked) {
            selectedContracts.add(contractId);
        } else {
            selectedContracts.delete(contractId);
        }
    });
    updateBulkActionsToolbar();
}

function updateBulkActionsToolbar() {
    const toolbar = document.getElementById('bulkActionsToolbar');
    const count = selectedContracts.size;

    if (count > 0) {
        toolbar.style.display = 'block';
        document.getElementById('selectedCount').textContent = `${count} contract${count > 1 ? 's' : ''} selected`;
    } else {
        toolbar.style.display = 'none';
    }
}

function clearSelection() {
    selectedContracts.clear();
    document.getElementById('selectAll').checked = false;
    document.querySelectorAll('.contract-checkbox').forEach(cb => cb.checked = false);
    updateBulkActionsToolbar();
}

async function bulkUpdateStatus(newStatus) {
    if (selectedContracts.size === 0) {
        showMessage('No contracts selected.', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to change ${selectedContracts.size} contract(s) to status "${newStatus.toUpperCase()}"?`)) {
        return;
    }

    const contractIds = Array.from(selectedContracts);
    let successCount = 0;
    let errorCount = 0;

    for (const contractId of contractIds) {
        try {
            const response = await fetch(`/api/contracts/${contractId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                successCount++;
            } else {
                errorCount++;
            }
        } catch (error) {
            console.error(`Error updating contract ${contractId}:`, error);
            errorCount++;
        }
    }

    // Show result message
    if (errorCount === 0) {
        showMessage(`Successfully updated ${successCount} contract(s) to ${newStatus.toUpperCase()}.`, 'success');
    } else {
        showMessage(`Updated ${successCount} contract(s), but ${errorCount} failed.`, 'error');
    }

    // Clear selection and reload
    clearSelection();
    await loadContracts();
}
