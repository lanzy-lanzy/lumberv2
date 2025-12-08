# Quick Start Guide - Phase 7 Frontend

## 30-Second Setup

```bash
# 1. Run server
python manage.py runserver

# 2. Login
# Go to: http://localhost:8000/admin/
# Create superuser if needed: python manage.py createsuperuser

# 3. Access dashboard
# http://localhost:8000/dashboard/
```

---

## Dashboard URLs by Role

```
Admin:              http://localhost:8000/dashboard/
Inventory Manager:  http://localhost:8000/dashboard/
Cashier:            http://localhost:8000/dashboard/
Warehouse Staff:    http://localhost:8000/dashboard/
```
*(Routes to appropriate dashboard based on user role)*

---

## Feature URLs

```
Stock In:           /inventory/stock-in/
Stock Out:          /inventory/stock-out/
Adjustments:        /inventory/adjustments/

Point of Sale:      /sales/pos/
Sales Orders:       /sales/orders/

Delivery Queue:     /delivery/queue/
All Deliveries:     /delivery/all/

Suppliers:          /supplier/suppliers/
Purchase Orders:    /supplier/purchase-orders/

Inventory Reports:  /reports/inventory/
Sales Reports:      /reports/sales/
Delivery Reports:   /reports/delivery/
```

---

## Test Data

### Create Test Users

```python
# In Python shell: python manage.py shell

from django.contrib.auth.models import User
from core.models import UserProfile

# Admin
admin = User.objects.create_user(username='admin', password='admin123')
UserProfile.objects.create(user=admin, role='Admin')

# Inventory Manager
inv_mgr = User.objects.create_user(username='inventory', password='inv123')
UserProfile.objects.create(user=inv_mgr, role='Inventory Manager')

# Cashier
cashier = User.objects.create_user(username='cashier', password='cash123')
UserProfile.objects.create(user=cashier, role='Cashier')

# Warehouse
warehouse = User.objects.create_user(username='warehouse', password='ware123')
UserProfile.objects.create(user=warehouse, role='Warehouse Staff')
```

### Login As
```
Username: admin     / Password: admin123
Username: inventory / Password: inv123
Username: cashier   / Password: cash123
Username: warehouse / Password: ware123
```

---

## Key Features

### Admin Dashboard
- Executive KPIs (Sales, Inventory, Deliveries, Credit)
- Low Stock Alerts
- Aged Receivables
- Sales Trend Chart
- Top Suppliers
- Quick Actions

### Inventory Manager Dashboard
- Board Feet Tracking
- Active Products Count
- Low Stock Items
- Quick Stock In Form
- Recent Transactions
- Inventory Composition

### Cashier Dashboard (POS)
- Product Search & Selection
- Cart Management
- Customer Info
- Payment Type Selection (Cash/Partial/Credit)
- Senior/PWD Discounts
- Automatic Change Calculation
- Receipt Generation
- Today's Transactions

### Warehouse Dashboard
- Delivery Queue by Status
- Item Picking Checklist
- Driver Assignment
- Status Updates
- Signature Capture
- Performance Metrics

---

## Form Usage

### Stock In
1. Select Supplier
2. Enter PO Number (optional)
3. Select Product
4. Enter Quantity & Cost
5. Enter Dimensions (optional, auto-calculates board feet)
6. Add Notes
7. Click "Add Stock"

### Stock Out
1. Select Reason (6 options)
2. Select Product
3. Enter Quantity
4. Enter Description
5. Add Reference (optional)
6. Click "Record Stock Out"

### Point of Sale
1. Search Products (search box)
2. Click Products to Add to Cart
3. Enter Customer Name (optional)
4. Select Payment Type
5. Check Senior/PWD if applicable
6. Review Order Summary
7. Enter Amount Tendered
8. Click "Process Sale"
9. View Receipt

### Purchase Order
1. Select Supplier
2. Set Expected Delivery Date
3. Add Line Items:
   - Product
   - Quantity
   - Cost per Unit
4. Submit PO
5. Confirm when ready
6. Mark Received to Auto-Stock In

---

## API Endpoints

### Inventory
```
GET    /api/inventory/stock-in/
POST   /api/inventory/stock-in/
GET    /api/inventory/stock-out/
POST   /api/inventory/stock-out/
GET    /api/inventory/adjustments/
POST   /api/inventory/adjustments/
```

### Sales
```
GET    /api/sales-orders/
POST   /api/sales-orders/
GET    /api/products/
```

### Delivery
```
GET    /api/delivery/
GET    /api/delivery/queue/
PATCH  /api/delivery/{id}/
```

