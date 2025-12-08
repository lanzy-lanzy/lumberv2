# Inventory Report PDF Export Feature

## Overview

This feature allows users to export comprehensive inventory reports as PDF files using ReportLab. The reports are fully customizable and include multiple types of analysis.

## Supported Report Types

### 1. **Overview Report**
- Summary statistics (Total Products, Total Stock, Total Board Feet, Total Value)
- Stock distribution by category with detailed breakdown
- Recent stock transactions (last 15 transactions)

### 2. **Stock Levels Report**
- Complete inventory of all products
- Organized by product name with category and SKU information
- Stock status indicators (Out of Stock, Low Stock, In Stock)
- Shows quantity in pieces and board feet

### 3. **Low Stock Alert Report**
- Lists all products below stock thresholds
- Threshold: < 100 pieces OR < 500 board feet
- Urgency indicators (CRITICAL, HIGH, MEDIUM)
- Helps prioritize reordering

### 4. **Stock Value Report**
- Total inventory value breakdown by category
- Percentage of total value per category
- Top 15 products ranked by value
- Perfect for financial analysis and budgeting

### 5. **Transactions Report**
- Complete transaction history with summary statistics
- Shows Stock In, Stock Out, and Adjustment transaction counts
- Detailed table of 100 most recent transactions
- Includes date, time, product, type, quantity, board feet, reference, and user
- Perfect for audit trails and reconciliation

### 6. **Turnover Report**
- Inventory turnover analysis for last 30 days
- Top 20 fast-moving products
- Average daily sales calculations
- Turnover status indicators (Fast Moving, Good, Slow)
- Helps identify sales trends and stock optimization needs

## Usage

### From the Web Interface

1. Navigate to **Reports** → **Inventory Reports**
2. Select the desired report tab (Overview, Stock Levels, Low Stock, or Stock Value)
3. Click the **"Export to PDF"** button in the top-right corner
4. The PDF will automatically download to your computer

### File Naming

PDFs are automatically named with the format:
```
inventory_report_{report_type}_{YYYYMMDD_HHMMSS}.pdf
```

Example: `inventory_report_overview_20241209_143025.pdf`

## Implementation Details

### Backend Files Modified

- **app_inventory/management_views.py**
  - New function: `export_inventory_report_pdf(request)`
  - Helper functions for each report type:
    - `_generate_overview_report()`
    - `_generate_stock_levels_report()`
    - `_generate_low_stock_report()`
    - `_generate_stock_value_report()`

- **app_inventory/management_urls.py**
  - New route: `/inventory/management/export/report-pdf/`

### Frontend Files Modified

- **templates/reports/inventory_reports.html**
  - Added "Export to PDF" button in the header
  - New JavaScript function: `exportReportPDF()`

## API Endpoint

### Export Inventory Report to PDF

**URL:** `/inventory/management/export/report-pdf/`

**Method:** GET

**Query Parameters:**
- `type` (string): Report type - `overview`, `stock_levels`, `low_stock`, `stock_value`, `transactions`, or `turnover`

**Examples:**
```
GET /inventory/management/export/report-pdf/?type=stock_value
GET /inventory/management/export/report-pdf/?type=transactions
GET /inventory/management/export/report-pdf/?type=turnover
```

**Response:**
- Content-Type: `application/pdf`
- Attachment with timestamp-based filename

## Dependencies

The implementation uses the following libraries (already installed):

- **ReportLab**: For PDF generation
  - `reportlab.lib.pagesizes`
  - `reportlab.platypus`
  - `reportlab.lib.styles`
  - `reportlab.lib.colors`

## Features

### Styling & Formatting

- **Professional Layout**: Landscape A4 pages for optimal table display
- **Color Coding**: 
  - Dark blue headers (#1e3a8a) for consistency
  - Red headers (#c41e3a) for critical low stock reports
  - Alternating row colors for readability
- **Typography**: Clear heading hierarchies and proper spacing
- **Tables**: Multi-column data with aligned columns and consistent formatting

### Data Aggregation

- Real-time calculations from database
- Summary statistics
- Category-level analysis
- Product-level detail
- Financial valuation

### Security

- Login required: `@login_required` decorator
- Role-based access: `@user_passes_test(is_admin_or_inventory_manager)`
- Only accessible to admin and inventory manager users

## Performance Considerations

- Reports query the database efficiently using `select_related()` and aggregations
- PDF generation is done in-memory using BytesIO buffer
- No file storage required - documents are generated on-demand

## Future Enhancements

Potential improvements for future versions:

1. **Email Delivery**: Send reports directly to email addresses
2. **Scheduled Reports**: Automatic PDF generation and delivery
3. **Custom Date Ranges**: Filter reports by specific date periods
4. **Charts & Graphs**: Add visual representations using ReportLab charts
5. **Multi-language Support**: Generate reports in different languages
6. **Batch Export**: Export multiple report types in a single download
7. **Branding**: Add company logo and custom headers/footers

## Troubleshooting

### PDF Not Downloading

- Ensure you're logged in with proper permissions (admin or inventory manager)
- Check browser download settings
- Try a different browser

### Incorrect Data in Report

- Click "Refresh" to reload latest data before exporting
- Verify that recent transactions have been saved to the database
- Check that product inventory levels are up to date

### Performance Issues

- For large databases with many products/transactions, initial load may take a few seconds
- Consider archiving old transactions if database is very large

## Support

For issues or feature requests related to the PDF export functionality:

1. Check this documentation
2. Review the console logs for JavaScript errors
3. Check Django logs for backend errors
4. Report issues with specific report data or formatting

## Version History

- **v1.0.0** (2024-12-09): Initial implementation
  - Four report types (Overview, Stock Levels, Low Stock, Stock Value)
  - ReportLab-based PDF generation
  - Web interface integration
  - Role-based access control
