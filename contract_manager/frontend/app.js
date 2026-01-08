// State management
let autocompleteTimeout = null;

// Review mode state
let reviewMode = false;
let draftContracts = [];
let currentReviewIndex = 0;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    loadContractsForReplacement();
    setupEventListeners();

    // Check if review mode should be started from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('review') === 'true') {
        startReviewMode();
    } else if (urlParams.get('edit')) {
        // Load contract for editing
        const contractId = urlParams.get('edit');
        loadContractForEdit(contractId);
    }
});

function setupEventListeners() {
    // File upload
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);

    // Form submission
    document.getElementById('contractForm').addEventListener('submit', handleFormSubmit);

    // Auto-calculate ARR when value or duration changes
    document.getElementById('value').addEventListener('input', calculateARR);
    document.getElementById('duration').addEventListener('input', calculateARR);

    // Autocomplete for company names
    document.getElementById('clientName').addEventListener('input', handleAutocomplete);
    document.getElementById('clientName').addEventListener('blur', () => {
        setTimeout(() => {
            document.getElementById('autocompleteResults').classList.remove('show');
        }, 200);
    });

    document.getElementById('resellerName').addEventListener('input', (e) => handleAutocompleteSecondary(e, 'reseller'));
    document.getElementById('resellerName').addEventListener('blur', () => {
        setTimeout(() => {
            document.getElementById('resellerAutocompleteResults').classList.remove('show');
        }, 200);
    });

    document.getElementById('endUserName').addEventListener('input', (e) => handleAutocompleteSecondary(e, 'endUser'));
    document.getElementById('endUserName').addEventListener('blur', () => {
        setTimeout(() => {
            document.getElementById('endUserAutocompleteResults').classList.remove('show');
        }, 200);
    });

    // Quick product form - toggle subtype visibility
    document.getElementById('quickProductType').addEventListener('change', toggleQuickProductSubtype);

    // Drag and drop
    const uploadSection = document.querySelector('.upload-section');

    uploadSection.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadSection.classList.add('dragover');
    });

    uploadSection.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadSection.classList.remove('dragover');
    });

    uploadSection.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadSection.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;

        if (files.length === 1) {
            handleFileUploadDirect(files[0]);
        } else {
            handleBatchUpload(files);
        }
    });
}


async function handleAutocomplete(event) {
    const query = event.target.value;

    // Clear previous timeout
    if (autocompleteTimeout) {
        clearTimeout(autocompleteTimeout);
    }

    if (query.length < 2) {
        document.getElementById('autocompleteResults').classList.remove('show');
        return;
    }

    // Debounce the search
    autocompleteTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error('Failed to search customers');
            }

            const customers = await response.json();
            displayAutocompleteResults(customers);

        } catch (error) {
            console.error('Error searching customers:', error);
        }
    }, 300);
}

function displayAutocompleteResults(customers) {
    const resultsDiv = document.getElementById('autocompleteResults');

    if (customers.length === 0) {
        resultsDiv.classList.remove('show');
        return;
    }

    resultsDiv.innerHTML = customers.map(customer => `
        <div class="autocomplete-item" onclick="selectCustomer(${customer.id})">
            ${customer.company_name}
        </div>
    `).join('');

    resultsDiv.classList.add('show');
}

