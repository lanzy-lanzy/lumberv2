# Inventory Management System

A comprehensive inventory management system with PDF export capabilities using ReportLab.

## Features

### 1. **Inventory Management Dashboard**
- Real-time overview of inventory statistics
- Total products and categories count
- Total pieces and board feet in stock
- Low stock alerts
- 7-day stock movement summary
- Recent transaction history

**URL**: `/inventory/management/`

### 2. **Categories Management**
- Create, read, update, and delete categories
- View product count per category
- Add descriptions to categories
- Quick modal-based interface

**URL**: `/inventory/management/categories/`

### 3. **Products Management**
- Manage lumber products with full details
- Track product dimensions (thickness, width, length)
- Set pricing per board foot and per piece
- Unique SKU management
- Bulk view all products

**URL**: `/inventory/management/products/`

### 4. **Stock In Management**
- Record incoming stock with full details
- Support for supplier information
- Track cost per unit
- Reference ID for purchase orders
- View recent stock in transactions

**URL**: `/inventory/management/stock-in/`

### 5. **Stock Out Management**
- Record outgoing stock
- Multiple reasons: sales, damaged, lost, return, other
- View current stock before removing
- Reference ID for sales orders or RMAs
- View recent stock out transactions

**URL**: `/inventory/management/stock-out/`

### 6. **Inventory Levels View**
- Real-time inventory status for all products
- Filter by category or search by name/SKU
- Low stock alerts (< 100 pieces or < 500 BF)
- Last updated timestamp
- Summary statistics

**URL**: `/inventory/management/inventory-levels/`

### 7. **Transaction History**
- Complete audit trail of all inventory movements
- Filter by transaction type, product, and date range
- Visual indicators for transaction type
- Reason/created by information
- Summary statistics

**URL**: `/inventory/management/transaction-history/`

## PDF Export Features

### Export Options

1. **Inventory Levels PDF**
   - Complete list of current inventory
   - Product names, categories, SKUs
   - Current pieces and board feet
   - Last updated dates
   
   **URL**: `/inventory/management/export/inventory-pdf/`

2. **Stock Transactions PDF**
   - Historical transaction records
   - Filterable by transaction type and date range
   - Shows product, quantity, board feet, reference IDs
   - Created by user information
   
   **URL**: `/inventory/management/export/transactions-pdf/`

3. **Products Catalog PDF**
   - Complete product catalog
   - Dimensions and pricing information
   - SKU and category information
   - Sortable by category
   
   **URL**: `/inventory/management/export/products-pdf/`

4. **Categories Summary PDF**
   - Inventory summary by category
   - Product count per category
   - Total pieces and board feet per category
   - Grand totals
   
   **URL**: `/inventory/management/export/categories-pdf/`

## Access Control

Only users with the following roles can access inventory management:
- **admin** - Full access to all features
- **inventory_manager** - Full access to all features

The system uses Django's `@user_passes_test` decorator to enforce role-based access control.

## URL Routes

All management routes are prefixed with `/inventory/management/`:

```
/                              → Dashboard
/categories/                   → Manage Categories
/products/                     → Manage Products
/stock-in/                     → Stock In Recording
/stock-out/                    → Stock Out Recording
/inventory-levels/             → View Inventory Levels
/transaction-history/          → View Transaction History
/export/inventory-pdf/         → Export Inventory PDF
/export/transactions-pdf/      → Export Transactions PDF
/export/products-pdf/          → Export Products PDF
/export/categories-pdf/        → Export Categories PDF
```

## Sidebar Integration

A new "Management" link has been added to the Inventory section in the admin sidebar:

```html
<a href="{% url 'inventory_management:dashboard' %}" class="sidebar-nav ...">
    <i class="fas fa-warehouse"></i>
    <span>Management</span>
</a>
```

The link is visible only to users with admin or inventory_manager roles.

## Database Models Used

The system leverages existing models:

1. **LumberCategory** - Product categories
2. **LumberProduct** - Product definitions with dimensions and pricing
3. **Inventory** - Current inventory levels (one-to-one with LumberProduct)
4. **StockTransaction** - Complete audit trail of all movements
5. **InventorySnapshot** - Historical daily snapshots (future reporting)

## PDF Generation with ReportLab

All PDF exports use ReportLab's Platypus API for professional document generation:

### Features
- Landscape A4 page layout for better table display
- Styled tables with alternating row colors
- Professional header styling
- Centered titles with blue color scheme
- Custom fonts and sizing
- Automatic generation timestamps

### Dependencies
```
reportlab>=4.0.0
pillow>=9.0.0
```

## Frontend Technology Stack

- **CSS Framework**: Tailwind CSS
- **JavaScript**: Vanilla JavaScript (no jQuery)
- **Icons**: Font Awesome 6.4.0
- **Modals**: Custom modal implementation using CSS classes
- **Forms**: Server-side CSRF protection with Django

## API Integration

The management views use existing DRF ViewSets via the InventoryService:

- `InventoryService.stock_in()` - Record stock in
- `InventoryService.stock_out()` - Record stock out
- `InventoryService.adjust_stock()` - Stock adjustments

## File Structure

```
app_inventory/
├── management_views.py          # All management view functions
├── management_urls.py           # URL routes for management
├── templatetags/
│   ├── __init__.py
│   └── custom_filters.py        # Template filters for summaries
│
templates/inventory/management/
├── dashboard.html               # Main dashboard
├── categories.html              # Category management
├── products.html                # Product management
├── stock_in.html                # Stock in recording
├── stock_out.html               # Stock out recording
├── inventory_levels.html        # Inventory view
└── transaction_history.html     # Transaction history
```

## Usage Examples

### Record Stock In
```
1. Navigate to /inventory/management/stock-in/
2. Select product from dropdown
3. Enter quantity in pieces
4. (Optional) Enter cost per unit
5. (Optional) Enter reference ID (PO number)
6. Click "Record Stock In"
```

### Export Inventory Report
```
1. Navigate to /inventory/management/
2. Click "Inventory Levels PDF" in Export Reports section
3. PDF will download automatically
4. Or go directly to /inventory/management/export/inventory-pdf/
```

### Manage Products
```
1. Navigate to /inventory/management/products/
2. Click "Add Product" button
3. Fill in all product details
4. Click "Save"
5. View all products in the table below
```

## Authentication & Permissions

All views require:
- User to be authenticated (`@login_required`)
- User to have admin or inventory_manager role (`@user_passes_test`)

## Notes

- Stock transactions are immutable (no editing, only deletion by admin)
- All changes are logged with timestamp and user information
- Board feet calculations follow the standard formula: (Thickness × Width × Length) / 12
- Inventory levels are updated in real-time with each transaction
- Low stock threshold: 100 pieces or 500 board feet

## Future Enhancements

- Batch import/export
- Email alerts for low stock
- Inventory forecasting
- Integration with supplier management
- Reorder points automation
- Cycle counting workflows
- Cost analysis and margin reports
