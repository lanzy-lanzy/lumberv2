from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app_sales.models import SalesOrder, SalesOrderItem, Customer
from app_inventory.models import LumberProduct


@login_required
def export_sales_report_pdf(request):
    """Export comprehensive sales report to PDF"""
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    report_type = request.GET.get('type', 'comprehensive')  # comprehensive, daily, customer, product
    
    # Build query with explicit table references to avoid ambiguity
    orders = SalesOrder.objects.select_related('customer', 'created_by').prefetch_related(
        'sales_order_items__product__category'
    ).order_by('-created_at')
    
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    
    if date_to:
        date_to_end = timezone.make_aware(datetime.combine(
            datetime.strptime(date_to, '%Y-%m-%d').date(),
            datetime.max.time()
        ))
        orders = orders.filter(created_at__lte=date_to_end)
    
    # Create PDF
    buffer = BytesIO()
    
    if report_type == 'daily':
        _generate_daily_sales_pdf(buffer, orders, date_from, date_to)
    elif report_type == 'customer':
        _generate_customer_report_pdf(buffer, orders, date_from, date_to)
    elif report_type == 'product':
        _generate_product_report_pdf(buffer, orders, date_from, date_to)
    else:
        _generate_comprehensive_pdf(buffer, orders, date_from, date_to)
    
    buffer.seek(0)
    
    filename = f"sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def _generate_comprehensive_pdf(buffer, orders, date_from, date_to):
    """Generate comprehensive sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Header with company branding
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Lumber Management System', header_style))
    
    # Report title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=8,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Comprehensive Sales Report', title_style))
    
    # Date range
    date_range = f"Period: {date_from or 'All dates'} to {date_to or 'All dates'}"
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {date_range}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    total_orders = orders.count()
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
    total_paid = orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
    total_balance = orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
    avg_order_value = total_sales / total_orders if total_orders > 0 else Decimal('0')
    
    # Summary cards
    summary_data = [
        ['Total Orders', 'Total Sales', 'Discounts', 'Amount Paid', 'Outstanding', 'Avg Order'],
        [str(total_orders), f"₱{float(total_sales):,.2f}", f"₱{float(total_discount):,.2f}",
         f"₱{float(total_paid):,.2f}", f"₱{float(total_balance):,.2f}", f"₱{float(avg_order_value):,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 1.8*inch, 1.5*inch, 1.5*inch, 1.8*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#eff6ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Payment type breakdown
    payment_summary = orders.values('payment_type').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    )
    
    payment_data = [['Payment Type', 'Orders', 'Total Amount', 'Percentage']]
    payment_total = float(total_sales)
    for p in payment_summary:
        pct = (float(p['total']) / payment_total * 100) if payment_total > 0 else 0
        payment_type_label = dict(SalesOrder.PAYMENT_CHOICES).get(p['payment_type'], p['payment_type'])
        payment_data.append([
            payment_type_label,
            str(p['count']),
            f"₱{float(p['total']):,.2f}",
            f"{pct:.1f}%"
        ])
    
    payment_table = Table(payment_data, colWidths=[2*inch, 1.2*inch, 2*inch, 1.2*inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
    ]))
    elements.append(Paragraph('Payment Type Analysis', styles['Heading3']))
    elements.append(payment_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Daily sales breakdown - use distinct alias to avoid ambiguity
    daily_sales = []
    orders_by_date = SalesOrder.objects.filter(
        id__in=orders.values('id')
    ).extra(select={'date': 'DATE(app_sales_salesorder.created_at)'}).values('date').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('date')
    
    daily_data = [['Date', 'Orders', 'Total Sales', 'Avg Order']]
    for d in orders_by_date:
        avg = d['total'] / d['count'] if d['count'] > 0 else 0
        daily_data.append([
            str(d['date']),
            str(d['count']),
            f"₱{float(d['total']):,.2f}",
            f"₱{float(avg):,.2f}"
        ])
    
    daily_table = Table(daily_data, colWidths=[1.5*inch, 1.2*inch, 1.8*inch, 1.5*inch])
    daily_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f3ff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(Paragraph('Daily Sales Summary', styles['Heading3']))
    elements.append(daily_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Top customers
    customer_sales = orders.values('customer__id', 'customer__name').annotate(
        order_count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')[:10]
    
    customer_data = [['Customer', 'Orders', 'Total Purchases', 'Avg Order']]
    for c in customer_sales:
        avg = c['total'] / c['order_count'] if c['order_count'] > 0 else 0
        customer_data.append([
            c['customer__name'][:25],
            str(c['order_count']),
            f"₱{float(c['total']):,.2f}",
            f"₱{float(avg):,.2f}"
        ])
    
    customer_table = Table(customer_data, colWidths=[2.5*inch, 1*inch, 2*inch, 1.5*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ea580c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff7ed')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(Paragraph('Top 10 Customers', styles['Heading3']))
    elements.append(customer_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Top products - use subquery to avoid ambiguity
    order_ids = orders.values_list('id', flat=True)
    product_sales = SalesOrderItem.objects.filter(
        sales_order_id__in=order_ids
    ).values('product__name', 'product__category__name').annotate(
        total_qty=Sum('quantity_pieces'),
        total_bf=Sum('board_feet'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')[:10]
    
    product_data = [['Product', 'Category', 'Qty Sold', 'Board Feet', 'Revenue']]
    for p in product_sales:
        product_data.append([
            p['product__name'][:20],
            p['product__category__name'] or 'N/A',
            str(p['total_qty']),
            f"{float(p['total_bf']):,.1f}",
            f"₱{float(p['total_revenue']):,.2f}"
        ])
    
    product_table = Table(product_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.2*inch, 1.5*inch])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecfeff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(Paragraph('Top 10 Products by Revenue', styles['Heading3']))
    elements.append(product_table)
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    elements.append(Paragraph('This is a computer-generated report. Lumber Management System.', footer_style))
    
    doc.build(elements)


def _generate_daily_sales_pdf(buffer, orders, date_from, date_to):
    """Generate daily sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Header
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Daily Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Daily summary table - use subquery with explicit table reference
    order_ids = orders.values_list('id', flat=True)
    orders_by_date = SalesOrder.objects.filter(
        id__in=order_ids
    ).extra(select={'date': 'DATE(app_sales_salesorder.created_at)'}).values('date').annotate(
        count=Count('id'),
        items=Count('sales_order_items'),
        total=Sum('total_amount'),
        discount=Sum('discount_amount'),
        paid=Sum('amount_paid'),
        balance=Sum('balance')
    ).order_by('date')
    
    table_data = [['Date', 'Orders', 'Items', 'Total Sales', 'Discount', 'Paid', 'Balance']]
    
    for d in orders_by_date:
        table_data.append([
            str(d['date']),
            str(d['count']),
            str(d['items']),
            f"₱{float(d['total'] or 0):,.2f}",
            f"₱{float(d['discount'] or 0):,.2f}",
            f"₱{float(d['paid'] or 0):,.2f}",
            f"₱{float(d['balance'] or 0):,.2f}"
        ])
    
    table = Table(table_data, colWidths=[1.3*inch, 0.9*inch, 0.9*inch, 1.3*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f9ff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)


def _generate_customer_report_pdf(buffer, orders, date_from, date_to):
    """Generate customer sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Customer Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Customer summary
    customer_sales = orders.values('customer__id', 'customer__name', 'customer__phone_number').annotate(
        order_count=Count('id'),
        total=Sum('total_amount'),
        paid=Sum('amount_paid'),
        balance=Sum('balance')
    ).order_by('-total')
    
    customer_data = [['Customer', 'Phone', 'Orders', 'Total Sales', 'Paid', 'Balance']]
    
    for c in customer_sales:
        customer_data.append([
            c['customer__name'][:25],
            c['customer__phone_number'] or '-',
            str(c['order_count']),
            f"₱{float(c['total'] or 0):,.2f}",
            f"₱{float(c['paid'] or 0):,.2f}",
            f"₱{float(c['balance'] or 0):,.2f}"
        ])
    
    table = Table(customer_data, colWidths=[2.5*inch, 1.5*inch, 0.9*inch, 1.5*inch, 1.3*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)


def _generate_product_report_pdf(buffer, orders, date_from, date_to):
    """Generate product sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Product Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Product summary - use subquery to avoid ambiguity
    order_ids = orders.values_list('id', flat=True)
    product_sales = SalesOrderItem.objects.filter(
        sales_order_id__in=order_ids
    ).values('product__name', 'product__category__name').annotate(
        order_count=Count('sales_order'),
        qty=Sum('quantity_pieces'),
        bf=Sum('board_feet'),
        revenue=Sum('subtotal')
    ).order_by('-revenue')
    
    product_data = [['Product', 'Category', 'Orders', 'Qty (pcs)', 'Board Feet', 'Revenue', 'Avg Price/BF']]
    
    for p in product_sales:
        avg_price = p['revenue'] / p['bf'] if p['bf'] > 0 else 0
        product_data.append([
            p['product__name'][:20],
            p['product__category__name'] or 'N/A',
            str(p['order_count']),
            str(p['qty']),
            f"{float(p['bf'] or 0):,.1f}",
            f"₱{float(p['revenue'] or 0):,.2f}",
            f"₱{float(avg_price):,.2f}"
        ])
    
    table = Table(product_data, colWidths=[2*inch, 1.5*inch, 0.9*inch, 1*inch, 1.2*inch, 1.5*inch, 1.4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#0891b2')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecfeff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)


def _generate_daily_sales_pdf(buffer, orders, date_from, date_to):
    """Generate daily sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Header
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Daily Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Daily summary table
    table_data = [['Date', 'Orders', 'Items', 'Total Sales', 'Paid']]
    
    orders_by_date = orders.extra(select={'date': 'DATE(app_sales_salesorder.created_at)'}).values('date').annotate(
        count=Count('id'),
        items=Count('sales_order_items'),
        total=Sum('total_amount'),
        paid=Sum('amount_paid')
    ).order_by('date')
    
    for d in orders_by_date:
        table_data.append([
            str(d['date']),
            str(d['count']),
            str(d['items']),
            f"₱{float(d['total'] or 0):,.2f}",
            f"₱{float(d['paid'] or 0):,.2f}"
        ])
    
    table = Table(table_data, colWidths=[1.3*inch, 0.9*inch, 0.9*inch, 1.3*inch, 1.1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f9ff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)


def _generate_customer_report_pdf(buffer, orders, date_from, date_to):
    """Generate customer sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Customer Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Customer summary
    customer_data = [['Customer', 'Phone', 'Orders', 'Total Sales', 'Paid', 'Balance']]
    
    customer_sales = orders.values('customer__id', 'customer__name', 'customer__phone_number').annotate(
        order_count=Count('id'),
        total=Sum('total_amount'),
        paid=Sum('amount_paid'),
        balance=Sum('balance')
    ).order_by('-total')
    
    for c in customer_sales:
        customer_data.append([
            c['customer__name'][:25],
            c['customer__phone_number'] or '-',
            str(c['order_count']),
            f"₱{float(c['total'] or 0):,.2f}",
            f"₱{float(c['paid'] or 0):,.2f}",
            f"₱{float(c['balance'] or 0):,.2f}"
        ])
    
    table = Table(customer_data, colWidths=[2.5*inch, 1.5*inch, 0.9*inch, 1.5*inch, 1.3*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)


def _generate_product_report_pdf(buffer, orders, date_from, date_to):
    """Generate product sales report PDF"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph('Lumber Management System', ParagraphStyle('Header', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER)))
    elements.append(Paragraph('Product Sales Report', ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#4b5563'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Period: {date_from or 'All'} to {date_to or 'All'}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Product summary
    product_data = [['Product', 'Category', 'Orders', 'Qty (pcs)', 'Board Feet', 'Revenue', 'Avg Price/BF']]
    
    product_sales = SalesOrderItem.objects.filter(
        sales_order__in=orders
    ).values('product__name', 'product__category__name').annotate(
        order_count=Count('sales_order'),
        qty=Sum('quantity_pieces'),
        bf=Sum('board_feet'),
        revenue=Sum('subtotal')
    ).order_by('-revenue')
    
    for p in product_sales:
        avg_price = p['revenue'] / p['bf'] if p['bf'] > 0 else 0
        product_data.append([
            p['product__name'][:20],
            p['product__category__name'] or 'N/A',
            str(p['order_count']),
            str(p['qty']),
            f"{float(p['bf'] or 0):,.1f}",
            f"₱{float(p['revenue'] or 0):,.2f}",
            f"₱{float(avg_price):,.2f}"
        ])
    
    table = Table(product_data, colWidths=[2*inch, 1.5*inch, 0.9*inch, 1*inch, 1.2*inch, 1.5*inch, 1.4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#0891b2')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecfeff')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)
