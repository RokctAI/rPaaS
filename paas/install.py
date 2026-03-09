import frappe
import os
from frappe.utils import get_bench_path


def check_site_role():
    """
    Checks the site role before PaaS installation.
    PaaS can be installed on both tenant and control sites:
    - Tenant sites: Full PaaS functionality with seeders
    - Control sites: For Swagger documentation (no seeders)
    """
    app_role = frappe.conf.get("app_role", "tenant")
    print(
        f"PaaS installation on site: {
            frappe.local.site} (app_role: {app_role})")


def after_install():
    """
    Wrapper to run all post-installation tasks.
    """
    setup_gin_indexes()
    setup_vector_extension()
    setup_geospatial_extensions()
    setup_product_vector_column()
    run_seeders()
    check_and_fetch_sources()


def setup_geospatial_extensions():
    """
    Enables cube and earthdistance extensions for geospatial queries.
    """
    try:
        frappe.db.sql("CREATE EXTENSION IF NOT EXISTS cube")
        frappe.db.sql("CREATE EXTENSION IF NOT EXISTS earthdistance")
        return True
    except Exception as e:
        frappe.db.rollback()
        print(f"⚠️ Failed to enable geospatial extensions: {e}")
        return False


def setup_vector_extension():
    """
    Enables the pgvector extension if not already enabled.
    """
    try:
        frappe.db.sql("CREATE EXTENSION IF NOT EXISTS vector")
        return True
    except Exception as e:
        frappe.db.rollback()
        print(f"⚠️ Failed to enable pgvector: {e}")
        return False


def setup_product_vector_column():
    """
    Adds a vector(384) column to the Product table for semantic search.
    """
    if not setup_vector_extension():
        print("⚠️ Skipping Product vector column creation due to missing extension.")
        return

    try:
        # Check if table exists
        if not frappe.db.table_exists("Item"):
            print("🛍️ Item table does not exist. Skipping vector column setup.")
            return

        # Check if column exists using standard API
        if not frappe.db.has_column("Item", "embedding"):
            print("🛍️ Adding 'embedding' vector column to Product (Item)...")

            # Note: DDL statements (ALTER TABLE, CREATE INDEX) require raw SQL.
            # frappe.qb is primarily for Data Manipulation (SELECT, INSERT,
            # UPDATE).
            frappe.db.sql(
                "ALTER TABLE \"tabItem\" ADD COLUMN embedding vector(384)")

            # Add an HNSW index for fast approximate nearest neighbor search
            print("🛍️ Creating HNSW index for Product embeddings...")
            frappe.db.sql("""
                CREATE INDEX ON \"tabItem\" USING hnsw (embedding vector_l2_ops)
            """)

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Failed to setup Product vector column: {e}")
        print(f"⚠️ Failed to setup vector column: {e}")


def setup_gin_indexes():
    """
    Creates GIN indexes for JSONB fields and FTS columns in PostgreSQL.
    Intended for fresh installs.
    """
    # JSONB GIN Indexes
    create_gin_index("tabRemote Config", "poi_data")
    create_gin_index("tabRemote Config", "quick_sale_no_user_stock_ids")
    create_gin_index("tabRemote Config", "mega_char_maintenance_durations")
    create_gin_index("tabRemote Config", "softener_maintenance_durations")
    create_gin_index("tabRemote Config", "maintenance_types")
    create_gin_index("tabRemote Config", "filter_types")

    create_gin_index("tabRequest Model", "data")
    create_gin_index("tabPayment Payload", "payload")

    # WhatsApp GIN Indexes
    create_gin_index("tabWhatsApp Session", "cart_items")
    # Check if metadata column exists before indexing (handle missing table
    # gracefully)
    try:
        if frappe.db.has_column("tabWhatsApp Session", "metadata"):
            create_gin_index("tabWhatsApp Session", "metadata")
    except Exception:
        # Table might not exist yet or other DB error - ignore
        pass

    # FTS Indexes
    create_fts_index("tabItem", "item_name")
    create_fts_index("tabShop", "shop_name")
    create_fts_index("tabCategory", "keywords")

    create_fts_index("tabUser", "first_name")
    create_fts_index("tabUser", "last_name")
    create_fts_index("tabUser", "email")
    create_fts_index("tabUser", "phone")


