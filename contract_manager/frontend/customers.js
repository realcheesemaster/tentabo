// State management
let customersTable = null;
let pennylaneCustomersTable = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initDataTable();
    initPennylaneDataTable();
    loadCustomers();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('customerForm').addEventListener('submit', handleFormSubmit);
}

function initDataTable() {
    customersTable = $('#customersTable').DataTable({
        order: [[1, 'asc']], // Sort by company name ascending
        columns: [
            {
                data: 'id',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'company_name',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'national_identifier',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'category',
                render: function(data) {
                    if (!data) return 'N/A';
                    return data.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
                }
            },
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    // Count contracts for this customer
                    return `<a href="/contracts?customer_id=${row.id}">View Contracts</a>`;
                }
            },
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    return `
                        <button class="btn" onclick="editCustomer(${row.id})">Edit</button>
                    `;
                }
            }
        ]
    });
}

async function loadCustomers() {
    try {
        const response = await fetch('/api/customers?limit=1000');

        if (!response.ok) {
            throw new Error('Failed to load customers');
        }

        const customers = await response.json();

        // Update DataTable
        customersTable.clear();
        customersTable.rows.add(customers);
        customersTable.draw();

    } catch (error) {
        console.error('Error loading customers:', error);
        showMessage('Error loading customers.', 'error');
    }
}

function showAddCustomerForm() {
    document.getElementById('formTitle').textContent = 'Add New Customer';
    document.getElementById('customerForm').reset();
    document.getElementById('customerId').value = '';
    document.getElementById('customerFormSection').classList.add('active');
    document.getElementById('customerFormSection').scrollIntoView({ behavior: 'smooth' });
}

async function editCustomer(customerId) {
    try {
        const response = await fetch(`/api/customers/${customerId}`);

        if (!response.ok) {
            throw new Error('Failed to load customer');
        }

        const customer = await response.json();

        // Populate form
        document.getElementById('formTitle').textContent = 'Edit Customer';
        document.getElementById('customerId').value = customer.id;
        document.getElementById('companyName').value = customer.company_name || '';
        document.getElementById('nationalIdentifier').value = customer.national_identifier || '';
        document.getElementById('category').value = customer.category || 'end-user';

        // Show form
        document.getElementById('customerFormSection').classList.add('active');
        document.getElementById('customerFormSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error loading customer:', error);
        showMessage('Error loading customer.', 'error');
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();

    const customerId = document.getElementById('customerId').value;
    const customerData = {
        company_name: document.getElementById('companyName').value,
        national_identifier: document.getElementById('nationalIdentifier').value,
        category: document.getElementById('category').value
    };

    try {
        let response;
        if (customerId) {
            // Update existing customer
            response = await fetch(`/api/customers/${customerId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(customerData)
            });
        } else {
            // Create new customer
            response = await fetch('/api/customers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(customerData)
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save customer');
        }

        showMessage(customerId ? 'Customer updated successfully!' : 'Customer created successfully!', 'success');

        // Reload customers list
        await loadCustomers();

        // Hide form
        cancelForm();

    } catch (error) {
        console.error('Error saving customer:', error);
        showMessage(error.message || 'Error saving customer. Please try again.', 'error');
    }
}

function cancelForm() {
    document.getElementById('customerForm').reset();
    document.getElementById('customerFormSection').classList.remove('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
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

// Tab switching
function switchTab(tab) {
    // Update tab buttons
    document.getElementById('tabContract').classList.remove('active');
    document.getElementById('tabPennylane').classList.remove('active');

    if (tab === 'contract') {
        document.getElementById('tabContract').classList.add('active');
        document.getElementById('contractCustomersSection').style.display = 'block';
        document.getElementById('pennylaneCustomersSection').style.display = 'none';
    } else {
        document.getElementById('tabPennylane').classList.add('active');
        document.getElementById('contractCustomersSection').style.display = 'none';
        document.getElementById('pennylaneCustomersSection').style.display = 'block';

        // Load first page of Pennylane customers if not already loaded
        if (pennylaneCustomersTable && pennylaneCustomersTable.data().count() === 0) {
            loadPennylaneCustomers();
        }
    }
}

// Pennylane customers with pagination
let customerLinks = {};  // Store customer links
let pennylaneAllCustomers = [];  // Store all loaded customers
let pennylanePageCursors = [null];  // Array of cursors for each page
let pennylaneHasMore = true;
let pennylaneIsLoading = false;
let pennylaneCurrentPage = 0;  // Current page index (0-based)
const PENNYLANE_PAGE_SIZE = 20;

function initPennylaneDataTable() {
    pennylaneCustomersTable = $('#pennylaneCustomersTable').DataTable({
        pageLength: 20,
        ordering: false,  // Disable client-side sorting
        paging: true,  // Enable DataTables pagination
        info: true,  // Show DataTables info
        searching: true,  // Enable search across all data
        columns: [
            {
                data: 'id',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'name',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: 'emails',
                render: function(data) {
                    if (!data || data.length === 0) return 'N/A';
                    return data[0] || 'N/A';
                }
            },
            {
                data: 'reg_no',
                render: function(data) {
                    return data || 'N/A';
                }
            },
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    // Check if this Pennylane customer is linked
                    const linkedCustomer = Object.values(customerLinks).find(
                        link => link.pennylane_customer_id == row.id
                    );

                    if (linkedCustomer) {
                        return `
                            <span style="color: #27ae60; font-weight: 600;">✓ Linked to ${linkedCustomer.local_customer_name}</span>
                            <button class="btn" style="margin-left: 10px; padding: 6px 12px; background: #e74c3c;"
                                onclick="unlinkCustomer(${linkedCustomer.local_customer_id})">Unlink</button>
                        `;
                    } else {
                        return `<button class="btn" style="padding: 6px 12px;" onclick="showLinkModal('${row.id}', '${row.name.replace(/'/g, "\\'")}')">🔗 Link</button>`;
                    }
                }
            }
        ]
    });
}

