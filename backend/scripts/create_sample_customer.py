"""
Script to create a sample customer for testing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.models import Customer

def create_sample_customer():
    db = SessionLocal()
    try:
        # Check if Global Industrial already exists
        existing = db.query(Customer).filter(Customer.name == "Global Industrial").first()
        if existing:
            print(f"Customer 'Global Industrial' already exists with ID: {existing.id}")
            return
        
        customer = Customer(
            name="Global Industrial",
            contact_name="Nick",
            contact_email="nick@globalindustrial.com"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        print(f"Created customer: {customer.name} (ID: {customer.id})")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_customer()

