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
<!-- 01db8071abc25e30e122d58dc9c6103336f43cdde0f6301521933816e3c82b7e -->
The get_shop_section function retrieves a specific shop section document from the database. It takes one parameter, name, which is the name of the shop section to be retrieved. This function utilizes the frappe framework to fetch the document, allowing for easy access to the shop section's details.

### `def update_shop_section(name, data)`
<!-- e2aae00370cee2af8cb979a86090360c418dac03b1551a44ee543e82239034f8 -->
The update_shop_section function updates an existing shop section document with new data. It takes two parameters: name, which is the name of the shop section to be updated, and data, which is a dictionary containing the new data to be applied to the shop section. The function first checks if the user has write permission for the shop section, throwing a permission error if not. If permission is granted, it retrieves the shop section document, updates it with the provided data, saves the changes, and returns the updated document.

### `def delete_shop_section(name)`
<!-- 3f8e3e8f98fc229cd62660d87e56313b20d9edfbaf8c6222000b94b57d76e11d -->
The delete_shop_section function is used to delete a specific shop section from the system. It takes one parameter, name, which represents the name of the shop section to be deleted. The function first checks if the user has the necessary permission to delete a shop section, and if not, it throws a permission error. If the user has permission, it proceeds to delete the shop section with the specified name and returns a success status along with a confirmation message.

### `def create_table(data)`
<!-- 1f0b5f664c8fac44366e85b97712f1aaf562df50afbb61bbab32634e1c6d34bd -->
The create_table function is used to create a new table in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create the table. The function first checks if the user has the necessary permission to create a table, throwing a PermissionError if they do not. If permission is granted, it retrieves the document using the provided data, inserts it into the system, and returns the newly created document.

### `def get_table(name)`
<!-- a64f7d53084917166dd7588461f2bdbc4d161ce67bd76698ef46fb1f4c27b39c -->
The get_table function retrieves a specific table document from the database. It takes one parameter, name, which represents the name of the table to be retrieved. The function utilizes the frappe framework to fetch the table document, returning the result as a document object.

### `def update_table(name, data)`
<!-- b69539a5d74b2f739cda426e253e5186bcb7622fff7125b7256fb73a4a04f6d6 -->
The update_table function updates an existing table document in the database. It takes two parameters: name, which specifies the name of the table to be updated, and data, which contains the new data to be applied to the table. The function first checks if the user has write permission for the table, throwing a permission error if not. If permitted, it retrieves the table document, applies the updates, saves the changes, and returns the updated document.

### `def delete_table(name)`
<!-- 42356639cd39b0237ff0343d9358bcbcc5d3772f8716c73effd5d1a56929a76e -->
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
<!-- 764505ff676f0ab3734e99b612e7af8f0a46f8efba49ceed37ca29cce437ca6f -->
The **create_booking** function serves as a simple wrapper that initiates the creation of a new booking. It accepts a single argument, **data**, which should contain all the necessary information required to define the booking (the exact structure of this data is determined by the underlying implementation of the booking system). Inside the function, the provided **data** is passed directly to **create_booking_slot**, which performs the actual booking‑slot creation and returns its result. In summary, **create_booking** offers a concise, high‑level interface for creating bookings by delegating the work to **create_booking_slot**.

### `def get_booking(name)`
<!-- 95e0c26c081b677e3d9f2c392b23bebc291741eb919ff8c070c84c9a4157ee5e -->
The get_booking function retrieves a specific booking document from the database. It takes one parameter, name, which is the unique identifier of the booking to be retrieved. The function uses the frappe framework to fetch the booking document with the specified name and returns it as a document object.

### `def update_booking(name, data)`
<!-- 3d32b21ff2f77cb9ff098bfa6f648a5c64d096ea9694fde7e01b1a82a4294fc7 -->
The update_booking function is used to modify an existing booking. It takes two parameters: name and data. The name parameter represents the identifier of the booking to be updated, while the data parameter contains the new information to be applied to the booking. This function serves as a wrapper around the update_booking_slot function, which performs the actual update operation.

### `def delete_booking(name)`
<!-- c5b9dc06b26930212b848ef8e6085c8255afecac5f4581fccf0a41aede7e5b35 -->
The delete_booking function is used to cancel a booking by removing the associated booking slot. It takes one parameter, name, which represents the name of the booking to be deleted. This function serves as a wrapper around the delete_booking_slot function, providing a simplified interface for deleting bookings.

### `def create_user_booking(data)`
<!-- 2a539f0467745d98c55c49b47abd72f6489bdf3140132a47f2a8a5667b48e848 -->
The create_user_booking function is used to generate a new user booking by creating a reservation. It takes one parameter, data, which is expected to contain all necessary information required to create the booking, such as user details and reservation specifics. This function essentially serves as a wrapper around the create_reservation function, passing the provided data to it to complete the booking process.

### `def get_user_bookings()`
<!-- d1f87fae5cd9035be7d69bc56bcc111c83b034bbc93f49a9866ad8f547153154 -->
The get_user_bookings function retrieves a list of bookings associated with the current user. It takes no parameters, relying on internal state to determine the user's identity. The function serves as a wrapper around the get_my_reservations function, providing a simplified interface for accessing user-specific booking data.

### `def update_user_booking_status(name, status)`
<!-- bc3595a073e8f264038a4ef0de71bdd428eb38af834e62502486d64725447231 -->
The update_user_booking_status function updates the status of a user's booking in the system. It takes two parameters: name, which represents the name of the user whose booking status is to be updated, and status, which represents the new status to be assigned to the user's booking. This function serves as a wrapper around the update_reservation_status function, providing a more specific and user-centric interface for managing booking statuses.

### `def get_shop_bookings(shop_id, status=None, date_from=None, date_to=None)`
<!-- a4965eb12c676eae7308d4abefd6ba9af7bc07a3593bf804ed85bd7f0641cea1 -->
The get_shop_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their current status, while date_from and date_to allow for filtering by a specific date range. If these optional parameters are not provided, the function will return all bookings for the specified shop.

### `def get_shop_user_bookings(shop_id, status=None, date_from=None, date_to=None)`
<!-- d41faa3fe3fe78df875c2234ec49f534fb4398a45ca1df99981b015c8123c5b8 -->
The get_shop_user_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their status, while date_from and date_to filter bookings by a specific date range. The function leverages the get_shop_reservations function to fetch the relevant data, providing a simplified interface for accessing shop user bookings.

### `def update_shop_user_booking_status(name, status)`
<!-- e8bca7752e24cc125c85110ad13f350f575525c0a0a0855883eac01ef945617d -->
The update_shop_user_booking_status function updates the status of a user's booking at a shop. It takes two parameters: name, which represents the name of the user or booking to be updated, and status, which represents the new status to be applied to the booking. This function serves as a wrapper around the update_reservation_status function, providing a shop-specific interface for managing user bookings.

### `def get_my_bookings()`
<!-- 549b1bb91c1b055419012afcfb07eb405be288f290cc1ea22cb1f90522645982 -->
The get_my_bookings function retrieves a list of bookings associated with the current user. This function takes no parameters and returns the result of the get_my_reservations function, effectively serving as an alias for retrieving user-specific reservation data.

### `def cancel_my_booking(name)`
<!-- 9bc4fe3bd229d0e34462a78a0fdf97872e10adf1bdf7d3ac2ba5d13114db43e2 -->
The cancel_my_booking function is used to cancel an existing booking by updating its reservation status. It takes one parameter, name, which represents the name associated with the booking to be cancelled. This function internally calls the update_reservation_status function, passing the provided name and the status "Cancelled" to effect the cancellation.
