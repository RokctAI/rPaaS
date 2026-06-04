# API Reference: admin_reports

Source file: `paas/api/admin_reports/admin_reports.py`

## Whitelisted API Endpoints

### `def get_admin_statistics()`
<!-- 5271b6792a7b7da473729f9e46642d754912fb1bcf40bbeeaead92aa840b269d -->
The get_admin_statistics function retrieves detailed statistics for the admin dashboard, including cards and charts. This function does not take any parameters. It returns a dictionary containing two main sections: cards and charts. The cards section provides an overview of key metrics such as total users, shops, orders, sales, and product reviews. The charts section includes data for visualizing orders per day, new users per day, new shops per day, and order status breakdown over the last 30 days. The function requires admin privileges to execute.

### `def get_multi_company_sales_report(from_date, to_date, company=None)`
<!-- 4fdbd554eaea2d49507d5a132bc259f01ac03b529db419c0091c07501bf1b79f -->
The get_multi_company_sales_report function generates a sales report for a specified date range, allowing administrators to retrieve data for a single company or all companies. The function takes three parameters: from_date and to_date, which define the date range for the report, and an optional company parameter, which filters the results to a specific company if provided. If the company parameter is not specified, the function returns data for all companies. The report includes order details such as name, shop, user, grand total, status, and creation date, as well as calculated commission amounts based on the sales commission rate for each company.

### `def get_admin_report(doctype, fields, filters=None, limit_start=0, limit_page_length=20)`
Retrieves a report for a specified doctype with given fields and filters (for admins).

### `def get_all_wallet_histories(limit_start=0, limit_page_length=20)`
Retrieves a list of all wallet histories on the platform (for admins).

### `def get_all_transactions(limit_start=0, limit_page_length=20)`
Retrieves a list of all transactions on the platform (for admins).

### `def get_all_seller_payouts(limit_start=0, limit_page_length=20)`
Retrieves a list of all seller payouts on the platform (for admins).

### `def get_all_shop_bonuses(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop bonuses on the platform (for admins).
