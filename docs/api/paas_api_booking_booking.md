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
*No documentation provided.*

### `def get_shop_section(name)`
*No documentation provided.*

### `def update_shop_section(name, data)`
*No documentation provided.*

### `def delete_shop_section(name)`
*No documentation provided.*

### `def create_table(data)`
*No documentation provided.*

### `def get_table(name)`
*No documentation provided.*

### `def update_table(name, data)`
*No documentation provided.*

### `def delete_table(name)`
*No documentation provided.*

### `def get_shop_sections_for_booking(shop_id)`
Get all shop sections for a specific shop.

### `def get_tables_for_section(shop_section_id)`
Get all tables for a specific shop section.

### `def manage_shop_booking_working_days(shop_id, working_days)`
Manage the booking working days for a shop.

### `def manage_shop_booking_closed_dates(shop_id, closed_dates)`
Manage the booking closed dates for a shop.

### `def create_booking(data)`
*No documentation provided.*

### `def get_booking(name)`
*No documentation provided.*

### `def update_booking(name, data)`
*No documentation provided.*

### `def delete_booking(name)`
*No documentation provided.*

### `def create_user_booking(data)`
*No documentation provided.*

### `def get_user_bookings()`
*No documentation provided.*

### `def update_user_booking_status(name, status)`
*No documentation provided.*

### `def get_shop_bookings(shop_id, status=None, date_from=None, date_to=None)`
*No documentation provided.*

### `def get_shop_user_bookings(shop_id, status=None, date_from=None, date_to=None)`
*No documentation provided.*

### `def update_shop_user_booking_status(name, status)`
*No documentation provided.*

### `def get_my_bookings()`
*No documentation provided.*

### `def cancel_my_booking(name)`
*No documentation provided.*

## Documented Module Functions

### `def check_shop_permission(shop_id, role)`
Check if the current user has permission for a given shop.

### `def check_availability(shop_id, table_id, start_date, end_date, exclude_reservation_id=None)`
Check if a table is available for the given time range.
Returns True if available, False otherwise.