async function loadPennylaneCustomers() {
    try {
        // Show loading overlay
        document.getElementById('pennylaneLoadingOverlay').style.display = 'flex';

        // First, load customer links
        await loadCustomerLinks();

        // Reset state
        pennylaneAllCustomers = [];

        // Load all customers from Pennylane in batches
        let cursor = null;
        let hasMore = true;
        let pageCount = 0;

        while (hasMore) {
            pageCount++;
            const url = cursor
                ? `/api/pennylane/customers/page?cursor=${encodeURIComponent(cursor)}`
                : '/api/pennylane/customers/page';

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to load Pennylane customers');
            }

            const data = await response.json();
            const customers = data.customers || [];

            // Add customers to our collection
            pennylaneAllCustomers.push(...customers);

            // Update loading message
            document.querySelector('#pennylaneLoadingOverlay p:first-of-type').textContent =
                `Loading Pennylane customers... (${pennylaneAllCustomers.length} loaded)`;

            hasMore = data.has_more;
            cursor = data.next_cursor;
        }

        // Load all customers into DataTable at once
        pennylaneCustomersTable.clear();
        pennylaneCustomersTable.rows.add(pennylaneAllCustomers);
        pennylaneCustomersTable.draw();

        showMessage(`Loaded ${pennylaneAllCustomers.length} customers from Pennylane.`, 'success');

        // Auto-match customers in background (don't wait for it)
        autoMatchCustomers().then(() => {
            // Refresh table after auto-matching
            pennylaneCustomersTable.draw();
        });

    } catch (error) {
        console.error('Error loading Pennylane customers:', error);
        showMessage('Error loading Pennylane customers: ' + error.message, 'error');
    } finally {
        // Hide loading overlay
        document.getElementById('pennylaneLoadingOverlay').style.display = 'none';
    }
}

async function loadCustomerLinks() {
    try {
        const response = await fetch('/api/pennylane/customer-links');
        if (response.ok) {
            const data = await response.json();
            // Store links in an object keyed by local customer ID
            customerLinks = {};
            data.links.forEach(link => {
                customerLinks[link.local_customer_id] = link;
            });
        }
    } catch (error) {
        console.error('Error loading customer links:', error);
    }
}

async function autoMatchCustomers() {
    try {
        const response = await fetch('/api/pennylane/auto-match-customers', {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            if (data.matched_count > 0) {
                showMessage(`Auto-matched ${data.matched_count} customer(s) based on SIREN.`, 'success');
                // Reload links
                await loadCustomerLinks();
            }
        }
    } catch (error) {
        console.error('Error auto-matching customers:', error);
    }
}

function showLinkModal(pennylaneCustomerId, pennylaneCustomerName) {
    // Store the Pennylane customer info for later use
    window.currentPennylaneCustomerId = pennylaneCustomerId;
    window.currentPennylaneCustomerName = pennylaneCustomerName;

    // Show modal
    document.getElementById('linkModalTitle').textContent = `Link "${pennylaneCustomerName}" to local customer`;
    document.getElementById('linkModal').classList.add('show');
    document.getElementById('localCustomerSearch').value = '';
    document.getElementById('localCustomerSearchResults').innerHTML = '';
    document.getElementById('localCustomerSearch').focus();
}

function closeLinkModal() {
    document.getElementById('linkModal').classList.remove('show');
}

async function searchLocalCustomers() {
    const query = document.getElementById('localCustomerSearch').value;

    if (query.length < 2) {
        document.getElementById('localCustomerSearchResults').innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);

        if (!response.ok) {
            throw new Error('Failed to search customers');
        }

        const customers = await response.json();
        const resultsDiv = document.getElementById('localCustomerSearchResults');

        if (customers.length === 0) {
            resultsDiv.innerHTML = '<div style="padding: 10px; color: #999;">No customers found</div>';
            return;
        }

        resultsDiv.innerHTML = customers.map(customer => `
            <div class="search-result-item" onclick="linkCustomers(${customer.id}, '${customer.company_name.replace(/'/g, "\\'")}')">
                <strong>${customer.company_name}</strong>
                ${customer.national_identifier ? `<br><small>SIREN: ${customer.national_identifier}</small>` : ''}
            </div>
        `).join('');

    } catch (error) {
        console.error('Error searching customers:', error);
    }
}

async function linkCustomers(localCustomerId, localCustomerName) {
    try {
        const response = await fetch('/api/pennylane/link-customer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                local_customer_id: localCustomerId,
                pennylane_customer_id: window.currentPennylaneCustomerId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to link customers');
        }

        showMessage(`Successfully linked "${window.currentPennylaneCustomerName}" to "${localCustomerName}"`, 'success');

        // Reload links and refresh table
        await loadCustomerLinks();
        pennylaneCustomersTable.draw();

        // Close modal
        closeLinkModal();

    } catch (error) {
        console.error('Error linking customers:', error);
        showMessage('Error linking customers: ' + error.message, 'error');
    }
}

async function unlinkCustomer(localCustomerId) {
    if (!confirm('Are you sure you want to unlink this customer?')) {
        return;
    }

    try {
        const response = await fetch(`/api/pennylane/link-customer/${localCustomerId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to unlink customer');
        }

        showMessage('Customer unlinked successfully', 'success');

        // Reload links and refresh table
        await loadCustomerLinks();
        pennylaneCustomersTable.draw();

    } catch (error) {
        console.error('Error unlinking customer:', error);
        showMessage('Error unlinking customer: ' + error.message, 'error');
    }
}
