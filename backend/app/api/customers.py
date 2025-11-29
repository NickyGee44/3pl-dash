"""
Customer API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse

router = APIRouter()


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    # Check if customer with same name exists
    existing = db.query(Customer).filter(Customer.name == customer_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with name '{customer_data.name}' already exists"
        )
    
    customer = Customer(
        name=customer_data.name,
        contact_name=customer_data.contact_name,
        contact_email=customer_data.contact_email,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return customer


@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    db: Session = Depends(get_db)
):
    """List all customers."""
    customers = db.query(Customer).order_by(Customer.name).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    return customer

