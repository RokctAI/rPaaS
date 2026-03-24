import frappe


@frappe.whitelist(allow_guest=True)
def get_parcel_options():
    """
    Retrieves a list of all active Parcel Options.
    """
    try:
        options = frappe.get_list(
            "Parcel Option",
            filters={"active": 1},
            fields=["name", "title", "description", "price"],
            order_by="price asc",
        )
        return options
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_parcel_options Error")
        frappe.throw(f"An error occurred while fetching parcel options: {
            str(e)}")


@frappe.whitelist()
def create_parcel_option(option_data):
    """
    Creates a new Parcel Option.
    """
    try:
        if isinstance(option_data, str):
            option_data = frappe.parse_json(option_data)

        doc = frappe.get_doc({"doctype": "Parcel Option", **option_data})
        doc.insert()
        return doc.as_dict()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_parcel_option Error")
        frappe.throw(f"An error occurred while creating parcel option: {
            str(e)}")


@frappe.whitelist()
def update_parcel_option(name, option_data):
    """
    Updates an existing Parcel Option.
    """
    try:
        if isinstance(option_data, str):
            option_data = frappe.parse_json(option_data)

        doc = frappe.get_doc("Parcel Option", name)
        doc.update(option_data)
        doc.save()
        return doc.as_dict()
    except frappe.DoesNotExistError:
        frappe.throw("Parcel Option not found", frappe.DoesNotExistError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_parcel_option Error")
        frappe.throw(f"An error occurred while updating parcel option: {
            str(e)}")


@frappe.whitelist()
def delete_parcel_option(name):
    """
    Deletes a Parcel Option.
    """
    try:
        frappe.delete_doc("Parcel Option", name)
        return {
            "status": "success",
            "message": "Parcel Option deleted successfully",
        }
    except frappe.DoesNotExistError:
        frappe.throw("Parcel Option not found", frappe.DoesNotExistError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "delete_parcel_option Error")
        frappe.throw(f"An error occurred while deleting parcel option: {
            str(e)}")
