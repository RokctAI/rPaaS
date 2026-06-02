# API Reference: blog

Source file: `paas/api/blog/blog.py`

## Whitelisted API Endpoints

### `def create_blog(data)`
Creates a new Blog post.

### `def get_blogs(type=None, limit=10, start=0)`
Retrieves Blogs, optionally filtered by type.

### `def get_blog_details(name)`
Retrieves full details of a Blog post.

### `def update_blog(name, data)`
Updates a Blog post.

### `def delete_blog(name)`
Deletes a Blog post.

### `def get_admin_blogs(page=1, limit=10, lang='en')`
Retrieves all Blogs for Admin (including inactive).

### `def create_admin_blog(data)`
Alias for create_blog (Admin usage).

### `def update_admin_blog(name, data)`
Alias for update_blog (Admin usage).

### `def delete_admin_blog(name)`
Alias for delete_blog (Admin usage).

### `def get_blog(name)`
Alias for get_blog_details.
