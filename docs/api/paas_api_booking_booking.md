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
The create_shop_section function is used to create a new shop section in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create a shop section. The function first checks if the current user has permission to create a shop section, throwing a PermissionError if they do not. If permission is granted, it creates a new document based on the provided data and inserts it into the system, returning the newly created document.

### `def get_shop_section(name)`
The get_shop_section function retrieves a specific shop section document from the database. It takes one parameter, name, which is the name of the shop section to be retrieved. This function utilizes the frappe framework to fetch the document, allowing for easy access to the shop section's details.

### `def update_shop_section(name, data)`
The update_shop_section function updates an existing shop section document with new data. It takes two parameters: name, which is the name of the shop section to be updated, and data, which is a dictionary containing the new data to be applied to the shop section. The function first checks if the user has write permission for the shop section, throwing a permission error if not. If permission is granted, it retrieves the shop section document, updates it with the provided data, saves the changes, and returns the updated document.

### `def delete_shop_section(name)`
The delete_shop_section function is used to delete a specific shop section from the system. It takes one parameter, name, which represents the name of the shop section to be deleted. The function first checks if the user has the necessary permission to delete a shop section, and if not, it throws a permission error. If the user has permission, it proceeds to delete the shop section with the specified name and returns a success status along with a confirmation message.

### `def create_table(data)`
The create_table function is used to create a new table in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create the table. The function first checks if the user has the necessary permission to create a table, throwing a PermissionError if they do not. If permission is granted, it retrieves the document using the provided data, inserts it into the system, and returns the newly created document.

### `def get_table(name)`
The get_table function retrieves a specific table document from the database. It takes one parameter, name, which represents the name of the table to be retrieved. The function utilizes the frappe framework to fetch the table document, returning the result as a document object.

### `def update_table(name, data)`
The update_table function updates an existing table document in the database. It takes two parameters: name, which specifies the name of the table to be updated, and data, which contains the new data to be applied to the table. The function first checks if the user has write permission for the table, throwing a permission error if not. If permitted, it retrieves the table document, applies the updates, saves the changes, and returns the updated document.

### `def delete_table(name)`
The delete_table function is used to delete a table from the database. It takes one parameter, name, which specifies the name of the table to be deleted. The function first checks if the user has permission to delete tables, and if not, it throws a permission error. If the user has permission, it deletes the table with the specified name and returns a success message.

### `def get_shop_sections_for_booking(shop_id)`
Get all shop sections for a specific shop.

### `def get_tables_for_section(shop_section_id)`
Get all tables for a specific shop section.

### `def manage_shop_booking_working_days(shop_id, working_days)`
Manage the booking working days for a shop.

### `def manage_shop_booking_closed_dates(shop_id, closed_dates)`
Manage the booking closed dates for a shop.

### `def create_booking(data)`
The **create_booking** function serves as a simple wrapper that initiates the creation of a new booking. It accepts a single argument, **data**, which should contain all the necessary information required to define the booking (the exact structure of this data is determined by the underlying implementation of the booking system). Inside the function, the provided **data** is passed directly to **create_booking_slot**, which performs the actual booking‑slot creation and returns its result. In summary, **create_booking** offers a concise, high‑level interface for creating bookings by delegating the work to **create_booking_slot**.

### `def get_booking(name)`
The get_booking function retrieves a specific booking document from the database. It takes one parameter, name, which is the unique identifier of the booking to be retrieved. The function uses the frappe framework to fetch the booking document with the specified name and returns it as a document object.

### `def update_booking(name, data)`
The update_booking function is used to modify an existing booking. It takes two parameters: name and data. The name parameter represents the identifier of the booking to be updated, while the data parameter contains the new information to be applied to the booking. This function serves as a wrapper around the update_booking_slot function, which performs the actual update operation.

### `def delete_booking(name)`
The delete_booking function is used to cancel a booking by removing the associated booking slot. It takes one parameter, name, which represents the name of the booking to be deleted. This function serves as a wrapper around the delete_booking_slot function, providing a simplified interface for deleting bookings.

### `def create_user_booking(data)`
The create_user_booking function is used to generate a new user booking by creating a reservation. It takes one parameter, data, which is expected to contain all necessary information required to create the booking, such as user details and reservation specifics. This function essentially serves as a wrapper around the create_reservation function, passing the provided data to it to complete the booking process.

### `def get_user_bookings()`
The get_user_bookings function retrieves a list of bookings associated with the current user. It takes no parameters, relying on internal state to determine the user's identity. The function serves as a wrapper around the get_my_reservations function, providing a simplified interface for accessing user-specific booking data.

### `def update_user_booking_status(name, status)`
The update_user_booking_status function updates the status of a user's booking in the system. It takes two parameters: name, which represents the name of the user whose booking status is to be updated, and status, which represents the new status to be assigned to the user's booking. This function serves as a wrapper around the update_reservation_status function, providing a more specific and user-centric interface for managing booking statuses.

### `def get_shop_bookings(shop_id, status=None, date_from=None, date_to=None)`
The get_shop_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their current status, while date_from and date_to allow for filtering by a specific date range. If these optional parameters are not provided, the function will return all bookings for the specified shop.

### `def get_shop_user_bookings(shop_id, status=None, date_from=None, date_to=None)`
The get_shop_user_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their status, while date_from and date_to filter bookings by a specific date range. The function leverages the get_shop_reservations function to fetch the relevant data, providing a simplified interface for accessing shop user bookings.

### `def update_shop_user_booking_status(name, status)`
The update_shop_user_booking_status function updates the status of a user's booking at a shop. It takes two parameters: name, which represents the name of the user or booking to be updated, and status, which represents the new status to be applied to the booking. This function serves as a wrapper around the update_reservation_status function, providing a shop-specific interface for managing user bookings.

### `def get_my_bookings()`
The get_my_bookings function retrieves a list of bookings associated with the current user. This function takes no parameters and returns the result of the get_my_reservations function, effectively serving as an alias for retrieving user-specific reservation data.

### `def cancel_my_booking(name)`
The cancel_my_booking function is used to cancel an existing booking by updating its reservation status. It takes one parameter, name, which represents the name associated with the booking to be cancelled. This function internally calls the update_reservation_status function, passing the provided name and the status "Cancelled" to effect the cancellation.
