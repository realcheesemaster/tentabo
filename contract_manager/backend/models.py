from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from database import CustomerCategory, ContractStatus


# Customer models
class CustomerBase(BaseModel):
    company_name: str
    national_identifier: Optional[str] = None
    category: CustomerCategory = CustomerCategory.END_USER


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = None
    national_identifier: Optional[str] = None
    category: Optional[CustomerCategory] = None


class CustomerResponse(CustomerBase):
    id: int

    class Config:
        from_attributes = True


# Product models
class ProductBase(BaseModel):
    product_type: str  # Cloud, Cloud MSP, Appliance, License
    volume_tb: Optional[float] = None
    subtype: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    product_type: Optional[str] = None
    volume_tb: Optional[float] = None
    subtype: Optional[str] = None


class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True


# ContractProduct models
class ContractProductBase(BaseModel):
    product_id: int
    quantity: int = 1


class ContractProductResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductResponse

    class Config:
        from_attributes = True


# Contract models
class ContractBase(BaseModel):
    contract_date: Optional[date] = None
    contract_duration: Optional[int] = None  # in months
    contract_value: Optional[float] = None
    arr: Optional[float] = None


class ContractCreate(ContractBase):
    customer_id: int
    product_id: int
    original_filename: str


class ContractUpdate(ContractBase):
    customer_id: Optional[int] = None
    reseller_id: Optional[int] = None
    end_user_id: Optional[int] = None
    status: Optional[ContractStatus] = None
    products: Optional[List[ContractProductBase]] = None
    replaced_by_contract_id: Optional[int] = None


class ContractResponse(ContractBase):
    id: int
    customer_id: Optional[int] = None
    reseller_id: Optional[int] = None
    end_user_id: Optional[int] = None
    original_filename: Optional[str] = None
    status: ContractStatus
    replaced_by_contract_id: Optional[int] = None
    customer: Optional[CustomerResponse] = None
    reseller: Optional[CustomerResponse] = None
    end_user: Optional[CustomerResponse] = None
    contract_products: List[ContractProductResponse] = []

    class Config:
        from_attributes = True


# PDF parsing response
class PDFParseResponse(BaseModel):
    client_company_name: Optional[str] = None
    client_company_address: Optional[str] = None
    client_national_identifier: Optional[str] = None
    contract_date: Optional[str] = None
    product: Optional[str] = None
    contract_duration: Optional[int] = None  # in months
    contract_value: Optional[float] = None
    arr: Optional[float] = None
    filename: str
    matched_customer_id: Optional[int] = None
    matched_customer_name: Optional[str] = None
    matched_product_id: Optional[int] = None
    matched_product_name: Optional[str] = None
    is_duplicate: bool = False
    duplicate_reason: Optional[str] = None
    existing_contract_id: Optional[int] = None


# Contract creation with customer and product info
class ContractCreateWithCustomer(ContractBase):
    customer_name: str
    customer_national_identifier: Optional[str] = None
    customer_category: Optional[CustomerCategory] = CustomerCategory.END_USER
    original_filename: str
    status: Optional[ContractStatus] = ContractStatus.ACTIVE
    products: List[ContractProductBase] = []
    # Optional reseller information
    reseller_name: Optional[str] = None
    reseller_national_identifier: Optional[str] = None
    # Optional end-user information
    end_user_name: Optional[str] = None
    end_user_national_identifier: Optional[str] = None


# Duplicate file info
class DuplicateInfo(BaseModel):
    filename: str
    reason: str
    existing_contract_id: Optional[int] = None


# Bulk upload response
class BulkUploadResponse(BaseModel):
    total_files: int
    contracts_created: int
    duplicates_ignored: int
    contract_ids: List[int]
    duplicates: List[DuplicateInfo]


# Pennylane customer link
class PennylaneCustomerLink(BaseModel):
    local_customer_id: int
    pennylane_customer_id: str
