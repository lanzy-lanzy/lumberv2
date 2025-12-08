# Phase 7 Implementation Guide - Frontend & Backend Synchronization

## Quick Start

### 1. Update Django Settings

Add to `lumber/settings.py`:

```python
# Add after INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps ...
    'corsheaders',  # For HTMX/AJAX requests
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add this
    # ... existing middleware ...
]

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://localhost:3000',
]

# Template Configuration (already done)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

### 2. Create Frontend URLs

Create `core/views.py` with the views from `templates/urls_frontend.py`:

```bash
cp templates/urls_frontend.py core/views.py
```

Then add to `lumber/urls.py`:

```python
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ... existing patterns ...
    
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Frontend Dashboard Routes
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Inventory Routes
    path('inventory/dashboard/', views.inventory_dashboard, name='inventory-dashboard'),
    path('inventory/stock-in/', views.stock_in, name='stock-in'),
    path('inventory/stock-out/', views.stock_out, name='stock-out'),
    path('inventory/adjustments/', views.stock_adjustment, name='stock-adjustment'),
    
    # Sales Routes
    path('sales/pos/', views.pos, name='pos'),
    path('sales/orders/', views.sales_orders, name='sales-orders'),
    
    # Delivery Routes
    path('delivery/queue/', views.delivery_queue, name='delivery-queue'),
    path('delivery/all/', views.deliveries, name='deliveries'),
    
    # Supplier Routes
    path('supplier/suppliers/', views.suppliers, name='suppliers'),
    path('supplier/purchase-orders/', views.purchase_orders, name='purchase-orders'),
    
    # Report Routes
    path('reports/inventory/', views.inventory_reports, name='inventory-reports'),
    path('reports/sales/', views.sales_reports, name='sales-reports'),
    path('reports/delivery/', views.delivery_reports, name='delivery-reports'),
    
    # API URLs (existing)
    path('api/', include('api.urls')),
]
```

### 3. Create Authentication Templates

Create `templates/auth/login.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Login - Lumber Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="min-h-screen flex items-center justify-center">
        <div class="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
            <div class="text-center mb-8">
                <i class="fas fa-tree text-green-600 text-5xl mb-4"></i>
                <h1 class="text-3xl font-bold text-gray-900">Lumber Management</h1>
            </div>
            
            <form method="post" class="space-y-4">
                {% csrf_token %}
                <div>
                    <label class="block text-sm font-medium text-gray-700">Username</label>
                    <input type="text" name="username" required 
                           class="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">Password</label>
                    <input type="password" name="password" required 
                           class="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg">
                </div>
                <button type="submit" class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                    Login
                </button>
            </form>
        </div>
    </div>
