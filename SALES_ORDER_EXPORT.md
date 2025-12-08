# Sales Orders Export Feature

Complete PDF export functionality for sales orders with custom date filters, preview, and multiple export formats.

## Features

### 1. Filter & Export Interface
- **Search**: Search by SO number or customer name
- **Payment Type Filter**: Cash, Partial Payment, or Credit (SOA)
- **Date Range**: Custom date filters (From Date and To Date)
- **Real-time Filtering**: All filters work together
- **Export Button**: One-click access to export preview

### 2. Export Preview Page
A comprehensive preview page before PDF export that shows:

#### Summary Statistics
- Total number of orders
- Total sales amount (₱)
- Total discounts applied (₱)
- Total amount paid (₱)
- Pending balance (₱)

#### Payment Type Summary
- Breakdown by Cash, Partial Payment, and Credit
- Count and total amount for each type

#### Data Preview Table
- SO Number
- Customer Name
- Number of Items
- Order Amount
- Discount Applied
- Amount Paid
- Outstanding Balance
- Payment Type Badge
- Order Date

**URL**: `/sales/orders/export/preview/?[filters]`

### 3. PDF Export Formats

#### Summary Report PDF
- **Format**: Landscape A4
- **Content**: Table view of all filtered orders
- **Best for**: Quick overview, multiple orders, printing
- **Features**:
  - Summary statistics at top
  - Professional table layout
  - Alternating row colors
  - Up to 200 orders per PDF
  - Compact format

**URL**: `/sales/orders/export/pdf/?format=summary&[filters]`

#### Detailed Report PDF
- **Format**: Portrait Letter
- **Content**: Individual order details with items
- **Best for**: Accounting, customer records, detailed analysis
- **Features**:
  - Full customer information
  - Complete item breakdown per order
  - Order summary with discount details
  - Notes and payment type
  - Page break between orders
  - Up to 50 orders per PDF (for size control)

**URL**: `/sales/orders/export/pdf/?format=detailed&[filters]`

## Usage Workflow

### Step 1: Navigate to Sales Orders
Go to `Inventory → Sales Orders` or `/sales/orders/`

### Step 2: Apply Filters (Optional)
- Enter search term (SO number or customer name)
- Select payment type filter
- Set date range with From Date and To Date
- Click any filter to update results

### Step 3: Click Export Button
Click the red "Export" button in the header
The button becomes available as soon as filters are set

### Step 4: Review Preview
You'll see:
- Applied filters summary
- Overall statistics
- Payment type breakdown
- Table preview of data to be exported
- Export format options

### Step 5: Download PDF
Choose one of two formats:

**Summary Report**
- Quick overview table format
- Good for printing lists
- Landscape orientation

**Detailed Report**
- Full order details
- Customer information included
- One order per page (approximately)
- Portrait orientation

Click the desired format to download

## Filter Parameters

All filters are optional and can be combined:

| Parameter | Type | Example |
|-----------|------|---------|
| `search` | String | "SO-2024-001" or "John Doe" |
| `payment_type` | Choice | "cash", "partial", or "credit" |
| `date_from` | Date | "2024-12-01" |
| `date_to` | Date | "2024-12-31" |
| `format` | Choice | "summary" or "detailed" |

### Example URLs

**All orders in December:**
```
/sales/orders/export/pdf/?date_from=2024-12-01&date_to=2024-12-31
```

**Cash sales in December (detailed):**
```
/sales/orders/export/pdf/?date_from=2024-12-01&date_to=2024-12-31&payment_type=cash&format=detailed
```

**Customer "John Doe" orders:**
```
/sales/orders/export/pdf/?search=John+Doe
```

## Data Included in Export

### Summary Report Columns
- SO Number
- Customer Name
- Number of Items
- Total Amount (₱)
- Discount Applied (₱)
- Amount Paid (₱)
- Outstanding Balance (₱)
- Payment Type
- Order Date

