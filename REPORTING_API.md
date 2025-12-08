# Comprehensive Reporting & Analytics API Documentation

## Overview
The Lumber Management System provides extensive reporting and analytics capabilities across all modules. All reports are accessible via REST API endpoints and support flexible filtering with query parameters.

## Base URL
```
/api/
```

---

## 1. INVENTORY REPORTS
**Endpoint**: `/api/inventory-reports/`

### Monthly Usage vs Purchases
```
GET /api/inventory-reports/monthly_usage/
```
Compare products purchased vs used in a specific month.

**Query Parameters:**
- `year` (int): Year (e.g., 2024)
- `month` (int): Month 1-12

**Response:**
```json
{
  "period": "2024-12",
  "purchases": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "total_pieces": 100,
      "total_bf": 500.0
    }
  ],
  "usage": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "total_pieces": 80,
      "total_bf": 400.0
    }
  ]
}
```

### Wastage Report
```
GET /api/inventory-reports/wastage/
```
Track damaged, lost, or wasted materials.

**Query Parameters:**
- `days` (int): Look back N days (default: 30)

**Response:**
```json
{
  "period": "2024-11-08 to 2024-12-08",
  "total_pieces_wasted": 50,
  "total_bf_wasted": 250.0,
  "items": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "reason": "damaged",
      "total_pieces": 50,
      "total_bf": 250.0,
      "count": 2
    }
  ]
}
```

### Inventory Turnover
```
GET /api/inventory-reports/turnover/
```
Fast-moving items and inventory velocity.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "data": [
    {
      "id": 1,
      "name": "Pine",
      "stock_outs": 15,
      "avg_inventory": 500.0
    }
  ]
}
```

### Stock Value Report
```
GET /api/inventory-reports/stock_value/
```
Inventory value breakdown by category.

**Response:**
```json
{
  "total_inventory_value": 500000.0,
  "by_category": {
    "Hardwood": {
      "value": 300000.0,
      "products": [
        {
          "product_id": 1,
          "product_name": "Mahogany",
          "bf": 1000.0,
          "price_per_bf": 300.0,
          "value": 300000.0
        }
      ]
    },
    "Softwood": {
      "value": 200000.0,
      "products": [...]
    }
  }
}
```

---

## 2. SALES REPORTS
**Endpoint**: `/api/sales-reports/`

### Daily Sales Summary
```
GET /api/sales-reports/daily_summary/
```
Daily sales performance.

**Query Parameters:**
- `date` (string): YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2024-12-08",
  "total_sales": 50000.0,
  "total_discount": 2500.0,
  "net_sales": 47500.0,
  "total_paid": 47500.0,
  "outstanding_balance": 0.0,
  "transactions": 25,
  "by_payment_type": [
    {
      "payment_type": "cash",
      "count": 15,
      "total": 30000.0,
      "paid": 30000.0
    },
    {
      "payment_type": "credit",
      "count": 10,
      "total": 20000.0,
      "paid": 0.0
    }
  ]
}
```

### Top Customers
```
GET /api/sales-reports/top_customers/
```
Best customers by total spending.

**Query Parameters:**
- `days` (int): Period (default: 30)
- `limit` (int): Number of results (default: 10)

**Response:**
```json
{
  "period_days": 30,
  "limit": 10,
  "customers": [
    {
      "customer_id": 1,
      "customer_name": "John Contractor",
      "phone": "555-1234",
      "total_spent": 50000.0,
      "transaction_count": 5,
      "avg_transaction": 10000.0
    }
  ]
}
```

### Top Items
```
GET /api/sales-reports/top_items/
```
Best-selling products by revenue.

**Query Parameters:**
- `days` (int): Period (default: 30)
- `limit` (int): Number of results (default: 10)

**Response:**
```json
{
  "period_days": 30,
  "limit": 10,
  "items": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "product_sku": "PINE-001",
      "total_pieces": 500,
      "total_bf": 2500.0,
      "total_revenue": 75000.0,
      "transaction_count": 10
    }
  ]
}
```