def create_gin_index(table, column):
    try:
        # Sanitize table name for index (remove 'tab', replace spaces with
        # underscores)
        clean_table = table.lower().replace('tab', '').replace(' ', '_')
        index_name = f"{clean_table}_{column}_gin_idx"

        # Check if table exists in information_schema to prevent "relation does
        # not exist" errors
        table_exists = frappe.db.sql(
            f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'",
            pluck=True)
        if not table_exists:
            print(
                f"ℹ️ Table {table} does not exist yet. Skipping index {index_name}.")
            return

        chk = frappe.db.sql(
            f"SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}'",
            pluck=True)
        if not chk:
            # Try catch GIN index creation
            # If column is json (text), cast to jsonb for indexing support
            frappe.db.sql(
                f"CREATE INDEX {index_name} ON \"{table}\" USING GIN (({column}::jsonb))")
    except Exception as e:
        frappe.db.rollback()
        # Log purely as warning, don't crash install
        print(f"⚠️ Failed to create GIN index {index_name}: {str(e)}")


def create_fts_index(table, column):
    try:
        # Check if table exists
        table_exists = frappe.db.sql(
            f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'",
            pluck=True)
        if not table_exists:
            print(
                f"ℹ️ Table {table} does not exist yet. Skipping FTS index {index_name}.")
            return

        chk = frappe.db.sql(
            f"SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}'",
            pluck=True)
        if not chk:
            frappe.db.sql(
                f"CREATE INDEX {index_name} ON \"{table}\" USING GIN (to_tsvector('english', {column}))")
    except Exception as e:
        frappe.db.rollback()
        print(f"⚠️ Failed to create FTS index {index_name}: {str(e)}")


def run_seeders():
    """
    Runs sensitive seeders from control app if available.
    Only runs on tenant sites - control sites skip seeding.
    """
    app_role = frappe.conf.get("app_role", "tenant")

    if app_role == "control":
        print("Skipping PaaS seeders on control site (Swagger documentation only).")
        return

    # Only seed on tenant sites
    try:
        # Dynamic loading to avoid strict module dependency (prevents install
        # crashes)
        def run_seeder_script(script_name):
            try:
                # Path: apps/control/control/seeds/scripts/{script_name}.py
                script_path = os.path.join(
                    get_bench_path(),
                    "apps",
                    "control",
                    "control",
                    "seeds",
                    "scripts",
                    f"{script_name}.py")

                if not os.path.exists(script_path):
                    print(f"Seeder script not found: {script_path}")
                    return

                print(f"Running {script_name} from {script_path}...")
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    script_name, script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.execute()
            except Exception as e:
                print(f"Failed to run {script_name}: {e}")

        # Execute
        run_seeder_script("seed_paas_payments")
        run_seeder_script("seed_paas_juvo_settings")

        # Run main PaaS seeder (handles global data + conditional Juvo data)
        print("Running main PaaS seeder...")
        from paas import seed
        seed.execute()

        print("PaaS seeders completed successfully.")
    except ImportError:
        # Seeders not available (control app doesn't have them or not
        # installed)
        print("Control seeders not found. Skipping sensitive data seeding.")
    except Exception as e:
        print(f"Error running PaaS seeders: {e}")
        frappe.log_error(
            f"Error running PaaS seeders: {e}",
            "PaaS Seeder Error")


def check_and_fetch_sources():
    """
    Checks if Flutter source code exists. If not, requests Control to fetch it.
    """
    print("--- Checking for Flutter Source Code ---")

    # Path: paas/builder/source_code
    source_code_path = frappe.get_app_path("paas", "builder", "source_code")

    # Check if directory exists and has content (ignoring .keep)
    missing = True
    if os.path.exists(source_code_path):
        contents = [c for c in os.listdir(source_code_path) if c != ".keep"]
        if contents:
            missing = False
            print(f"✅ PaaS Source Code detected: {contents}")

    if missing:
        print(f"⚠️ PaaS Flutter Source Code missing in {source_code_path}.")
        print("Requesting Control app to fetch sources...")
        try:
            if "control" in frappe.get_installed_apps():
                # Dynamically call the function in Control app
                # Note: This function (control.control.api.fetch_paas_sources)
                # must exist in Control
                try:
                    fetch_sources = frappe.get_attr(
                        "control.control.api.fetch_paas_sources")
                    fetch_sources()
                    print("✅ Successfully requested Control to fetch sources.")
                except AttributeError:
                    print(
                        "❌ Error: 'control.control.api.fetch_paas_sources' method not found.")
                    print("Please ensure Control app is updated.")
                except Exception as ex:
                    print(f"❌ Error during fetch request: {ex}")
            else:
                print("ℹ️ Control app is not installed. Cannot auto-fetch sources.")
                print(
                    "Please manually clone sources into: " +
                    source_code_path)
        except Exception as e:
            print(f"❌ Error initiating source check: {e}")