### Detailed Report Sections

**Order Header**
- SO Number and Date
- Customer Name, Phone, Email
- Customer Address

**Order Items Table**
- Product Name
- Quantity (pieces)
- Unit Price (₱)
- Board Feet
- Line Subtotal (₱)

**Order Summary**
- Total Amount
- Discount (20% if applicable)
- Amount Paid
- Outstanding Balance
- Payment Type

**Additional**
- Order Notes (if any)
- Created By User
- Creation Timestamp

## PDF Features

### Professional Styling
- Header with title and generation timestamp
- Blue color scheme matching system
- Bordered tables with alternating row colors
- Proper column alignment (text left, numbers right)
- Clear section headings

### Pagination
- Summary: Up to 200 orders
- Detailed: Up to 50 orders (one order per ~0.5 pages)
- Automatic page breaks for detailed format

### File Naming
```
sales_orders_YYYYMMDD_HHMMSS.pdf
```
Example: `sales_orders_20241209_143522.pdf`

## Technical Implementation

### Files Created/Modified

#### New Files
- `app_sales/sales_pdf_views.py` - PDF generation views
- `templates/sales/export_preview.html` - Preview page template

#### Modified Files
- `templates/sales/sales_orders.html` - Added Export button and function
- `core/urls.py` - Added URL routes for export

### URL Routes
```
/sales/orders/export/preview/          → Preview page with filters
/sales/orders/export/pdf/              → PDF download (summary default)
```

### URL Parameters
```
?search=TERM                 Search by SO number or customer
?payment_type=cash|partial|credit   Filter by payment type
?date_from=YYYY-MM-DD       Start date
?date_to=YYYY-MM-DD         End date
?format=summary|detailed    PDF format (default: summary)
```

## Dependencies

- ReportLab 4.0+ (already installed)
- Django QuerySet filtering
- datetime for date handling
- BytesIO for PDF buffer

## Browser Compatibility

- Chrome/Chromium: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Edge: ✅ Full support
- IE: ❌ Not supported

## Error Handling

- Invalid date format → Shows all records
- No matching filters → Empty table in preview
- Export timeout → Browser will retry
- PDF generation error → Error page displayed

## Performance Considerations

- Summary format: Handles 200+ orders efficiently
- Detailed format: Limited to 50 orders to control PDF size
- Preview: Shows up to 100 orders
- Large datasets: Consider using date range filters

## Tips for Best Results

1. **Use Date Range**: Narrow date range = faster processing
2. **Combine Filters**: Use multiple filters for targeted exports
3. **Summary for Lists**: Use summary format for multiple orders
4. **Detailed for Records**: Use detailed format for customer files
5. **Print Landscape**: Summary format prints better in landscape
6. **Archive PDFs**: Save PDFs for record keeping

## Security

- Requires user authentication
- Uses Django CSRF protection
- Filters based on user access
- All date inputs validated
- SQL injection protection via ORM

## Future Enhancements

- [ ] CSV export option
- [ ] Email export functionality
- [ ] Scheduled exports
- [ ] Export templates (custom branding)
- [ ] Batch export multiple formats
- [ ] Export history/logs
- [ ] Watermark support
- [ ] Digital signature integration

## Troubleshooting

### Export button not showing
- Ensure you're logged in as admin or sales staff
- Clear browser cache
- Refresh the page

### Preview page is blank
- Check filters are correctly set
- Ensure there are matching orders in database
- Check date format (YYYY-MM-DD)

### PDF downloads but won't open
- Check file isn't corrupted (try different reader)
- Ensure PDF viewer is installed
- Try downloading again

### PDF is too large
- Use date range to limit records
- Use summary format instead of detailed
- Filter by payment type or customer

## Support

For issues with sales order export:
1. Check the filter settings
2. Review the preview data
3. Ensure PDF viewer compatibility
4. Contact system administrator if problems persist