### Income by Category
```
GET /api/sales-reports/income_by_category/
```
Revenue breakdown by product category.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "categories": [
    {
      "product_category_name": "Hardwood",
      "total_revenue": 200000.0,
      "total_items": 50,
      "total_pieces": 1000,
      "avg_item_value": 4000.0
    }
  ]
}
```

### Senior/PWD Discount Summary
```
GET /api/sales-reports/senior_pwd_discount/
```
Discount benefits given to eligible customers.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "senior_customers": 10,
  "senior_discount": 5000.0,
  "pwd_customers": 5,
  "pwd_discount": 2500.0,
  "total_discounted_orders": 15,
  "total_discount_given": 7500.0
}
```

### Outstanding Credit/SOA
```
GET /api/sales-reports/credit_outstanding/
```
Aging receivables from credit customers.

**Query Parameters:**
- `days` (int): Show only orders from last N days (optional)

**Response:**
```json
{
  "total_outstanding": 50000.0,
  "orders_count": 10,
  "orders": [
    {
      "so_number": "SO-20241201-0001",
      "customer_id": 5,
      "customer_name": "ABC Construction",
      "total_amount": 10000.0,
      "amount_paid": 0.0,
      "balance": 10000.0,
      "created_at": "2024-12-01T10:00:00Z"
    }
  ]
}
```

### Sales Trend
```
GET /api/sales-reports/sales_trend/
```
Daily sales trend over period.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "data": [
    {
      "date": "2024-11-08",
      "total": 10000.0,
      "count": 5,
      "avg": 2000.0
    }
  ]
}
```

---

## 3. DELIVERY REPORTS
**Endpoint**: `/api/delivery-reports/`

### Daily Delivery Summary
```
GET /api/delivery-reports/daily_summary/
```
Daily delivery performance and status.

**Query Parameters:**
- `date` (string): YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2024-12-08",
  "deliveries_created": 30,
  "delivered_today": 25,
  "pending": 3,
  "in_progress": 2,
  "in_transit": 5,
  "avg_delivery_time_hours": 2.5,
  "completion_rate": 83.3
}
```

### Delivery Turnaround Time
```
GET /api/delivery-reports/turnaround_time/
```
Delivery time analysis (average, min, max, median).

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "completed_deliveries": 100,
  "avg_turnaround_hours": 2.5,
  "min_turnaround_hours": 0.5,
  "max_turnaround_hours": 8.0,
  "median_turnaround_hours": 2.0
}
```

### Delivery by Driver
```
GET /api/delivery-reports/by_driver/
```
Driver performance metrics.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "drivers": [
    {
      "driver_name": "Juan Dela Cruz",
      "deliveries": 25,
      "total_bf": 5000.0,
      "avg_time_hours": 2.0
    }
  ]
}
```

### Delivery Failure Analysis
```
GET /api/delivery-reports/failure_analysis/
```
Stuck or delayed deliveries requiring attention.

**Query Parameters:**
- `days` (int): Period threshold (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "stuck_deliveries": 2,
  "deliveries": [
    {
      "delivery_id": 1,
      "delivery_number": "DEL-20241108-001",
      "so_number": "SO-20241108-001",
      "customer": "ABC Construction",
      "status": "out_for_delivery",
      "age_hours": 48.5,
      "created_at": "2024-12-06T10:00:00Z"
    }
  ]
}
```

### Delivery Volume Trend
```
GET /api/delivery-reports/volume_trend/
```
Daily delivery volume trends.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "data": [
    {
      "date": "2024-11-08",
      "created": 10,
      "completed": 8,
      "in_progress": 2
    }
  ]
}
```

