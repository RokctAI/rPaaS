# API Reference: driver_report

Source file: `paas/api/driver_report/driver_report.py`

## Whitelisted API Endpoints

### `def get_order_report(from_date=None, to_date=None)`
<!-- 399768ea9ca26b909b90e2b40f6f13cb81c4e1ea3f95433737e1cd9e5f3383d2 -->
The get_order_report function generates a report of orders within a specified date range. It accepts two optional parameters: from_date and to_date, which represent the start and end dates of the report period, respectively. If either parameter is not provided, the function defaults to a date range of the last month, with from_date set to one month prior to the current date and to_date set to the current date. The function returns the generated report.
