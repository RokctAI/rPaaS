# API Reference: lending

Source file: `paas/api/lending/lending.py`

## Whitelisted API Endpoints

### `def check_loan_eligibility(id_number, amount, lang='en')`
Checks if a user is eligible for a loan.

### `def check_loan_history_eligibility(lang='en')`
Checks if a user is eligible for a loan based on their loan history.

### `def mark_application_as_rejected(financial_details, lang='en')`
Marks a loan application as rejected.

### `def check_financial_eligibility(monthly_income, grocery_expenses, other_expenses, existing_credits, lang='en')`
Checks if a user is financially eligible for a loan.

### `def save_incomplete_loan_application(financial_details, lang='en')`
Saves an incomplete loan application as a draft.

### `def fetch_saved_application(lang='en')`
Fetches a saved loan application.

### `def fetch_saved_applications(lang='en')`
Fetches all saved loan applications for the current user.

### `def create_loan_application(financial_details, lang='en')`
Creates a new loan application.

### `def disburse_loan(loan_id, lang='en')`
Disburses a loan.

### `def get_my_loan_applications(lang='en')`
Fetches all loan applications for the user.
