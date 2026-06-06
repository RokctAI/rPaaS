# API Reference: branch

Source file: `paas/api/branch/branch.py`

## Whitelisted API Endpoints

### `def get_branches(shop_id)`
<!-- 4b9bb9582d95866901b8ea8d44c4a4d1180924c79d413c876c9349cfb0c7fd54 -->
The get_branches function retrieves a list of branches associated with a specific shop. It takes one parameter, shop_id, which is a string representing the unique identifier of the shop. The function first checks if the provided shop_id exists in the database, throwing an error if it does not. If the shop exists, it queries the database for a list of branches linked to the shop, returning their names, addresses, and geographic coordinates.

### `def get_branch(branch_id)`
Retrieves a single branch.

### `def create_branch(branch_data)`
Creates a new branch.

### `def update_branch(branch_id, branch_data)`
Updates an existing branch.

### `def delete_branch(branch_id)`
Deletes a branch.