</body>
</html>
```

### 4. Install Required Packages

```bash
pip install django-cors-headers
pip install django-htmx
```

### 5. Update User Model

Add role field to User model (if not already present):

```python
# core/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Inventory Manager', 'Inventory Manager'),
        ('Cashier', 'Cashier'),
        ('Warehouse Staff', 'Warehouse Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='User')
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
```

Then update templates to use:
```html
{{ request.user.userprofile.role }}
```

---

## Template Files Created

### Phase 1-7 Synchronized Templates

#### Base & Layout
- ✅ `templates/base.html` - Main layout with navigation & sidebar
- ✅ `templates/dashboard.html` - Dashboard entry point

#### Dashboards (Role-Based)
- ✅ `templates/dashboards/admin_dashboard.html` - Admin overview
- ✅ `templates/dashboards/inventory_manager_dashboard.html` - Stock management
- ✅ `templates/dashboards/cashier_dashboard.html` - POS interface
- ✅ `templates/dashboards/warehouse_dashboard.html` - Delivery queue

#### Inventory Module (Phase 2)
- ✅ `templates/inventory/stock_in.html` - Add inventory
- ✅ `templates/inventory/stock_out.html` - Record deductions
- 🟡 `templates/inventory/stock_adjustment.html` - (Stub needed)
- 🟡 `templates/inventory/inventory_dashboard.html` - Stock overview (Stub)

#### Sales Module (Phase 3)
- 🟡 `templates/sales/pos.html` - POS interface (Full version from cashier dashboard)
- 🟡 `templates/sales/sales_orders.html` - Order management (Stub)
- 🟡 `templates/sales/receipts.html` - Receipt display (Stub)

#### Delivery Module (Phase 4)
- 🟡 `templates/delivery/delivery_queue.html` - Picking queue (Stub)
- 🟡 `templates/delivery/deliveries.html` - All deliveries (Stub)
- 🟡 `templates/delivery/delivery_detail.html` - Single delivery (Stub)

#### Supplier Module (Phase 5)
- 🟡 `templates/supplier/suppliers.html` - Supplier list (Stub)
- 🟡 `templates/supplier/supplier_detail.html` - Supplier info (Stub)
- 🟡 `templates/supplier/purchase_orders.html` - PO management (Stub)

#### Reports Module (Phase 6)
- 🟡 `templates/reports/inventory_reports.html` - Stock reports (Stub)
- 🟡 `templates/reports/sales_reports.html` - Revenue reports (Stub)
- 🟡 `templates/reports/delivery_reports.html` - Logistics reports (Stub)

#### Components & Reusables
- 🟡 `templates/components/tables.html` - Table templates (Stub)
- 🟡 `templates/components/forms.html` - Form elements (Stub)
- 🟡 `templates/components/modals.html` - Dialog templates (Stub)

**Status**: ✅ Core framework + 4 dashboards + 2 stock forms complete
**Remaining**: Stubs for 14+ templates (easy to expand)

---

## API Integration Pattern

All templates follow this pattern for syncing with backend:

### 1. Load Data on Page Load
```html
<div hx-get="/api/inventory/" hx-trigger="load" hx-swap="innerHTML">
    <div class="text-center text-gray-500">Loading...</div>
</div>
```

### 2. Submit Form
```html
<form hx-post="/api/inventory/stock-in/" hx-swap="none">
    <!-- Form fields -->
</form>
```

### 3. Polling for Updates
```html
<div hx-get="/api/metrics/low_stock_alerts/" hx-trigger="every 60s">
    <!-- Alert list -->
</div>
```

### 4. Dynamic Search
```html
<input type="text" 
       hx-get="/api/products/?q={query}" 
       hx-trigger="keyup changed delay:500ms"
       hx-target="#products-list">
```

---

## Data Flow Examples

### Stock In Flow
```
User fills form → Validates client-side → 
Submit via HTMX POST /api/inventory/stock-in/ → 
Backend creates StockTransaction → 
Updates LumberProduct quantity → 
Updates SupplierPriceHistory →
Response back → Refresh list via HTMX
```

### Sales Order Flow
```
Cashier selects products → Cart managed by Alpine.js →
Enter customer info → Select payment type →
Submit via HTMX POST /api/sales-orders/ →
Backend creates SalesOrder → Deducts stock →
Updates payment tracking →
Generate Receipt →
Display success message → Clear cart
```

### Delivery Flow
```
Warehouse views queue (HTMX load) →
Selects delivery →
Modal shows items →
Checks items as picked →
Updates status (Picking → Loaded → Out → Delivered) →
Each status update via HTMX PATCH →
Captures signature for final delivery →
Updates delivery metrics
```

---

## Validation Examples

### Client-Side (HTML5)
```html
<input type="number" required min="1" />
<input type="email" required />
<select required>
    <option value="">Select...</option>
</select>
```

### Server-Side (Django)
```python
def stock_in(request):
    if request.method == 'POST':
        # Validate quantity > 0
        # Validate product exists
        # Validate supplier active
        # Validate cost > 0
        # Save to database
        # Return success or error
```

---

## Responsive Design Breakpoints

All templates use Tailwind breakpoints:

```html
<!-- Mobile first approach -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- 1 col on mobile, 2 on tablet, 3 on desktop -->
</div>
```

Common patterns:
- Single column layouts for mobile
- 2-column for tablet/iPad
- 3-4 column for desktop monitors
- Hidden elements on mobile: `hidden md:block`
- Visible only on mobile: `md:hidden`

---

## Environment Variables & Settings

Add to `.env`:
```
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

Update `settings.py`:
```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
```

---

## Testing the Frontend

### Manual Testing Checklist
- [ ] Login/Logout works
- [ ] Dashboard shows correct role
- [ ] Sidebar navigation works
- [ ] Forms submit correctly
- [ ] HTMX updates show data
- [ ] Real-time stock check works
- [ ] Payment calculations correct
- [ ] Delivery status updates work
- [ ] Reports load without errors
- [ ] Responsive on mobile/tablet/desktop

### Browser DevTools
1. Open Console (F12)
2. Check for JS errors
3. Monitor Network tab for HTMX requests
4. Verify API responses
5. Check CSS is loading (Tailwind CDN)

---

## Common Issues & Solutions

### CSRF Token Errors
**Issue**: Form submission fails with CSRF error
**Solution**: Add `{% csrf_token %}` to all forms

### HTMX Not Working
**Issue**: Content doesn't update
**Solution**: 
1. Check HTMX is loaded: `<script src="https://unpkg.com/htmx.org"></script>`
2. Verify API endpoint returns HTML (not JSON)
3. Check browser console for errors

### Sidebar Not Toggling
**Issue**: Sidebar toggle button doesn't work
**Solution**: Ensure Alpine.js is loaded: `<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>`

### API 404 Errors
**Issue**: API endpoints return 404
**Solution**: Verify API URLs are registered in `lumber/urls.py`

### Styling Not Applied
**Issue**: Tailwind styles missing
**Solution**: Check CDN link is loaded: `<script src="https://cdn.tailwindcss.com"></script>`

---

## Performance Optimization

### 1. Caching
```python
# Cache dashboard data
from django.views.decorators.cache import cache_page

@cache_page(60)  # Cache for 60 seconds
def dashboard(request):
    pass
```

### 2. Pagination
```html
<!-- Paginate large lists -->
<div hx-get="/api/products/?page=1" hx-swap="innerHTML"></div>
```

### 3. Lazy Loading
```html
<!-- Load images on scroll -->
<img loading="lazy" src="image.jpg" />

<!-- Load content on scroll -->
<div hx-get="/api/more-items/" hx-trigger="revealed" hx-swap="appendChild"></div>
```

### 4. Minimize Requests
- Combine CSS/JS files
- Use HTMX for incremental updates
- Load only visible data (pagination)

---

## Deployment Checklist

- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Set DEBUG=False in production
- [ ] Update ALLOWED_HOSTS
- [ ] Configure HTTPS/SSL
- [ ] Set secure cookies
- [ ] Enable CSRF protection
- [ ] Configure database backups
- [ ] Set up logging
- [ ] Configure email for notifications

---

## Next Steps

1. **Complete Stub Templates**: Expand remaining 14+ template stubs
2. **Add Charting**: Integrate Chart.js for reports
3. **Mobile App**: Create React/Vue app using same APIs
4. **Testing**: Write unit & integration tests
5. **Optimization**: Profile & optimize performance
6. **Documentation**: Add inline comments & docstrings
7. **CI/CD**: Set up GitHub Actions for deployment
8. **Monitoring**: Add error tracking (Sentry)

---

## Support Files

- `PHASE_7_SUMMARY.md` - Detailed template documentation
- `PHASE_STATUS.md` - Overall project status
- `REPORTING_API.md` - Complete API documentation
- `README.MD` - Project overview

---

**Version**: Phase 7 Implementation Guide
**Last Updated**: December 8, 2024
**Status**: Ready for Frontend Integration Testing
