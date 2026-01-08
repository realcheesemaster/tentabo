from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
import shutil
import os
import hashlib
from pathlib import Path
from difflib import SequenceMatcher
import httpx

from database import get_db, init_db, Contract, Customer, Product, ContractStatus, ContractProduct
from models import (
    ContractCreate, ContractUpdate, ContractResponse, PDFParseResponse,
    CustomerCreate, CustomerUpdate, CustomerResponse, ContractCreateWithCustomer,
    ProductCreate, ProductUpdate, ProductResponse, BulkUploadResponse, DuplicateInfo,
    PennylaneCustomerLink
)
from pdf_parser import PDFParser

app = FastAPI(title="Contract Manager API")

# Pennylane API configuration
PENNYLANE_API_KEY = "ssht3SIkdTCxhcDCUw9fCV47-CxMEaFm72OD1tAkDtA"
PENNYLANE_API_BASE_URL = "https://app.pennylane.com/api/external/v2"

# Initialize database
init_db()

# Initialize PDF parser
pdf_parser = PDFParser()

# Create upload directory
UPLOAD_DIR = Path("../uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Serve frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("../frontend/index.html")


@app.get("/contracts")
async def contracts_page():
    """Serve the contracts list page."""
    return FileResponse("../frontend/contracts.html")


@app.get("/products")
async def products_page():
    """Serve the products management page."""
    return FileResponse("../frontend/products.html")


@app.get("/customers")
async def customers_page():
    """Serve the customers management page."""
    return FileResponse("../frontend/customers.html")


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    """Serve uploaded PDF files."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Use headers to force inline display in Firefox
    from fastapi.responses import Response
    with open(file_path, "rb") as f:
        pdf_content = f.read()

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )


def find_matching_customer(company_name: str, db: Session, threshold: float = 0.85):
    """Find a matching customer by fuzzy name matching."""
    if not company_name:
        return None

    customers = db.query(Customer).all()

    best_match = None
    best_ratio = 0.0

    for customer in customers:
        ratio = SequenceMatcher(None, company_name.lower(), customer.company_name.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = customer

    return best_match


def find_matching_product(product_name: str, db: Session, threshold: float = 0.85):
    """Find a matching product by fuzzy name matching."""
    if not product_name:
        return None

    products = db.query(Product).all()

    best_match = None
    best_ratio = 0.0

    for product in products:
        ratio = SequenceMatcher(None, product_name.lower(), product.name.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = product

    return best_match


@app.post("/api/upload", response_model=PDFParseResponse)
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF file and extract contract information."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save uploaded file temporarily to calculate hash
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Calculate file hash
    file_hash = calculate_file_hash(str(file_path))

    # Check if file with same hash already exists
    existing_by_hash = db.query(Contract).filter(
        Contract.file_hash == file_hash
    ).first()

    if existing_by_hash:
        # File is a duplicate - delete the newly uploaded file
        if file_path.exists():
            os.remove(file_path)

        # Return existing contract data
        parsed_data = {
            'filename': file.filename,
            'is_duplicate': True,
            'duplicate_reason': 'Identical PDF file already exists',
            'existing_contract_id': existing_by_hash.id
        }
        # Add existing contract data
        if existing_by_hash.customer:
            parsed_data['client_company_name'] = existing_by_hash.customer.company_name
            parsed_data['client_national_identifier'] = existing_by_hash.customer.national_identifier
            parsed_data['matched_customer_id'] = existing_by_hash.customer_id
            parsed_data['matched_customer_name'] = existing_by_hash.customer.company_name
        if existing_by_hash.product:
            parsed_data['product'] = existing_by_hash.product.name
            parsed_data['matched_product_id'] = existing_by_hash.product_id
            parsed_data['matched_product_name'] = existing_by_hash.product.name
        if existing_by_hash.contract_date:
            parsed_data['contract_date'] = str(existing_by_hash.contract_date)
        parsed_data['contract_duration'] = existing_by_hash.contract_duration
        parsed_data['contract_value'] = existing_by_hash.contract_value
        parsed_data['arr'] = existing_by_hash.arr

        return PDFParseResponse(**parsed_data)

    # Parse PDF
    try:
        parsed_data = pdf_parser.parse_contract(str(file_path), file.filename)

        # Try to match customer
        if parsed_data.get('client_company_name'):
            matched_customer = find_matching_customer(parsed_data['client_company_name'], db)
            if matched_customer:
                parsed_data['matched_customer_id'] = matched_customer.id
                parsed_data['matched_customer_name'] = matched_customer.company_name
                # Use existing customer data if parsed data is missing
                if not parsed_data.get('client_national_identifier'):
                    parsed_data['client_national_identifier'] = matched_customer.national_identifier

        # Try to match product
        if parsed_data.get('product'):
            matched_product = find_matching_product(parsed_data['product'], db)
            if matched_product:
                parsed_data['matched_product_id'] = matched_product.id
                parsed_data['matched_product_name'] = matched_product.name

        return PDFParseResponse(**parsed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")


@app.post("/api/upload-bulk", response_model=BulkUploadResponse)
async def upload_bulk_pdfs(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Upload multiple PDF files, parse them, and create draft contracts."""
    contract_ids = []
    duplicates = []

    for file in files:
        if not file.filename.endswith('.pdf'):
            continue

        try:
            # Save uploaded file temporarily to calculate hash
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Calculate file hash
            file_hash = calculate_file_hash(str(file_path))

            # Check if file with same hash already exists
            existing_by_hash = db.query(Contract).filter(
                Contract.file_hash == file_hash
            ).first()

            if existing_by_hash:
                duplicates.append(DuplicateInfo(
                    filename=file.filename,
                    reason="Identical PDF file already exists",
                    existing_contract_id=existing_by_hash.id
                ))
                # Delete the uploaded file since it's a duplicate
                if file_path.exists():
                    os.remove(file_path)
                continue

            # Parse PDF
            parsed_data = pdf_parser.parse_contract(str(file_path), file.filename)

            # Find or create customer
            customer = None
            if parsed_data.get('client_company_name'):
                customer = find_matching_customer(parsed_data['client_company_name'], db)
                if not customer:
                    customer = Customer(
                        company_name=parsed_data.get('client_company_name', 'Unknown'),
                        national_identifier=parsed_data.get('client_national_identifier'),
                        category=parsed_data.get('client_category', 'end-user')
                    )
                    db.add(customer)
                    db.commit()
                    db.refresh(customer)

            # Product will be handled manually in review mode
            product = None

            # Calculate ARR
            arr = None
            if parsed_data.get('contract_value') and parsed_data.get('contract_duration'):
                arr = round(parsed_data['contract_value'] / (parsed_data['contract_duration'] / 12), 2)

            # Convert contract_date string to date object if needed
            contract_date = parsed_data.get('contract_date')
            if contract_date and isinstance(contract_date, str):
                try:
                    contract_date = datetime.strptime(contract_date, '%Y-%m-%d').date()
                except ValueError:
                    contract_date = None

            # Create draft contract
            db_contract = Contract(
                customer_id=customer.id if customer else None,
                contract_date=contract_date,
                contract_duration=parsed_data.get('contract_duration'),
                contract_value=parsed_data.get('contract_value'),
                arr=arr or parsed_data.get('arr'),
                original_filename=file.filename,
                file_hash=file_hash,
                status=ContractStatus.DRAFT
            )

            db.add(db_contract)
            db.commit()
            db.refresh(db_contract)

            # Add product to contract if found
            if product:
                contract_product = ContractProduct(
                    contract_id=db_contract.id,
                    product_id=product.id,
                    quantity=1
                )
                db.add(contract_product)
                db.commit()

            contract_ids.append(db_contract.id)

        except Exception as e:
            print(f"Error processing {file.filename}: {str(e)}")
            continue

    return BulkUploadResponse(
        total_files=len(files),
        contracts_created=len(contract_ids),
        duplicates_ignored=len(duplicates),
        contract_ids=contract_ids,
        duplicates=duplicates
    )


@app.get("/api/contracts/draft", response_model=List[ContractResponse])
async def get_draft_contracts(db: Session = Depends(get_db)):
    """Retrieve all contracts with draft status."""
    contracts = db.query(Contract).filter(Contract.status == ContractStatus.DRAFT).all()
    return contracts


# Customer endpoints
@app.get("/api/customers", response_model=List[CustomerResponse])
async def get_customers(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Retrieve all customers."""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@app.get("/api/customers/search", response_model=List[CustomerResponse])
async def search_customers(q: str, db: Session = Depends(get_db)):
    """Search customers by name."""
    customers = db.query(Customer).filter(
        Customer.company_name.ilike(f"%{q}%")
    ).limit(10).all()
    return customers


@app.get("/api/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific customer by ID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.post("/api/customers", response_model=CustomerResponse)
async def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer."""
    # Check if customer already exists
    existing = db.query(Customer).filter(
        func.lower(Customer.company_name) == func.lower(customer.company_name)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Customer with this name already exists")

    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@app.put("/api/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing customer."""
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)

    db.commit()
    db.refresh(db_customer)
    return db_customer


# Pennylane API endpoints
@app.get("/api/pennylane/customers/page")
async def get_pennylane_customers_page(cursor: str = None):
    """Fetch a single page of customers from Pennylane API."""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {PENNYLANE_API_KEY}",
                "Content-Type": "application/json"
            }

            params = {}
            if cursor:
                params['cursor'] = cursor

            response = await client.get(
                f"{PENNYLANE_API_BASE_URL}/customers",
                headers=headers,
                params=params,
                timeout=30.0
            )

            # Handle rate limiting with retry
            if response.status_code == 429:
                import asyncio
                await asyncio.sleep(5)
                response = await client.get(
                    f"{PENNYLANE_API_BASE_URL}/customers",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Pennylane API error: {response.text}"
                )

            data = response.json()

            return {
                "customers": data.get('items', []),
                "has_more": data.get('has_more', False),
                "next_cursor": data.get('next_cursor')
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Pennylane API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Pennylane API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/pennylane/customers")
async def get_pennylane_customers():
    """Fetch all customers from Pennylane API with pagination."""
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {PENNYLANE_API_KEY}",
                "Content-Type": "application/json"
            }

            all_customers = []
            cursor = None
            has_more = True
            page = 0

            # Fetch all pages
            while has_more:
                page += 1
                params = {}
                if cursor:
                    params['cursor'] = cursor

                print(f"Fetching page {page}, cursor: {cursor}")

                # Add delay to avoid rate limiting (wait 1 second between requests)
                if page > 1:
                    import asyncio
                    await asyncio.sleep(1)

                response = await client.get(
                    f"{PENNYLANE_API_BASE_URL}/customers",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )

                print(f"Response status: {response.status_code}")

                # Handle rate limiting with retry
                if response.status_code == 429:
                    print("Rate limit hit, waiting 5 seconds before retry...")
                    import asyncio
                    await asyncio.sleep(5)
                    # Retry the same request
                    response = await client.get(
                        f"{PENNYLANE_API_BASE_URL}/customers",
                        headers=headers,
                        params=params,
                        timeout=30.0
                    )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Pennylane API error: {response.text}"
                    )

                data = response.json()
                items = data.get('items', [])
                all_customers.extend(items)

                print(f"Page {page}: got {len(items)} items, total so far: {len(all_customers)}")
                print(f"has_more: {data.get('has_more')}, next_cursor: {data.get('next_cursor')}")

                has_more = data.get('has_more', False)
                cursor = data.get('next_cursor')

            print(f"Final total: {len(all_customers)} customers")
            return {"customers": all_customers, "total": len(all_customers)}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Pennylane API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Pennylane API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/pennylane/link-customer")
async def link_pennylane_customer(
    link_data: PennylaneCustomerLink,
    db: Session = Depends(get_db)
):
    """Link a local customer to a Pennylane customer."""
    # Check if local customer exists
    customer = db.query(Customer).filter(Customer.id == link_data.local_customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Local customer not found")

    # Check if another customer is already linked to this Pennylane customer
    existing_link = db.query(Customer).filter(
        Customer.pennylane_customer_id == link_data.pennylane_customer_id,
        Customer.id != link_data.local_customer_id
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=400,
            detail=f"Pennylane customer is already linked to {existing_link.company_name}"
        )

    # Link the customers
    customer.pennylane_customer_id = link_data.pennylane_customer_id
    db.commit()
    db.refresh(customer)

    return {"message": "Customers linked successfully", "customer": customer}


@app.delete("/api/pennylane/link-customer/{local_customer_id}")
async def unlink_pennylane_customer(local_customer_id: int, db: Session = Depends(get_db)):
    """Unlink a local customer from Pennylane."""
    customer = db.query(Customer).filter(Customer.id == local_customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.pennylane_customer_id = None
    db.commit()

    return {"message": "Customer unlinked successfully"}


@app.post("/api/pennylane/auto-match-customers")
async def auto_match_customers(db: Session = Depends(get_db)):
    """Auto-match local customers with Pennylane customers based on first 9 characters of national identifier (SIREN)."""
    try:
        # Fetch all Pennylane customers
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {PENNYLANE_API_KEY}",
                "Content-Type": "application/json"
            }

            all_pennylane_customers = []
            cursor = None
            has_more = True

            while has_more:
                params = {}
                if cursor:
                    params['cursor'] = cursor

                import asyncio
                if cursor:
                    await asyncio.sleep(1)

                response = await client.get(
                    f"{PENNYLANE_API_BASE_URL}/customers",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )

                if response.status_code == 429:
                    await asyncio.sleep(5)
                    response = await client.get(
                        f"{PENNYLANE_API_BASE_URL}/customers",
                        headers=headers,
                        params=params,
                        timeout=30.0
                    )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Pennylane API error: {response.text}"
                    )

                data = response.json()
                all_pennylane_customers.extend(data.get('items', []))
                has_more = data.get('has_more', False)
                cursor = data.get('next_cursor')

        # Get all local customers with national identifiers
        local_customers = db.query(Customer).filter(
            Customer.national_identifier.isnot(None),
            Customer.national_identifier != ''
        ).all()

        matches = []

        for local_customer in local_customers:
            # Skip if already linked
            if local_customer.pennylane_customer_id:
                continue

            local_siren = local_customer.national_identifier[:9] if local_customer.national_identifier else None
            if not local_siren or len(local_siren) < 9:
                continue

            # Find matching Pennylane customer
            for pennylane_customer in all_pennylane_customers:
                pennylane_reg_no = pennylane_customer.get('reg_no', '')
                pennylane_siren = pennylane_reg_no[:9] if pennylane_reg_no else None

                if pennylane_siren and local_siren == pennylane_siren:
                    # Check if this Pennylane customer is already linked to someone else
                    existing_link = db.query(Customer).filter(
                        Customer.pennylane_customer_id == str(pennylane_customer['id'])
                    ).first()

                    if not existing_link:
                        # Create the link
                        local_customer.pennylane_customer_id = str(pennylane_customer['id'])
                        matches.append({
                            'local_customer_id': local_customer.id,
                            'local_customer_name': local_customer.company_name,
                            'pennylane_customer_id': pennylane_customer['id'],
                            'pennylane_customer_name': pennylane_customer['name'],
                            'siren': local_siren
                        })
                        break

        db.commit()

        return {
            "matched_count": len(matches),
            "matches": matches
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error auto-matching customers: {str(e)}")


@app.get("/api/pennylane/customer-links")
async def get_customer_links(db: Session = Depends(get_db)):
    """Get all customer links between local and Pennylane customers."""
    linked_customers = db.query(Customer).filter(
        Customer.pennylane_customer_id.isnot(None)
    ).all()

    return {
        "links": [
            {
                "local_customer_id": c.id,
                "local_customer_name": c.company_name,
                "pennylane_customer_id": c.pennylane_customer_id
            }
            for c in linked_customers
        ]
    }


# Product endpoints
@app.get("/api/products", response_model=List[ProductResponse])
async def get_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all products."""
    products = db.query(Product).offset(skip).limit(limit).all()
    return products


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.put("/api/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product is used in any contracts
    contracts_count = db.query(ContractProduct).filter(ContractProduct.product_id == product_id).count()
    if contracts_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete product. It is used in {contracts_count} contract(s)."
        )

    db.delete(db_product)
    db.commit()

    return {"message": "Product deleted successfully"}


# Contract endpoints
@app.post("/api/contracts", response_model=ContractResponse)
async def create_contract(contract: ContractCreateWithCustomer, db: Session = Depends(get_db)):
    """Create a new contract with customer and product information."""
    # Calculate ARR if not provided (ARR = value / (duration in months / 12))
    if contract.arr is None and contract.contract_value and contract.contract_duration:
        arr = round(contract.contract_value / (contract.contract_duration / 12), 2)
    else:
        arr = contract.arr

    # Find or create customer
    customer = db.query(Customer).filter(
        func.lower(Customer.company_name) == func.lower(contract.customer_name)
    ).first()

    if customer:
        # Update customer info if provided and different
        if contract.customer_national_identifier and contract.customer_national_identifier != customer.national_identifier:
            customer.national_identifier = contract.customer_national_identifier
        if contract.customer_category and contract.customer_category != customer.category:
            customer.category = contract.customer_category
        db.commit()
        db.refresh(customer)
    else:
        # Create new customer
        customer = Customer(
            company_name=contract.customer_name,
            national_identifier=contract.customer_national_identifier,
            category=contract.customer_category
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # Handle optional reseller
    reseller_id = None
    if contract.reseller_name:
        reseller = db.query(Customer).filter(
            func.lower(Customer.company_name) == func.lower(contract.reseller_name)
        ).first()

        if reseller:
            if contract.reseller_national_identifier and contract.reseller_national_identifier != reseller.national_identifier:
                reseller.national_identifier = contract.reseller_national_identifier
            db.commit()
            db.refresh(reseller)
        else:
            reseller = Customer(
                company_name=contract.reseller_name,
                national_identifier=contract.reseller_national_identifier,
                category=CustomerCategory.RESELLER
            )
            db.add(reseller)
            db.commit()
            db.refresh(reseller)

        reseller_id = reseller.id

    # Handle optional end-user
    end_user_id = None
    if contract.end_user_name:
        end_user = db.query(Customer).filter(
            func.lower(Customer.company_name) == func.lower(contract.end_user_name)
        ).first()

        if end_user:
            if contract.end_user_national_identifier and contract.end_user_national_identifier != end_user.national_identifier:
                end_user.national_identifier = contract.end_user_national_identifier
            db.commit()
            db.refresh(end_user)
        else:
            end_user = Customer(
                company_name=contract.end_user_name,
                national_identifier=contract.end_user_national_identifier,
                category=CustomerCategory.END_USER
            )
            db.add(end_user)
            db.commit()
            db.refresh(end_user)

        end_user_id = end_user.id

    # Calculate file hash for the uploaded file
    file_path = UPLOAD_DIR / contract.original_filename
    file_hash = None
    if file_path.exists():
        file_hash = calculate_file_hash(str(file_path))

        # Check for duplicate file hash (for all contracts, including drafts)
        if file_hash:
            existing_contract = db.query(Contract).filter(Contract.file_hash == file_hash).first()
            if existing_contract:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate file detected. Contract already exists with ID: {existing_contract.id}"
                )

    # Create contract
    db_contract = Contract(
        customer_id=customer.id,
        reseller_id=reseller_id,
        end_user_id=end_user_id,
        contract_date=contract.contract_date,
        contract_duration=contract.contract_duration,
        contract_value=contract.contract_value,
        arr=arr,
        original_filename=contract.original_filename,
        file_hash=file_hash,
        status=contract.status
    )

    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)

    # Add products to contract
    for product_data in contract.products:
        contract_product = ContractProduct(
            contract_id=db_contract.id,
            product_id=product_data.product_id,
            quantity=product_data.quantity
        )
        db.add(contract_product)

    db.commit()
    db.refresh(db_contract)

    return db_contract


@app.get("/api/contracts", response_model=List[ContractResponse])
async def get_contracts(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Retrieve all contracts."""
    contracts = db.query(Contract).offset(skip).limit(limit).all()
    return contracts


@app.get("/api/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@app.put("/api/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract: ContractUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing contract."""
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if db_contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Update fields
    update_data = contract.dict(exclude_unset=True)

    # Recalculate ARR if value or duration changed
    if 'contract_value' in update_data or 'contract_duration' in update_data:
        value = update_data.get('contract_value', db_contract.contract_value)
        duration = update_data.get('contract_duration', db_contract.contract_duration)
        if value and duration:
            update_data['arr'] = round(value / (duration / 12), 2)

    # Handle products update if provided
    if 'products' in update_data:
        products = update_data.pop('products')

        # Delete existing contract products
        db.query(ContractProduct).filter(ContractProduct.contract_id == contract_id).delete()

        # Add new products
        for product_data in products:
            # product_data can be either a dict or a Pydantic model
            if isinstance(product_data, dict):
                product_id = product_data['product_id']
                quantity = product_data.get('quantity', 1)
            else:
                product_id = product_data.product_id
                quantity = product_data.quantity

            contract_product = ContractProduct(
                contract_id=contract_id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(contract_product)

    for field, value in update_data.items():
        setattr(db_contract, field, value)

    db.commit()
    db.refresh(db_contract)

    return db_contract


@app.delete("/api/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    """Delete a contract."""
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if db_contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    db.delete(db_contract)
    db.commit()

    return {"message": "Contract deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="10.0.0.1", port=8000)
