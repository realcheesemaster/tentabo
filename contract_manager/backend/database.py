from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

SQLALCHEMY_DATABASE_URL = "sqlite:///./contracts.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class CustomerCategory(str, enum.Enum):
    END_USER = "end-user"
    RESELLER = "reseller"
    DISTRIBUTOR = "distributor"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    TERMINATED = "terminated"
    REPLACED = "replaced"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, unique=True, index=True, nullable=False)
    national_identifier = Column(String, index=True)
    category = Column(Enum(CustomerCategory), default=CustomerCategory.END_USER)
    pennylane_customer_id = Column(String, index=True)  # Link to Pennylane customer ID

    # Relationship to contracts (only for primary customer)
    contracts = relationship("Contract", foreign_keys="Contract.customer_id", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_type = Column(String, nullable=False)  # Cloud, Cloud MSP, Appliance, License
    volume_tb = Column(Float)  # Volume in TB
    subtype = Column(String)  # Optional subtype

    # Relationships
    contract_products = relationship("ContractProduct", back_populates="product")


class ContractProduct(Base):
    """Junction table for many-to-many relationship between contracts and products"""
    __tablename__ = "contract_products"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    # Relationships
    contract = relationship("Contract", back_populates="contract_products")
    product = relationship("Product", back_populates="contract_products")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys to customers (hierarchy: distributor -> reseller -> end-user)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)  # Main customer (who signed the contract)
    reseller_id = Column(Integer, ForeignKey("customers.id"), nullable=True)  # Optional reseller
    end_user_id = Column(Integer, ForeignKey("customers.id"), nullable=True)  # Optional end-user

    # Contract characteristics
    contract_date = Column(Date)
    contract_duration = Column(Integer)  # in months
    contract_value = Column(Float)
    arr = Column(Float)  # Annual Recurring Revenue

    # Metadata
    original_filename = Column(String)
    file_hash = Column(String, unique=True, index=True)  # SHA256 hash of PDF file
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT, index=True)

    # Contract replacement tracking
    replaced_by_contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id], back_populates="contracts")
    reseller = relationship("Customer", foreign_keys=[reseller_id])
    end_user = relationship("Customer", foreign_keys=[end_user_id])
    contract_products = relationship("ContractProduct", back_populates="contract", cascade="all, delete-orphan")
    replaced_by = relationship("Contract", remote_side="Contract.id", foreign_keys=[replaced_by_contract_id])


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