### Vehicle Utilization
```
GET /api/delivery-reports/vehicle_utilization/
```
Vehicle and driver utilization metrics.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "total_active_deliveries": 50,
  "unique_vehicles": 5,
  "avg_deliveries_per_vehicle": 10.0,
  "vehicles": [
    {
      "plate_number": "ABC-1234",
      "driver": "Juan Dela Cruz",
      "deliveries": 12
    }
  ]
}
```

---

## 4. PURCHASE/SUPPLIER REPORTS
**Endpoint**: `/api/supplier-reports/`

### Supplier Totals
```
GET /api/supplier-reports/supplier_totals/
```
Total spending per supplier.

**Response:**
```json
[
  {
    "supplier_id": 1,
    "company_name": "ABC Lumber Suppliers",
    "contact_person": "Mr. Santos",
    "total_spent": 500000.0,
    "po_count": 25,
    "avg_po_amount": 20000.0,
    "delivery_rating": 4.5
  }
]
```

### Cost History
```
GET /api/supplier-reports/cost_history/
```
Historical pricing by supplier and product.

**Query Parameters:**
- `supplier_id` (int): Filter by supplier (optional)
- `product_id` (int): Filter by product (optional)

**Response:**
```json
[
  {
    "id": 1,
    "supplier": "ABC Lumber Suppliers",
    "product": "Pine",
    "price_per_unit": 25.0,
    "valid_from": "2024-11-01",
    "valid_to": "2024-12-01",
    "created_at": "2024-11-01T10:00:00Z"
  }
]
```

### Delivery Performance
```
GET /api/supplier-reports/delivery_performance/
```
Supplier on-time delivery metrics.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
[
  {
    "supplier_id": 1,
    "company_name": "ABC Lumber Suppliers",
    "total_pos": 10,
    "received_pos": 9,
    "pending_pos": 1,
    "on_time_delivery_estimate": 8,
    "delivery_rating": 4.5
  }
]
```

### Purchase Summary
```
GET /api/supplier-reports/purchase_summary/
```
Overall purchasing summary.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "total_spent": 500000.0,
  "total_pos": 25,
  "received_pos": 23,
  "pending_pos": 2,
  "supplier_count": 5,
  "avg_po_amount": 20000.0
}
```

---

## 5. COMPREHENSIVE DASHBOARD
**Endpoint**: `/api/metrics/`

### Executive Dashboard
```
GET /api/metrics/executive_dashboard/
```
High-level executive summary.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "sales": {
    "total": 500000.0,
    "transactions": 100,
    "avg_transaction": 5000.0
  },
  "inventory": {
    "total_value": 1000000.0,
    "products_active": 50,
    "low_stock_alerts": 5
  },
  "deliveries": {
    "completed": 80,
    "pending": 20,
    "total": 100
  },
  "purchasing": {
    "total_spent": 400000.0,
    "orders": 25,
    "suppliers": 5
  },
  "customers": {
    "unique": 50,
    "total": 150
  }
}
```

### Low Stock Alerts
```
GET /api/metrics/low_stock_alerts_comprehensive/
```
All products below stock threshold.

**Response:**
```json
{
  "count": 3,
  "alerts": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "sku": "PINE-001",
      "quantity_pieces": 10,
      "board_feet": 50.0,
      "price_per_bf": 25.0,
      "estimated_value": 1250.0
    }
  ]
}
```

### Overstock Alerts
```
GET /api/metrics/overstock_alerts_comprehensive/
```
Products above stock threshold.

**Query Parameters:**
- `threshold` (int): Board feet threshold (default: 5000)

**Response:**
```json
{
  "threshold": 5000,
  "count": 2,
  "alerts": [
    {
      "product_id": 2,
      "product_name": "Mahogany",
      "sku": "MAH-001",
      "quantity_pieces": 500,
      "board_feet": 10000.0,
      "price_per_bf": 300.0,
      "estimated_value": 3000000.0
    }
  ]
}
```

### Aged Receivables
```
GET /api/metrics/aged_receivables/
```
Credit customers with aging accounts.

**Query Parameters:**
- `days` (int): Days threshold (default: 30)

**Response:**
```json
{
  "days_threshold": 30,
  "total_outstanding": 100000.0,
  "count": 10,
  "items": [
    {
      "so_number": "SO-20241108-001",
      "customer_name": "ABC Construction",
      "customer_id": 1,
      "total_amount": 10000.0,
      "amount_paid": 0.0,
      "balance": 10000.0,
      "days_old": 30,
      "created_at": "2024-11-08T10:00:00Z"
    }
  ]
}
```

