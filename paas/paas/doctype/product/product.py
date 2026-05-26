# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

from frappe.model.document import Document
import frappe


class Product(Document):
    pass


def auto_vectorize_product(doc, method=None):
    """
    Hooks into Item (Product) on_save/after_insert to generate embeddings via Brain.
    """
    # Only vectorize if there is meaningful content
    if not (doc.item_name or doc.description):
        return

    try:
        # Check if Brain is installed and accessible
        from brain.services.llm_service import embed_text

        # Construct context for embedding
        # We want to capture: Name, Group, Description, Shop
        # "Pizza Margherita (Food) - Delicious cheese pizza"
        text = f"{doc.item_name} ({doc.item_group})"
        if doc.description:
            text += f"\n{doc.description}"
        if hasattr(doc, "shop") and doc.shop:
            text += f"\nShop: {doc.shop}"

        vector = embed_text(text)

        if vector:
            # Direct SQL update to avoid recursive triggers or permission
            # issues
            frappe.db.sql(
                f"""
                UPDATE "tabItem"
                SET embedding = '{vector}'
                WHERE name = %s
            """,
                (doc.name,),
            )
            # We don't commit here, we let the transaction handler do it

    except ImportError:
        # Brain app not installed or service not available
        pass
    except Exception as e:
        # Log but don't break the save
        frappe.log_error(f"PaaS: Auto-vectorization failed for {doc.name}: {e}")