async function selectCustomer(customerId) {
    try {
        const response = await fetch(`/api/customers/${customerId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch customer');
        }

        const customer = await response.json();

        // Fill in customer data
        document.getElementById('clientName').value = customer.company_name;
        document.getElementById('clientIdentifier').value = customer.national_identifier || '';
        document.getElementById('clientCategory').value = customer.category || 'end-user';
        document.getElementById('matchedCustomerId').value = customer.id;

        // Update visibility of reseller/end-user sections
        toggleCustomerHierarchy();

        // Hide autocomplete
        document.getElementById('autocompleteResults').classList.remove('show');

    } catch (error) {
        console.error('Error fetching customer:', error);
    }
}

// Toggle visibility of reseller/end-user sections based on primary customer category
function toggleCustomerHierarchy() {
    const category = document.getElementById('clientCategory').value;
    const resellerSection = document.getElementById('resellerSection');
    const endUserSection = document.getElementById('endUserSection');

    if (category === 'distributor') {
        // Distributor can have reseller and/or end-user
        resellerSection.style.display = 'block';
        endUserSection.style.display = 'block';
    } else if (category === 'reseller') {
        // Reseller can only have end-user
        resellerSection.style.display = 'none';
        endUserSection.style.display = 'block';
        // Clear reseller data
        document.getElementById('resellerName').value = '';
        document.getElementById('resellerIdentifier').value = '';
        document.getElementById('matchedResellerId').value = '';
    } else {
        // End-user has no additional customers
        resellerSection.style.display = 'none';
        endUserSection.style.display = 'none';
        // Clear both
        document.getElementById('resellerName').value = '';
        document.getElementById('resellerIdentifier').value = '';
        document.getElementById('matchedResellerId').value = '';
        document.getElementById('endUserName').value = '';
        document.getElementById('endUserIdentifier').value = '';
        document.getElementById('matchedEndUserId').value = '';
    }
}

// Autocomplete for reseller and end-user
async function handleAutocompleteSecondary(event, type) {
    const query = event.target.value;
    const resultsId = type === 'reseller' ? 'resellerAutocompleteResults' : 'endUserAutocompleteResults';

    if (query.length < 2) {
        document.getElementById(resultsId).classList.remove('show');
        return;
    }

    try {
        const response = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Failed to search customers');
        }

        const customers = await response.json();
        displayAutocompleteResultsSecondary(customers, type);

    } catch (error) {
        console.error('Error searching customers:', error);
    }
}

function displayAutocompleteResultsSecondary(customers, type) {
    const resultsId = type === 'reseller' ? 'resellerAutocompleteResults' : 'endUserAutocompleteResults';
    const resultsDiv = document.getElementById(resultsId);

    if (customers.length === 0) {
        resultsDiv.classList.remove('show');
        return;
    }

    resultsDiv.innerHTML = customers.map(customer => `
        <div class="autocomplete-item" onclick="selectSecondaryCustomer(${customer.id}, '${type}')">
            ${customer.company_name}
        </div>
    `).join('');

    resultsDiv.classList.add('show');
}

async function selectSecondaryCustomer(customerId, type) {
    try {
        const response = await fetch(`/api/customers/${customerId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch customer');
        }

        const customer = await response.json();

        if (type === 'reseller') {
            document.getElementById('resellerName').value = customer.company_name;
            document.getElementById('resellerIdentifier').value = customer.national_identifier || '';
            document.getElementById('matchedResellerId').value = customer.id;
            document.getElementById('resellerAutocompleteResults').classList.remove('show');
        } else {
            document.getElementById('endUserName').value = customer.company_name;
            document.getElementById('endUserIdentifier').value = customer.national_identifier || '';
            document.getElementById('matchedEndUserId').value = customer.id;
            document.getElementById('endUserAutocompleteResults').classList.remove('show');
        }

    } catch (error) {
        console.error('Error fetching customer:', error);
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        if (!response.ok) {
            throw new Error('Failed to load products');
        }

        const products = await response.json();

        // Store globally for use in multiple product rows
        window.allProducts = products;

        // Populate all product selects
        document.querySelectorAll('.product-select').forEach(select => {
            populateProductSelect(select);
        });

    } catch (error) {
        console.error('Error loading products:', error);
    }
}

async function loadContractsForReplacement() {
    try {
        const response = await fetch('/api/contracts?limit=1000');
        if (!response.ok) {
            throw new Error('Failed to load contracts');
        }

        const contracts = await response.json();

        // Store globally for replacement contract selector
        window.allContracts = contracts;

        // Populate replacement contract select
        populateReplacementContractSelect();

    } catch (error) {
        console.error('Error loading contracts:', error);
    }
}

function populateReplacementContractSelect() {
    const select = document.getElementById('replacementContract');
    const currentContractId = document.getElementById('contractId').value;
    const currentCustomerId = document.getElementById('matchedCustomerId').value;
    const contracts = window.allContracts || [];

    select.innerHTML = '<option value="">Select replacement contract...</option>';

    // Filter contracts to only show those with the same customer
    const filteredContracts = contracts.filter(contract => {
        // Don't show the current contract in the list
        if (currentContractId && parseInt(currentContractId) === contract.id) {
            return false;
        }
        // Only show contracts with the same customer
        if (currentCustomerId && contract.customer_id === parseInt(currentCustomerId)) {
            return true;
        }
        return false;
    });

    // Sort contracts by ID descending (most recent first)
    const sortedContracts = [...filteredContracts].sort((a, b) => b.id - a.id);

    sortedContracts.forEach(contract => {
        const option = document.createElement('option');
        option.value = contract.id;

        // Display: ID - Date - Status
        let text = `#${contract.id}`;
        if (contract.contract_date) {
            text += ` - ${contract.contract_date}`;
        }
        text += ` (${contract.status})`;

        option.textContent = text;
        select.appendChild(option);
    });

    // Show message if no contracts available
    if (sortedContracts.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No other contracts for this customer';
        option.disabled = true;
        select.appendChild(option);
    }
}

function toggleReplacementContract() {
    const status = document.getElementById('contractStatus').value;
    const replacementSection = document.getElementById('replacementContractSection');
    const replacementSelect = document.getElementById('replacementContract');

    if (status === 'replaced') {
        replacementSection.style.display = 'block';
        replacementSelect.required = true;
    } else {
        replacementSection.style.display = 'none';
        replacementSelect.required = false;
        replacementSelect.value = '';
    }
}

async function handleFileUpload(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    if (files.length === 1) {
        // Single file mode
        await handleFileUploadDirect(files[0]);
    } else {
        // Batch mode
        await handleBatchUpload(files);
    }
}

async function handleBatchUpload(files) {
    // Show file names
    document.getElementById('fileName').textContent = `Selected: ${files.length} files`;

    // Show progress list
    const progressContainer = document.getElementById('bulkUploadProgress');
    const progressList = document.getElementById('uploadProgressList');
    progressContainer.style.display = 'block';
    progressList.innerHTML = '';

    // Create progress items for each file
    const progressItems = {};
    for (let file of files) {
        const itemId = `progress-${file.name.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const item = document.createElement('div');
        item.id = itemId;
        item.className = 'upload-progress-item';
        item.innerHTML = `
            <div class="upload-progress-icon">⏳</div>
            <div class="upload-progress-filename">${file.name}</div>
            <div class="upload-progress-status">Waiting...</div>
        `;
        progressList.appendChild(item);
        progressItems[file.name] = item;
    }

    // Process files one by one
    let contractsCreated = 0;
    let duplicatesIgnored = 0;
    const duplicatesList = [];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const item = progressItems[file.name];

        // Update status to processing
        item.className = 'upload-progress-item processing';
        item.querySelector('.upload-progress-icon').textContent = '🔄';
        item.querySelector('.upload-progress-status').textContent = 'Processing...';

        try {
            const formData = new FormData();
            formData.append('files', file);

            const response = await fetch('/api/upload-bulk', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Failed to upload file');
            }

            const result = await response.json();

            // Check if it was a duplicate
            if (result.duplicates && result.duplicates.length > 0) {
                duplicatesIgnored++;
                duplicatesList.push(result.duplicates[0]);
                item.className = 'upload-progress-item duplicate';
                item.querySelector('.upload-progress-icon').textContent = '⚠️';
                item.querySelector('.upload-progress-status').textContent = `Duplicate (ID: ${result.duplicates[0].existing_contract_id})`;
            } else if (result.contracts_created > 0) {
                contractsCreated++;
                item.className = 'upload-progress-item success';
                item.querySelector('.upload-progress-icon').textContent = '✅';
                item.querySelector('.upload-progress-status').textContent = `Created (ID: ${result.contract_ids[0]})`;
            } else {
                throw new Error('No contract created');
            }

        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            item.className = 'upload-progress-item error';
            item.querySelector('.upload-progress-icon').textContent = '❌';
            item.querySelector('.upload-progress-status').textContent = 'Failed';
        }

        // Small delay for visual feedback
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    // Build final message
    let message = `✅ Upload complete! ${contractsCreated} draft contract(s) created!`;

    if (duplicatesIgnored > 0) {
        message += ` ${duplicatesIgnored} duplicate(s) ignored.`;
    }

    message += ' Click "Review Drafts" to review and validate them.';

    showMessage(message, 'success');

    // Update progress header to show completion
    const progressHeader = progressContainer.querySelector('h3');
    progressHeader.textContent = `Upload Complete - ${contractsCreated} Created, ${duplicatesIgnored} Duplicates`;
    progressHeader.style.color = '#2ecc71';
}

function showBatchProgress() {
    const batchProgress = document.getElementById('batchProgress');
    batchProgress.style.display = 'block';
    updateBatchProgress();
}

function hideBatchProgress() {
    const batchProgress = document.getElementById('batchProgress');
    batchProgress.style.display = 'none';
}

function updateBatchProgress() {
    const total = batchFiles.length;
    const current = currentBatchIndex + 1;
    const percentage = ((currentBatchIndex) / total) * 100;

    document.getElementById('progressText').textContent = `${current} of ${total}`;
    document.getElementById('progressBar').style.width = `${percentage}%`;
    document.getElementById('currentFile').textContent = `Current: ${batchFiles[currentBatchIndex].name}`;

    // Update navigation buttons
    document.getElementById('prevBtn').disabled = currentBatchIndex === 0;
    document.getElementById('nextBtn').disabled = currentBatchIndex === total - 1;
}

function loadBatchItem(index) {
    currentBatchIndex = index;
    const data = batchParsedData[index];

    console.log(`Loading batch item ${index}, filename:`, data.filename);

    // Reset form first
    document.getElementById('contractForm').reset();
    document.getElementById('autocompleteResults').classList.remove('show');

    // Populate form with new data
    populateForm(data);

    // Show PDF
    showPDFViewer(data.filename);

    // Show form
    document.getElementById('formSection').classList.add('active');

    // Update progress
    updateBatchProgress();

    // Scroll to form
    document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });
}

function navigateToPrevious() {
    if (currentBatchIndex > 0) {
        loadBatchItem(currentBatchIndex - 1);
    }
}

function navigateToNext() {
    if (currentBatchIndex < batchFiles.length - 1) {
        loadBatchItem(currentBatchIndex + 1);
    }
}

function skipCurrent() {
    if (currentBatchIndex < batchFiles.length - 1) {
        navigateToNext();
    } else {
        // Last item - finish batch
        finishBatch();
    }
}

async function handleFileUploadDirect(file) {
    // Show file name
    document.getElementById('fileName').textContent = `Selected: ${file.name}`;

    // Show spinner
    document.getElementById('uploadSpinner').innerHTML = '<div class="spinner"></div> Parsing PDF...';

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to upload file');
        }

        const data = await response.json();

        // Hide spinner
        document.getElementById('uploadSpinner').innerHTML = '';

        // Check if duplicate
        if (data.is_duplicate) {
            const messageEl = document.getElementById('message');
            messageEl.innerHTML = `<strong>Duplicate PDF detected!</strong><br>${data.duplicate_reason}<br>Existing contract ID: ${data.existing_contract_id}<br><br>The file was not uploaded.`;
            messageEl.className = 'message error show';

            setTimeout(() => {
                messageEl.classList.remove('show');
            }, 8000);

            // Reset file input
            document.getElementById('fileInput').value = '';
            document.getElementById('fileName').textContent = '';
            return;
        }

        // Populate form with extracted data
        populateForm(data);

        // Show PDF in viewer
        showPDFViewer(data.filename);

        // Show form
        document.getElementById('formSection').classList.add('active');

        let message = 'PDF parsed successfully. Please review and correct the information below.';
        if (data.matched_customer_id) {
            message += ` Customer "${data.matched_customer_name}" matched!`;
        }
        showMessage(message, 'success');

        // Scroll to form
        document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error uploading file:', error);
        showMessage('Error parsing PDF. Please try again or enter information manually.', 'error');
        document.getElementById('uploadSpinner').innerHTML = '';

        // Show empty form for manual entry
        document.getElementById('formSection').classList.add('active');
        document.getElementById('originalFilename').value = file.name;
    }
}

function populateForm(data) {
    document.getElementById('clientName').value = data.client_company_name || '';
    document.getElementById('clientIdentifier').value = data.client_national_identifier || '';
    document.getElementById('clientCategory').value = 'end-user';
    document.getElementById('contractDate').value = data.contract_date || '';
    document.getElementById('product').value = data.product || '';
    document.getElementById('duration').value = data.contract_duration || '';
    document.getElementById('value').value = data.contract_value || '';
    document.getElementById('arr').value = data.arr || '';
    document.getElementById('originalFilename').value = data.filename || '';
    document.getElementById('matchedCustomerId').value = data.matched_customer_id || '';
    document.getElementById('contractStatus').value = 'active'; // Default to active for new contracts

    // Calculate ARR if not provided
    if (!data.arr) {
        calculateARR();
    }
}

function calculateARR() {
    const value = parseFloat(document.getElementById('value').value);
    const durationMonths = parseInt(document.getElementById('duration').value);

    if (value && durationMonths && durationMonths > 0) {
        // ARR = value / (duration in months / 12)
        const arr = (value / (durationMonths / 12)).toFixed(2);
        document.getElementById('arr').value = arr;
    } else {
        document.getElementById('arr').value = '';
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();

    // Check form validity
    const form = document.getElementById('contractForm');
    if (!form.checkValidity()) {
        // Find invalid fields
        const invalidFields = form.querySelectorAll(':invalid');
        console.log('Invalid fields:', invalidFields);
        invalidFields.forEach(field => {
            console.log('Invalid field:', field.name || field.className, field.validationMessage);
        });
        form.reportValidity();
        return;
    }

    const contractId = document.getElementById('contractId').value;

    // Collect products from all product rows
    const productRows = document.querySelectorAll('.product-item');
    const products = [];
    productRows.forEach(row => {
        const productId = row.querySelector('.product-select').value;
        const quantity = parseInt(row.querySelector('.product-quantity').value);
        if (productId) {
            products.push({ product_id: parseInt(productId), quantity });
        }
    });

    if (products.length === 0) {
        showMessage('Please select at least one product', 'error');
        return;
    }

    // Check if we're updating an existing contract (has contractId)
    if (contractId) {
        try {
            // First, update or create the customer
            const customerId = document.getElementById('matchedCustomerId').value;
            const customerData = {
                company_name: document.getElementById('clientName').value,
                national_identifier: document.getElementById('clientIdentifier').value,
                category: document.getElementById('clientCategory').value
            };

            let finalCustomerId;
            if (customerId) {
                // Update existing customer
                const customerResponse = await fetch(`/api/customers/${customerId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(customerData)
                });

                if (!customerResponse.ok) {
                    throw new Error('Failed to update customer');
                }

                finalCustomerId = parseInt(customerId);
            } else {
                // Create new customer
                const customerResponse = await fetch('/api/customers', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(customerData)
                });

                if (!customerResponse.ok) {
                    throw new Error('Failed to create customer');
                }

                const newCustomer = await customerResponse.json();
                finalCustomerId = newCustomer.id;
            }

            // Handle reseller (if applicable)
            let resellerId = null;
            const resellerName = document.getElementById('resellerName').value;
            if (resellerName) {
                const resellerData = {
                    company_name: resellerName,
                    national_identifier: document.getElementById('resellerIdentifier').value || null,
                    category: 'reseller'
                };

                const existingResellerId = document.getElementById('matchedResellerId').value;
                if (existingResellerId) {
                    await fetch(`/api/customers/${existingResellerId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(resellerData)
                    });
                    resellerId = parseInt(existingResellerId);
                } else {
                    const resellerResponse = await fetch('/api/customers', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(resellerData)
                    });
                    const newReseller = await resellerResponse.json();
                    resellerId = newReseller.id;
                }
            }

            // Handle end-user (if applicable)
            let endUserId = null;
            const endUserName = document.getElementById('endUserName').value;
            if (endUserName) {
                const endUserData = {
                    company_name: endUserName,
                    national_identifier: document.getElementById('endUserIdentifier').value || null,
                    category: 'end-user'
                };

                const existingEndUserId = document.getElementById('matchedEndUserId').value;
                if (existingEndUserId) {
                    await fetch(`/api/customers/${existingEndUserId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(endUserData)
                    });
                    endUserId = parseInt(existingEndUserId);
                } else {
                    const endUserResponse = await fetch('/api/customers', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(endUserData)
                    });
                    const newEndUser = await endUserResponse.json();
                    endUserId = newEndUser.id;
                }
            }

            // Get status and replacement contract
            const status = document.getElementById('contractStatus').value;
            const replacedByContractId = status === 'replaced' ? document.getElementById('replacementContract').value : null;

            // Now update the contract
            const updateData = {
                customer_id: finalCustomerId,
                reseller_id: resellerId,
                end_user_id: endUserId,
                contract_date: document.getElementById('contractDate').value || null,
                contract_duration: parseInt(document.getElementById('duration').value) || null,
                contract_value: parseFloat(document.getElementById('value').value) || null,
                arr: parseFloat(document.getElementById('arr').value) || null,
                status: status,
                replaced_by_contract_id: replacedByContractId ? parseInt(replacedByContractId) : null,
                products: products
            };

            const response = await fetch(`/api/contracts/${contractId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });

            if (!response.ok) {
                throw new Error('Failed to update contract');
            }

            showMessage('Contract updated successfully!', 'success');

            if (reviewMode) {
                // Remove from draft list
                draftContracts.splice(currentReviewIndex, 1);

                // Load next or finish review
                setTimeout(() => {
                    if (draftContracts.length === 0) {
                        showMessage('All draft contracts reviewed!', 'success');
                        exitReviewMode();
                    } else {
                        // Stay at same index (since we removed current item)
                        if (currentReviewIndex >= draftContracts.length) {
                            currentReviewIndex = draftContracts.length - 1;
                        }
                        loadDraftContract(currentReviewIndex);
                    }
                }, 500);
            } else {
                // Not in review mode - redirect to contracts list
                setTimeout(() => {
                    window.location.href = '/contracts';
                }, 1000);
            }

        } catch (error) {
            console.error('Error updating contract:', error);
            showMessage('Error updating contract. Please try again.', 'error');
        }

    } else {
        // Create new contract
        const status = document.getElementById('contractStatus').value;
        const contractData = {
            customer_name: document.getElementById('clientName').value,
            customer_national_identifier: document.getElementById('clientIdentifier').value,
            customer_category: document.getElementById('clientCategory').value,
            contract_date: document.getElementById('contractDate').value,
            contract_duration: parseInt(document.getElementById('duration').value),
            contract_value: parseFloat(document.getElementById('value').value),
            arr: parseFloat(document.getElementById('arr').value),
            original_filename: document.getElementById('originalFilename').value,
            status: status || 'active',
            products: products
        };

        try {
            const response = await fetch('/api/contracts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(contractData)
            });

            if (!response.ok) {
                throw new Error('Failed to save contract');
            }

            showMessage('Contract saved successfully!', 'success');

            // Single file mode - reset form
            resetForm();
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });

        } catch (error) {
            console.error('Error saving contract:', error);
            showMessage('Error saving contract. Please try again.', 'error');
        }
    }
}


function cancelForm() {
    resetForm();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function resetForm() {
    document.getElementById('contractForm').reset();
    document.getElementById('formSection').classList.remove('active');
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('matchedCustomerId').value = '';
    document.getElementById('autocompleteResults').classList.remove('show');
    hidePDFViewer();

    // Reset batch mode
    if (batchMode) {
        finishBatch();
    }
}

function finishBatch() {
    batchMode = false;
    batchFiles = [];
    currentBatchIndex = 0;
    batchParsedData = [];

    hideBatchProgress();
    hidePDFViewer();
    document.getElementById('formSection').classList.remove('active');
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';

    showMessage('Batch processing complete! All contracts have been processed.', 'success');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showPDFViewer(filename) {
    const pdfViewer = document.getElementById('pdfViewer');
    const pdfFrame = document.getElementById('pdfFrame');

    // Set the PDF URL and load it directly
    const pdfUrl = `/api/files/${encodeURIComponent(filename)}`;
    pdfFrame.src = pdfUrl;
    pdfViewer.style.display = 'block';
}

function hidePDFViewer() {
    const pdfViewer = document.getElementById('pdfViewer');
    const pdfFrame = document.getElementById('pdfFrame');

    // Hide the viewer
    pdfViewer.style.display = 'none';

    // Clear the iframe src
    pdfFrame.src = '';
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

// Review Mode Functions
async function startReviewMode() {
    try {
        // Ensure products are loaded first
        if (!window.allProducts) {
            await loadProducts();
        }

        const response = await fetch('/api/contracts/draft');

        if (!response.ok) {
            throw new Error('Failed to load draft contracts');
        }

        draftContracts = await response.json();

        if (draftContracts.length === 0) {
            showMessage('No draft contracts to review!', 'error');
            return;
        }

        reviewMode = true;
        currentReviewIndex = 0;

        // Hide upload section
        document.querySelector('.upload-section').style.display = 'none';

        // Show review progress
        document.getElementById('reviewProgress').style.display = 'block';

        // Load first draft contract
        loadDraftContract(0);

        showMessage(`Review mode started. ${draftContracts.length} draft contracts to review.`, 'success');

    } catch (error) {
        console.error('Error loading draft contracts:', error);
        showMessage('Error loading draft contracts.', 'error');
    }
}

async function loadContractForEdit(contractId) {
    try {
        const response = await fetch(`/api/contracts/${contractId}`);
        if (!response.ok) {
            throw new Error('Failed to load contract');
        }

        const contract = await response.json();

        // Update contract ID display
        document.getElementById('contractIdDisplay').textContent = `(Editing ID: ${contract.id})`;

        // Reset and populate form
        document.getElementById('contractForm').reset();
        document.getElementById('contractId').value = contract.id;
        document.getElementById('originalFilename').value = contract.original_filename || '';

        // Refresh replacement contract select (to exclude current contract)
        populateReplacementContractSelect();

        // Populate customer data
        if (contract.customer) {
            document.getElementById('clientName').value = contract.customer.company_name || '';
            document.getElementById('clientIdentifier').value = contract.customer.national_identifier || '';
            document.getElementById('clientCategory').value = contract.customer.category || 'end-user';
            document.getElementById('matchedCustomerId').value = contract.customer_id || '';
        }

        // Toggle and populate reseller/end-user sections
        toggleCustomerHierarchy();

        // Populate reseller data if exists
        if (contract.reseller) {
            document.getElementById('resellerName').value = contract.reseller.company_name || '';
            document.getElementById('resellerIdentifier').value = contract.reseller.national_identifier || '';
            document.getElementById('matchedResellerId').value = contract.reseller_id || '';
        }

        // Populate end-user data if exists
        if (contract.end_user) {
            document.getElementById('endUserName').value = contract.end_user.company_name || '';
            document.getElementById('endUserIdentifier').value = contract.end_user.national_identifier || '';
            document.getElementById('matchedEndUserId').value = contract.end_user_id || '';
        }

        // Populate products data
        const productsContainer = document.getElementById('productsContainer');
        productsContainer.innerHTML = ''; // Clear existing product rows

        if (contract.contract_products && contract.contract_products.length > 0) {
            // Add rows for each product
            contract.contract_products.forEach((cp, index) => {
                addProductRow();
                const rows = document.querySelectorAll('.product-item');
                const newRow = rows[rows.length - 1];
                newRow.querySelector('.product-select').value = cp.product_id;
                newRow.querySelector('.product-quantity').value = cp.quantity;

                // Show remove button if not first row
                if (index > 0) {
                    newRow.querySelector('.btn-icon-remove').style.visibility = 'visible';
                }
            });
        } else {
            // No products, add one empty row
            addProductRow();
        }

        // Populate contract data
        if (contract.contract_date) {
            document.getElementById('contractDate').value = contract.contract_date;
        }
        if (contract.contract_duration) {
            document.getElementById('duration').value = contract.contract_duration;
        }
        if (contract.contract_value) {
            document.getElementById('value').value = contract.contract_value;
        }
        if (contract.arr) {
            document.getElementById('arr').value = contract.arr;
        }

        // Populate status
        if (contract.status) {
            document.getElementById('contractStatus').value = contract.status;
        }

        // Populate replacement contract if status is replaced
        if (contract.replaced_by_contract_id) {
            document.getElementById('replacementContract').value = contract.replaced_by_contract_id;
        }

        // Toggle replacement contract section based on status
        toggleReplacementContract();

        // Show PDF if available
        if (contract.original_filename) {
            showPDFViewer(contract.original_filename);
        }

        // Show form
        document.getElementById('formSection').classList.add('active');

        // Scroll to form
        document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error loading contract for edit:', error);
        showMessage('Error loading contract for editing.', 'error');
    }
}

function loadDraftContract(index) {
    currentReviewIndex = index;
    const contract = draftContracts[index];

    console.log('Loading draft contract:', contract);

    // Update contract ID display
    document.getElementById('contractIdDisplay').textContent = `(ID: ${contract.id})`;
    document.getElementById('currentContractId').textContent = contract.id;
    document.getElementById('currentContractFile').textContent = contract.original_filename;

    // Reset and populate form
    document.getElementById('contractForm').reset();
    document.getElementById('contractId').value = contract.id;
    document.getElementById('originalFilename').value = contract.original_filename;

    // Populate customer data
    if (contract.customer) {
        document.getElementById('clientName').value = contract.customer.company_name || '';
        document.getElementById('clientIdentifier').value = contract.customer.national_identifier || '';
        document.getElementById('clientCategory').value = contract.customer.category || 'end-user';
        document.getElementById('matchedCustomerId').value = contract.customer_id || '';
    }

    // Populate products data
    const productsContainer = document.getElementById('productsContainer');
    productsContainer.innerHTML = ''; // Clear existing product rows

    if (contract.contract_products && contract.contract_products.length > 0) {
        // Add rows for each product
        contract.contract_products.forEach((cp, index) => {
            addProductRow();
            const rows = document.querySelectorAll('.product-item');
            const newRow = rows[rows.length - 1];
            newRow.querySelector('.product-select').value = cp.product_id;
            newRow.querySelector('.product-quantity').value = cp.quantity;

            // Show remove button if not first row
            if (index > 0) {
                newRow.querySelector('.btn-icon-remove').style.visibility = 'visible';
            }
        });
    } else {
        // No products, add one empty row
        addProductRow();
    }

    // Populate contract data
    if (contract.contract_date) {
        document.getElementById('contractDate').value = contract.contract_date;
    }
    if (contract.contract_duration) {
        document.getElementById('duration').value = contract.contract_duration;
    }
    if (contract.contract_value) {
        document.getElementById('value').value = contract.contract_value;
    }
    if (contract.arr) {
        document.getElementById('arr').value = contract.arr;
    }

    // Populate status
    if (contract.status) {
        document.getElementById('contractStatus').value = contract.status;
    } else {
        document.getElementById('contractStatus').value = 'draft';
    }

    // Toggle replacement contract section based on status
    toggleReplacementContract();

    // Show PDF
    console.log('Loading PDF for contract:', contract);
    if (contract.original_filename) {
        showPDFViewer(contract.original_filename);
    } else {
        console.warn('No filename found for contract', contract);
        hidePDFViewer();
    }

    // Show form
    document.getElementById('formSection').classList.add('active');

    // Update progress
    updateReviewProgress();

    // Scroll to form
    document.getElementById('formSection').scrollIntoView({ behavior: 'smooth' });
}

function updateReviewProgress() {
    const total = draftContracts.length;
    const current = currentReviewIndex + 1;

    document.getElementById('reviewProgressText').textContent = `${current} of ${total}`;

    const percentage = (current / total) * 100;
    document.getElementById('reviewProgressBar').style.width = `${percentage}%`;

    // Update navigation buttons
    document.getElementById('reviewPrevBtn').disabled = currentReviewIndex === 0;
    document.getElementById('reviewNextBtn').disabled = currentReviewIndex === total - 1;
}

function reviewNavigatePrevious() {
    if (currentReviewIndex > 0) {
        loadDraftContract(currentReviewIndex - 1);
    }
}

function reviewNavigateNext() {
    if (currentReviewIndex < draftContracts.length - 1) {
        loadDraftContract(currentReviewIndex + 1);
    }
}

function exitReviewMode() {
    reviewMode = false;
    draftContracts = [];
    currentReviewIndex = 0;

    // Hide review progress
    document.getElementById('reviewProgress').style.display = 'none';

    // Show upload section
    document.querySelector('.upload-section').style.display = 'block';

    // Hide form
    document.getElementById('formSection').classList.remove('active');
    hidePDFViewer();

    // Reset form
    resetForm();
    document.getElementById('contractIdDisplay').textContent = '';

    showMessage('Review mode exited.', 'success');
}

// Multiple Products Functions
function addProductRow() {
    const container = document.getElementById('productsContainer');
    const newRow = document.createElement('div');
    newRow.className = 'product-item';
    newRow.innerHTML = `
        <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 15px;">
            <div style="flex: 2;">
                <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #2c3e50;">Product *</label>
                <select class="product-select" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                    <option value="">Select a product...</option>
                </select>
            </div>
            <div style="flex: 1;">
                <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #2c3e50;">Quantity *</label>
                <input type="number" class="product-quantity" min="1" value="1" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
            </div>
            <button type="button" class="btn-icon-remove" onclick="removeProduct(this)" style="margin-top: 28px;" title="Remove product">🗑️</button>
        </div>
    `;
    container.appendChild(newRow);
    
    // Populate the new select with products
    populateProductSelect(newRow.querySelector('.product-select'));
}

function removeProduct(button) {
    const productItem = button.closest('.product-item');
    productItem.remove();
}

function populateProductSelect(selectElement) {
    // This is called after products are loaded
    const products = window.allProducts || [];
    selectElement.innerHTML = '<option value="">Select a product...</option>';
    products.forEach(product => {
        const option = document.createElement('option');
        option.value = product.id;
        // Display: Type - Volume TB (Subtype)
        let text = `${product.product_type}`;
        if (product.volume_tb) {
            text += ` - ${product.volume_tb} TB`;
        }
        if (product.subtype) {
            text += ` (${product.subtype})`;
        }
        option.textContent = text;
        selectElement.appendChild(option);
    });
}

// Quick Product Creation Functions
function showQuickProductForm() {
    document.getElementById('quickProductForm').style.display = 'block';
    document.getElementById('quickProductType').value = '';
    document.getElementById('quickProductVolume').value = '';
    document.getElementById('quickProductSubtype').value = '';
    document.getElementById('quickProductSubtypeGroup').style.display = 'none';
}

function cancelQuickProduct() {
    document.getElementById('quickProductForm').style.display = 'none';
}

function toggleQuickProductSubtype() {
    const productType = document.getElementById('quickProductType').value;
    const subtypeGroup = document.getElementById('quickProductSubtypeGroup');
    const subtypeSelect = document.getElementById('quickProductSubtype');

    if (productType === 'Appliance') {
        subtypeGroup.style.display = 'block';
        subtypeSelect.required = true;
    } else {
        subtypeGroup.style.display = 'none';
        subtypeSelect.required = false;
        subtypeSelect.value = '';
    }
}

async function createQuickProduct() {
    const productType = document.getElementById('quickProductType').value;
    const volumeTb = document.getElementById('quickProductVolume').value;
    const subtype = document.getElementById('quickProductSubtype').value;

    if (!productType) {
        showMessage('Please select a product type', 'error');
        return;
    }

    if (productType === 'Appliance' && !subtype) {
        showMessage('Please select a subtype for Appliance products', 'error');
        return;
    }

    const productData = {
        product_type: productType,
        volume_tb: volumeTb ? parseFloat(volumeTb) : null,
        subtype: subtype || null
    };

    try {
        const response = await fetch('/api/products', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        });

        if (!response.ok) {
            throw new Error('Failed to create product');
        }

        const newProduct = await response.json();

        // Add to global products list
        if (!window.allProducts) {
            window.allProducts = [];
        }
        window.allProducts.push(newProduct);

        // Refresh all product selects
        document.querySelectorAll('.product-select').forEach(select => {
            const currentValue = select.value;
            populateProductSelect(select);
            if (currentValue) {
                select.value = currentValue;
            }
        });

        showMessage('Product created successfully!', 'success');
        cancelQuickProduct();

    } catch (error) {
        console.error('Error creating product:', error);
        showMessage('Error creating product. Please try again.', 'error');
    }
}
