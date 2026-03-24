import frappe
import json


@frappe.whitelist()
def check_loan_eligibility(id_number: str, amount: float, lang: str = "en"):
    """
    Checks if a user is eligible for a loan.
    """
    # This is a placeholder for the actual scorecard logic.
    is_eligible = True
    loan_eligibility_check = frappe.get_doc(
        {
            "doctype": "Loan Eligibility Check",
            "id_number": id_number,
            "amount": amount,
            "is_eligible": is_eligible,
        }
    )
    loan_eligibility_check.insert(ignore_permissions=True)
    return {"is_eligible": is_eligible}


@frappe.whitelist()
def check_loan_history_eligibility(lang: str = "en"):
    """
    Checks if a user is eligible for a loan based on their loan history.
    """
    # This is a placeholder for the actual scorecard logic.
    return {"has_disqualifying_history": False}


@frappe.whitelist()
def mark_application_as_rejected(financial_details: dict, lang: str = "en"):
    """
    Marks a loan application as rejected.
    """
    # This is a placeholder for the actual scorecard logic.
    return {"status": "success"}


@frappe.whitelist()
def check_financial_eligibility(
    monthly_income: float,
    grocery_expenses: float,
    other_expenses: float,
    existing_credits: float,
    lang: str = "en",
):
    """
    Checks if a user is financially eligible for a loan.
    """
    # This is a placeholder for the actual scorecard logic.
    return {"is_eligible": True}


@frappe.whitelist()
def save_incomplete_loan_application(
    financial_details: dict, lang: str = "en"
):
    """
    Saves an incomplete loan application as a draft.
    """
    loan_application = frappe.get_doc(
        {
            "doctype": "Loan Application",
            "status": "Draft",
            # ... save other details from financial_details ...
        }
    )
    loan_application.insert(ignore_permissions=True)
    return {"name": loan_application.name}


@frappe.whitelist()
def fetch_saved_application(lang: str = "en"):
    """
    Fetches a saved loan application.
    """
    user = frappe.session.user
    loan_application = frappe.get_list(
        "Loan Application",
        filters={"customer": user, "status": "Draft"},
        limit=1,
    )
    if loan_application:
        return frappe.get_doc("Loan Application", loan_application[0].name)
    return {}


@frappe.whitelist()
def fetch_saved_applications(lang: str = "en"):
    """
    Fetches all saved loan applications for the current user.
    """
    user = frappe.session.user
    loan_applications = frappe.get_list(
        "Loan Application",
        filters={"customer": user, "status": "Draft"},
    )
    return loan_applications


@frappe.whitelist()
def create_loan_application(financial_details: dict, lang: str = "en"):
    """
    Creates a new loan application.
    """
    loan_application = frappe.get_doc(
        {
            "doctype": "Loan Application",
            "status": "Submitted",
            # Map fields
        }
    )
    loan_application.insert(ignore_permissions=True)
    return {"name": loan_application.name}


@frappe.whitelist()
def disburse_loan(loan_id: str, lang: str = "en"):
    """
    Disburses a loan.
    """
    return {"status": "success", "message": "Loan disbursed."}


@frappe.whitelist()
def get_my_loan_applications(lang: str = "en"):
    """
    Fetches all loan applications for the user.
    """
    user = frappe.session.user
    return frappe.get_list("Loan Application", filters={"customer": user})
