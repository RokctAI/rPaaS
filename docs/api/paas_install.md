# API Reference: install

Source file: `paas/install.py`

## Documented Module Functions

### `def check_site_role()`
Checks the site role before PaaS installation.
PaaS can be installed on both tenant and control sites:
- Tenant sites: Full PaaS functionality with seeders
- Control sites: For Swagger documentation (no seeders)

### `def after_install()`
Wrapper to run all post-installation tasks.

### `def setup_geospatial_extensions()`
Enables cube and earthdistance extensions for geospatial queries.
bypass_sql

### `def setup_vector_extension()`
Enables the pgvector extension if not already enabled.
bypass_sql

### `def setup_product_vector_column()`
Adds a vector(384) column to the Product table for semantic search.
bypass_sql

### `def setup_gin_indexes()`
Creates GIN indexes for JSONB fields and FTS columns in PostgreSQL.
Intended for fresh installs.

### `def create_gin_index(table, column)`
Creates GIN indexes for JSONB fields and FTS columns.
bypass_sql

### `def create_fts_index(table, column)`
Creates FTS indexes on PostgreSQL.
bypass_sql

### `def run_seeders()`
Runs sensitive seeders from control app if available.
Only runs on tenant sites - control sites skip seeding.

### `def check_and_fetch_sources()`
Checks if Flutter source code exists. If not, requests Control to fetch it.
