// State management
let productsTable = null;
let editingProductId = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initDataTable();
    loadProducts();
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    document.getElementById('productForm').addEventListener('submit', handleFormSubmit);

    // Show/hide subtype based on product type
    document.getElementById('productType').addEventListener('change', toggleSubtypeField);
}

function toggleSubtypeField() {
    const productType = document.getElementById('productType').value;
    const subtypeGroup = document.getElementById('subtypeGroup');
    const subtypeSelect = document.getElementById('subtype');

    if (productType === 'Appliance') {
        subtypeGroup.style.display = 'block';
        subtypeSelect.required = true;
    } else {
        subtypeGroup.style.display = 'none';
        subtypeSelect.required = false;
        subtypeSelect.value = '';
    }
}

function initDataTable() {
    productsTable = $('#productsTable').DataTable({
        order: [[0, 'asc']], // Sort by ID ascending
        columns: [
            { data: 'id' },
            {
                data: 'product_type',
                render: function(data) {
                    return data || '-';
                }
            },
            {
                data: 'volume_tb',
                render: function(data) {
                    return data ? data.toFixed(2) : '-';
                }
            },
            {
                data: 'subtype',
                render: function(data) {
                    return data || '-';
                }
            },
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    return `
                        <button class="btn" onclick="editProduct(${row.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deleteProduct(${row.id})">Delete</button>
                    `;
                }
            }
        ]
    });
}

function showAddForm() {
    editingProductId = null;
    document.getElementById('formTitle').textContent = 'Add Product';
    document.getElementById('productForm').reset();
    document.getElementById('productId').value = '';
    document.getElementById('formSection').classList.add('active');

    // Hide subtype initially
    toggleSubtypeField();

    // Scroll to form
    document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });
}

async function editProduct(productId) {
    try {
        const response = await fetch(`/api/products/${productId}`);

        if (!response.ok) {
            throw new Error('Failed to fetch product');
        }

        const product = await response.json();

        // Populate form
        editingProductId = productId;
        document.getElementById('formTitle').textContent = 'Edit Product';
        document.getElementById('productId').value = product.id;
        document.getElementById('productType').value = product.product_type || '';
        document.getElementById('volumeTb').value = product.volume_tb || '';

        // Toggle subtype visibility and set value
        toggleSubtypeField();
        document.getElementById('subtype').value = product.subtype || '';

        document.getElementById('formSection').classList.add('active');

        // Scroll to form
        document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error fetching product:', error);
        showMessage('Error loading product.', 'error');
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();

    const volumeValue = document.getElementById('volumeTb').value;
    const productData = {
        product_type: document.getElementById('productType').value,
        volume_tb: volumeValue ? parseFloat(volumeValue) : null,
        subtype: document.getElementById('subtype').value || null
    };

    try {
        let response;

        if (editingProductId) {
            // Update existing product
            response = await fetch(`/api/products/${editingProductId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            });
        } else {
            // Create new product
            response = await fetch('/api/products', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save product');
        }

        showMessage(`Product ${editingProductId ? 'updated' : 'created'} successfully!`, 'success');

        // Reset form
        cancelForm();

        // Reload products list
        await loadProducts();

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        console.error('Error saving product:', error);
        showMessage(error.message || 'Error saving product. Please try again.', 'error');
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products');

        if (!response.ok) {
            throw new Error('Failed to load products');
        }

        const products = await response.json();

        // Update DataTable
        productsTable.clear();
        productsTable.rows.add(products);
        productsTable.draw();

    } catch (error) {
        console.error('Error loading products:', error);
        showMessage('Error loading products.', 'error');
    }
}

async function deleteProduct(productId) {
    if (!confirm('Are you sure you want to delete this product?')) {
        return;
    }

    try {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete product');
        }

        showMessage('Product deleted successfully.', 'success');
        await loadProducts();

    } catch (error) {
        console.error('Error deleting product:', error);
        showMessage(error.message || 'Error deleting product.', 'error');
    }
}

function cancelForm() {
    editingProductId = null;
    document.getElementById('productForm').reset();
    document.getElementById('formSection').classList.remove('active');
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
