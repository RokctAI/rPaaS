# API Reference: admin_records

Source file: `paas/api/admin_records/admin_records.py`

## Whitelisted API Endpoints

### `def get_all_orders(limit_start=0, limit_page_length=20, status=None, from_date=None, to_date=None)`
Retrieves a list of all orders on the platform (for admins).

### `def get_all_parcel_orders(limit_start=0, limit_page_length=20, status=None, from_date=None, to_date=None)`
Retrieves a list of all parcel orders on the platform (for admins).

### `def delete_admin_parcel_order(parcel_order_id)`
Deletes a parcel order (for admins).

### `def assign_deliveryman_to_parcel(parcel_order_id, deliveryman_id)`
The assign_deliveryman_to_parcel function assigns a deliveryman to a specific parcel order. This function is restricted to admin users and requires two parameters: parcel_order_id, which is the unique identifier of the parcel order, and deliveryman_id, which is the unique identifier of the deliveryman to be assigned. The function validates the existence of the deliveryman and then updates the parcel order with the assigned deliveryman, returning the updated parcel order details.

### `def get_all_reviews(limit_start=0, limit_page_length=20)`
Retrieves a list of all reviews on the platform (for admins).

### `def update_admin_review(review_name, review_data)`
Updates a review (for admins).

### `def delete_admin_review(review_name)`
Deletes a review (for admins).

### `def get_all_tickets(limit_start=0, limit_page_length=20)`
Retrieves a list of all tickets on the platform (for admins).

### `def update_admin_ticket(ticket_name, ticket_data)`
Updates a ticket (for admins).

### `def get_all_order_refunds(limit_start=0, limit_page_length=20)`
Retrieves a list of all order refunds on the platform (for admins).

### `def update_admin_order_refund(refund_name, status, answer=None)`
Updates the status and answer of an order refund (for admins).

### `def get_all_notifications(limit_start=0, limit_page_length=20)`
Retrieves a list of all notifications on the platform (for admins).

### `def get_all_bookings(limit_start=0, limit_page_length=20)`
Retrieves a list of all bookings on the platform (for admins).

### `def create_booking(booking_data)`
Creates a new booking (for admins).

### `def update_booking(booking_name, booking_data)`
Updates a booking (for admins).

### `def delete_booking(booking_name)`
Deletes a booking (for admins).

### `def get_all_order_statuses(limit_start=0, limit_page_length=20)`
Retrieves a list of all order statuses on the platform (for admins).

### `def get_all_request_models(limit_start=0, limit_page_length=20)`
Retrieves a list of all request models on the platform (for admins).
