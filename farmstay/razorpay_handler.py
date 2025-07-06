import razorpay
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Razorpay credentials from environment or hardcoded fallback
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_ZemE8STl4VIdIS')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '6vb5IaV8kM1hSyrFflNxFaaJ')

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_payment_order(details):
    """
    Create Razorpay order and return full booking + order details.

    :param details: dict with keys:
        name, email, phone, guests, checkin, checkout, amount
    :return: dict
    """
    try:
        # Extract and validate fields
        name = details.get("name", "")
        email = details.get("email", "")
        phone = details.get("phone", "")
        guests = details.get("guests", 0)
        checkin = details.get("checkin", "")
        checkout = details.get("checkout", "")
        amount_inr = float(details.get("amount", 0))

        if amount_inr <= 0:
            return {"error": "Invalid amount"}

        # Convert INR to paise for Razorpay
        amount_paise = int(amount_inr * 100)

        # Create Razorpay order
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1
        })

        # Return full booking + order details
        return {
            "success": True,
            "message": "Booking order created successfully.",
            "booking_details": {
                "name": name,
                "email": email,
                "phone": phone,
                "guests": guests,
                "checkin": checkin,
                "checkout": checkout,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "razorpay_order": order,
            "amount": amount_inr,
            "order_id": order.get("id"),
            "currency": "INR"
        }

    except Exception as e:
        print(f"[ERROR] Razorpay order creation failed: {e}")
        return {"error": "Failed to create Razorpay order", "details": str(e)}
