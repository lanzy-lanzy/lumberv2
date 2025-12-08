# Inventory Management - Quick Start Guide

## Getting Started

### 1. Access the Dashboard
- **URL**: http://localhost:8000/inventory/management/
- **Requirements**: Must be logged in as admin or inventory_manager
- **From Sidebar**: Click "Inventory" → "Management"

### 2. Set Up Categories
Navigate to: `/inventory/management/categories/`

1. Click "Add Category"
2. Enter category name (e.g., "Softwood", "Hardwood")
3. Add description (optional)
4. Click "Save"

### 3. Create Products
Navigate to: `/inventory/management/products/`

1. Click "Add Product"
2. Fill in product details:
   - Product Name: e.g., "2x4 White Pine"
   - Category: Select from dropdown
   - SKU: Unique identifier (e.g., "WP-2x4-10")
   - Thickness: 2 inches
   - Width: 4 inches
   - Length: 10 feet
   - Price per Board Foot: $3.50
   - Price per Piece: $14.00 (optional)
3. Click "Save"

### 4. Record Stock In
Navigate to: `/inventory/management/stock-in/`

1. Select product from dropdown
2. Enter quantity in pieces (e.g., 50)
3. Enter cost per unit (optional)
4. Enter reference ID/PO number (optional)
5. Click "Record Stock In"
6. View recorded transactions below

### 5. Record Stock Out
Navigate to: `/inventory/management/stock-out/`

1. Select product from dropdown
   - Current stock will display automatically
2. Enter quantity to remove
3. Select reason (Sales, Damaged, Lost, Return, Other)
4. Enter reference ID (SO number, RMA, etc.) (optional)
5. Click "Record Stock Out"

### 6. Check Inventory Levels
Navigate to: `/inventory/management/inventory-levels/`

- View all products and current stock
- Filter by category or search by name/SKU
- Red badge = Low stock alert
- Green badge = Normal stock
- Export to PDF with one click

### 7. View Transaction History
Navigate to: `/inventory/management/transaction-history/`

- Filter by type (Stock In, Stock Out, Adjustment)
- Filter by specific product
- Filter by date range
- See who made each transaction
- Export to PDF with one click

## Export Reports

### Available PDF Exports

From the Dashboard (`/inventory/management/`):

1. **Inventory Levels PDF** → Complete current inventory list
2. **Stock Transactions PDF** → All transactions (filterable)
3. **Products Catalog PDF** → All product specs and pricing
4. **Categories Summary PDF** → Inventory totals by category

All exports include:
- Generation timestamp
- Professional formatting
- Table with proper styling
- Landscape orientation for readability

## Dashboard Widgets

### Statistics
- **Total Products**: Active products in system
- **Total Categories**: Number of categories
- **Total Pieces**: Sum of all inventory pieces
- **Total Board Feet**: Sum of all inventory board feet

### Quick Actions
- Manage Categories
- Manage Products
- Record Stock In
- Record Stock Out
- View Inventory Levels
- View Transaction History

### Alerts
- **Low Stock**: Products below 100 pieces or 500 BF
- **7-Day Summary**: Recent transaction counts

### Recent Transactions
- Last 10 transactions
- Date, product, type, quantity, board feet, user

## Common Tasks

### Add New Product Category
```
Inventory → Management → Categories → Add Category
```

### Add New Product to Category
```
Inventory → Management → Products → Add Product
```

### Receive Purchase Order
```
Inventory → Management → Stock In
- Select product
- Enter quantity received
- Enter PO reference number
```

### Process Sales Order
```
Inventory → Management → Stock Out
- Select product
- Enter quantity sold
- Select "Sales" as reason
- Enter SO reference number
```

### Check Low Stock Items
```
Inventory → Management → Dashboard
→ Look for "Low Stock Alerts" section
→ Or go to Inventory Levels to see full list with filter
```

### Generate Inventory Report
```
Inventory → Management → Dashboard
→ Click "Inventory Levels PDF"
→ File downloads automatically
```

## Tips & Best Practices

1. **Reference IDs**: Always include PO/SO numbers for tracking
2. **Categories**: Create logical categories for organization
3. **SKUs**: Use consistent naming convention for products
4. **Regular Exports**: Export reports monthly for record-keeping
5. **Stock Checks**: Review low stock alerts weekly
6. **Audit Trail**: Check transaction history for discrepancies

## Keyboard Shortcuts

None at this time, but all forms are keyboard accessible using Tab key.

## Troubleshooting

### Missing Inventory Link in Sidebar
- Check that you're logged in as admin or inventory_manager
- Role is set in user profile in Django admin

### Cannot Save Product
- Ensure SKU is unique
- Ensure all required fields are filled
- Category must be selected

### Stock Out Fails
- Check current inventory (should show below product dropdown)
- Cannot remove more than current stock
- Try exact quantity first to test

### PDF Export Not Working
- Check that reportlab is installed: `pip install reportlab`
- Try a different browser
- Check browser console for errors

## Support

For issues or questions:
1. Check this guide first
2. Review INVENTORY_MANAGEMENT.md for detailed docs
3. Check Django debug mode for error details