### Product Performance
```
GET /api/metrics/product_performance/
```
Sales performance by product.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "products": [
    {
      "product_id": 1,
      "product_name": "Pine",
      "product_sku": "PINE-001",
      "total_pieces": 500,
      "total_bf": 2500.0,
      "total_revenue": 75000.0,
      "transaction_count": 10,
      "avg_unit_price": 25.0
    }
  ]
}
```

### Category Performance
```
GET /api/metrics/category_performance/
```
Sales performance by category.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "categories": [
    {
      "product_category_name": "Hardwood",
      "total_revenue": 300000.0,
      "total_items": 60,
      "total_pieces": 1200,
      "avg_item_value": 5000.0,
      "margin_estimate": 300000.0
    }
  ]
}
```

### Cash Flow Summary
```
GET /api/metrics/cash_flow/
```
Cash inflows and outflows analysis.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "cash_inflows": 500000.0,
  "credit_sales_outstanding": 100000.0,
  "cash_outflows": 400000.0,
  "net_cash_position": 100000.0,
  "outstanding_receivables": 50000.0
}
```

### Supplier Analysis
```
GET /api/metrics/supplier_analysis/
```
Supplier performance ranking.

**Query Parameters:**
- `days` (int): Period (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "suppliers": [
    {
      "supplier_id": 1,
      "company_name": "ABC Lumber Suppliers",
      "contact_person": "Mr. Santos",
      "total_spent": 500000.0,
      "po_count": 25,
      "received_count": 23,
      "pending_count": 2,
      "fulfillment_rate": 92.0,
      "delivery_rating": 4.5
    }
  ]
}
```

### Inventory Composition
```
GET /api/metrics/inventory_composition/
```
Inventory breakdown by category.

**Response:**
```json
{
  "total_inventory_value": 1000000.0,
  "total_board_feet": 50000.0,
  "categories": {
    "Hardwood": {
      "value": 600000.0,
      "board_feet": 20000.0,
      "product_count": 10,
      "percentage_of_total": 60.0,
      "products": [
        {
          "product_id": 1,
          "product_name": "Mahogany",
          "sku": "MAH-001",
          "pieces": 1000,
          "board_feet": 5000.0,
          "value": 1500000.0
        }
      ]
    },
    "Softwood": {
      "value": 400000.0,
      "board_feet": 30000.0,
      "product_count": 15,
      "percentage_of_total": 40.0,
      "products": [...]
    }
  }
}
```

---

## Common Query Parameters

| Parameter | Type | Example | Note |
|-----------|------|---------|------|
| days | integer | 30 | Look back N days from today |
| date | string | 2024-12-08 | YYYY-MM-DD format |
| year | integer | 2024 | For monthly reports |
| month | integer | 12 | 1-12 for monthly reports |
| limit | integer | 10 | Limit results (top N) |
| threshold | integer | 100 | For alert thresholds |
| supplier_id | integer | 1 | Filter by supplier |
| product_id | integer | 5 | Filter by product |

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (authentication required) |
| 404 | Not found |
| 500 | Server error |

---

## Authentication

All reporting endpoints require authentication. Include token in header:
```
Authorization: Bearer <your_token>
```

---

## Examples

### Get December 2024 Usage vs Purchases
```bash
GET /api/inventory-reports/monthly_usage/?year=2024&month=12
```

### Get Top 5 Customers Last 60 Days
```bash
GET /api/sales-reports/top_customers/?days=60&limit=5
```

### Get Delivery Performance Last 7 Days
```bash
GET /api/delivery-reports/turnaround_time/?days=7
```

### Get Low Stock Products
```bash
GET /api/metrics/low_stock_alerts_comprehensive/
```

### Get 90-Day Aged Receivables
```bash
GET /api/metrics/aged_receivables/?days=90
```

### Get Executive Dashboard (60-day view)
```bash
GET /api/metrics/executive_dashboard/?days=60
```

---

## Notes

- All monetary values are in decimal format (e.g., 1000.00)
- All dates/times are in ISO 8601 format
- Board feet (BF) calculations follow: (Thickness × Width × Length) / 12
- Default period for most reports is last 30 days
- Reports are read-only (GET endpoints only)
- All reports require user authentication