### Supplier
```
GET    /api/suppliers/
POST   /api/suppliers/
GET    /api/purchase-orders/
POST   /api/purchase-orders/
```

### Metrics & Reports
```
GET    /api/metrics/executive_dashboard/
GET    /api/metrics/low_stock_alerts_comprehensive/
GET    /api/metrics/aged_receivables/
GET    /api/inventory-reports/
GET    /api/sales-reports/
GET    /api/delivery-reports/
GET    /api/supplier-reports/
```

---

## Troubleshooting

### "Page not found" Error
**Issue**: Template not loading
**Solution**: 
1. Verify templates in `/templates/` directory
2. Check `TEMPLATES` setting in `settings.py`
3. Run `python manage.py collectstatic`

### "API 404" Error
**Issue**: API endpoint not found
**Solution**: 
1. Check API URLs are registered in `urls.py`
2. Verify endpoint is correct in template
3. Check API response in browser Network tab

### "Styling not applied"
**Issue**: Tailwind CSS not loading
**Solution**: 
1. Check CDN link in browser console
2. No internet = Tailwind won't load
3. Use local CSS fallback if needed

### "Form not submitting"
**Issue**: HTMX not working
**Solution**: 
1. Check HTMX library is loaded (browser console)
2. Ensure form has `hx-post` attribute
3. Check API endpoint returns correct response

### "Login redirects to /admin/"
**Issue**: Custom login URL not configured
**Solution**: 
1. Add to `settings.py`: `LOGIN_URL = 'login'`
2. Create `templates/auth/login.html` (provided in guide)

---

## Performance Tips

1. **Caching**: Dashboard data cached for 60 seconds
2. **Pagination**: Lists show 10-20 items with pagination
3. **Lazy Loading**: Images load on scroll
4. **Debouncing**: Search queries debounced 500ms
5. **Compression**: Enable GZIP in production

---

## Browser DevTools

### Check HTMX Requests
1. Open DevTools (F12)
2. Go to Network tab
3. Look for XHR/Fetch requests
4. Verify 200/201 responses

### Check Console Errors
1. Open Console tab (F12)
2. Look for red JS errors
3. Check for CSS warnings
4. Verify no CSRF errors

### Check Responsive Design
1. Press Ctrl+Shift+M (toggle device toolbar)
2. Test mobile (375px width)
3. Test tablet (768px width)
4. Test desktop (1920px width)

---

## Common Tasks

### Reset Database
```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Load Sample Data
```python
# Create products, suppliers, etc. via admin or shell
python manage.py shell
```

### View API Responses
```
Open: http://localhost:8000/api/products/
Shows JSON data directly
```

### Clear Cache
```bash
python manage.py clear_cache  # If using cache
```

### Collect Static Files
```bash
python manage.py collectstatic --noinput
```

---

## File Structure

```
lumber/
├── templates/                 # All HTML templates
│   ├── base.html             # Master layout
│   ├── dashboard.html        # Dashboard router
│   ├── dashboards/           # Role-specific dashboards
│   ├── inventory/            # Inventory forms
│   ├── sales/                # Sales forms
│   ├── delivery/             # Delivery forms
│   ├── supplier/             # Supplier forms
│   └── reports/              # Report templates
│
├── app_**/                    # Django apps (API endpoints)
├── core/                      # Auth & user roles
├── lumber/                    # Django settings
├── manage.py                  # Django CLI
├── db.sqlite3                 # Database
├── static/                    # CSS, JS, Images
└── media/                     # User uploads
```

---

## Documentation Files

- **README.MD** - Project overview
- **PHASE_7_COMPLETE.md** - Phase 7 full documentation
- **PHASE_7_SUMMARY.md** - Template details
- **PHASE_7_IMPLEMENTATION_GUIDE.md** - Setup guide
- **REPORTING_API.md** - Complete API docs
- **QUICK_START.md** - This file

---

## Support

### Getting Help
1. Check template comments
2. Review API documentation
3. Check browser console (F12)
4. Verify database has test data
5. Test API endpoints directly

### Reporting Issues
1. Note error message
2. Check browser console
3. Check Network tab in DevTools
4. Provide Django logs
5. Include Django version & Python version

---

## Next Steps

1. **Explore Dashboards**: Login as different roles to see all views
2. **Test Forms**: Submit data and verify API calls
3. **Check Reports**: Generate reports and review data
4. **Review Code**: Check template comments and code structure
5. **Customize**: Modify templates for your needs

---

**Version**: Phase 7 Complete
**Last Updated**: December 8, 2024
**Status**: Ready to Use

Happy coding! 🌲📊
