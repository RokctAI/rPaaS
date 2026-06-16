# API Reference: seller_report

Source file: `paas/api/seller_report/seller_report.py`

## Whitelisted API Endpoints

### `def get_order_report(from_date=None, to_date=None)`
The get_order_report function generates a sales report for orders placed within a specified date range. It accepts two optional parameters: from_date and to_date, which represent the start and end dates of the reporting period, respectively. If either parameter is not provided, the function defaults to a date range of the last month, with from_date set to one month prior to the current date and to_date set to the current date. The function returns the sales report data for the specified period, obtained by calling the get_seller_sales_report function with the determined date range.
