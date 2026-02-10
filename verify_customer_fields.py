from app import app, db
from models import Customer, Director

def verify():
    with app.app_context():
        # Ensure a director exists
        director = Director.query.first()
        if not director:
            director = Director(name="Test Director", phone="1234567890")
            db.session.add(director)
            db.session.commit()
            print("Created test director.")
        
        # Create a customer with new fields
        customer_id = "TEST-CUST-001"
        new_customer = Customer(
            director_id=director.id,
            customer_id=customer_id,
            name="Test Customer",
            phone="9876543210",
            father_name="Test Father",
            mother_name="Test Mother",
            dob="1990-01-01",
            religion="Islam",
            profession="Engineer",
            nid_no="1234567890123",
            present_address="Test Present Address",
            permanent_address="Test Permanent Address",
            plot_no="A-1",
            total_price=100000,
            down_payment=10000,
            monthly_installment=5000,
            total_paid=10000,
            due_amount=90000
        )
        
        db.session.add(new_customer)
        db.session.commit()
        print(f"Created customer {customer_id}.")
        
        # Verify fields
        saved_customer = Customer.query.filter_by(customer_id=customer_id).first()
        if saved_customer:
            print(f"Father Name: {saved_customer.father_name}")
            print(f"Mother Name: {saved_customer.mother_name}")
            print(f"DOB: {saved_customer.dob}")
            print(f"Religion: {saved_customer.religion}")
            print(f"Profession: {saved_customer.profession}")
            print(f"NID No: {saved_customer.nid_no}")
            print(f"Present Address: {saved_customer.present_address}")
            print(f"Permanent Address: {saved_customer.permanent_address}")
            
            # Clean up
            db.session.delete(saved_customer)
            db.session.commit()
            print("Verification successful and cleaned up.")
        else:
            print("Verification failed: Customer not found.")

if __name__ == "__main__":
    verify()
