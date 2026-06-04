# API Reference: booking

Source file: `paas/api/booking/booking.py`

## Whitelisted API Endpoints

### `def create_booking_slot(data)`
Create a new booking slot (shift).

### `def get_booking_slots(shop_id)`
Get all booking slots for a specific shop.

### `def update_booking_slot(name, data)`
Update a booking slot.

### `def delete_booking_slot(name)`
Delete a booking slot.

### `def create_reservation(data)`
Create a new user reservation.

### `def get_my_reservations()`
Get the current user's reservations.

### `def get_shop_reservations(shop_id, status=None, date_from=None, date_to=None)`
Get all reservations for a specific shop.

### `def update_reservation_status(name, status)`
Update the status of a reservation.

### `def create_shop_section(data)`
<!-- c602279bc1e6671a835fd05feb838276197fb368343fcf74ed98936fea962363 -->
The create_shop_section function is used to create a new shop section in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create a shop section. The function first checks if the current user has permission to create a shop section, throwing a PermissionError if they do not. If permission is granted, it creates a new document based on the provided data and inserts it into the system, returning the newly created document.

### `def get_shop_section(name)`
*No documentation provided (generation failed).*

### `def update_shop_section(name, data)`
*No documentation provided (generation failed).*

### `def delete_shop_section(name)`
*No documentation provided (generation failed).*

### `def create_table(data)`
*No documentation provided (generation failed).*

### `def get_table(name)`
*No documentation provided (generation failed).*

### `def update_table(name, data)`
*No documentation provided (generation failed).*

### `def delete_table(name)`
*No documentation provided (generation failed).*

### `def get_shop_sections_for_booking(shop_id)`
Get all shop sections for a specific shop.

### `def get_tables_for_section(shop_section_id)`
Get all tables for a specific shop section.

### `def manage_shop_booking_working_days(shop_id, working_days)`
Manage the booking working days for a shop.

### `def manage_shop_booking_closed_dates(shop_id, closed_dates)`
Manage the booking closed dates for a shop.

### `def create_booking(data)`
*No documentation provided (generation failed).*

### `def get_booking(name)`
*No documentation provided (generation failed).*

### `def update_booking(name, data)`
*No documentation provided (generation failed).*

### `def delete_booking(name)`
*No documentation provided (generation failed).*

### `def create_user_booking(data)`
*No documentation provided (generation failed).*

### `def get_user_bookings()`
<!-- d1f87fae5cd9035be7d69bc56bcc111c83b034bbc93f49a9866ad8f547153154 -->
The get_user_bookings function retrieves a list of bookings associated with the current user. It takes no parameters, relying on internal state to determine the user's identity. The function serves as a wrapper around the get_my_reservations function, providing a simplified interface for accessing user-specific booking data.

### `def update_user_booking_status(name, status)`
*No documentation provided (generation failed).*

### `def get_shop_bookings(shop_id, status=None, date_from=None, date_to=None)`
*No documentation provided (generation failed).*

### `def get_shop_user_bookings(shop_id, status=None, date_from=None, date_to=None)`
*No documentation provided (generation failed).*

### `def update_shop_user_booking_status(name, status)`
*No documentation provided (generation failed).*

### `def get_my_bookings()`
*No documentation provided (generation failed).*

### `def cancel_my_booking(name)`
*No documentation provided (generation failed).*
