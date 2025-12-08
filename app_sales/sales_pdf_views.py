from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime
from io import BytesIO
from decimal import Decimal

from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app_sales.models import SalesOrder, SalesOrderItem


@login_required
def sales_orders_export_preview(request):
    """Show preview of sales orders based on filters"""
    
    # Get filter parameters
    search_term = request.GET.get('search', '')
    payment_type = request.GET.get('payment_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build query
    orders = SalesOrder.objects.select_related('customer', 'created_by').prefetch_related('sales_order_items')
    
    # Apply filters
    if search_term:
        orders = orders.filter(
            Q(so_number__icontains=search_term) |
            Q(customer__name__icontains=search_term)
        )
    
    if payment_type:
        orders = orders.filter(payment_type=payment_type)
    
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    
    if date_to:
        date_to_end = timezone.make_aware(datetime.combine(
            datetime.strptime(date_to, '%Y-%m-%d').date(),
            datetime.max.time()
        ))
        orders = orders.filter(created_at__lte=date_to_end)
    
    # Calculate summaries
    total_orders = orders.count()
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
    pending_balance = orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
    amount_paid = orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
    
    # Group by payment type
    payment_summary = orders.values('payment_type').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('payment_type')
    
    context = {
        'orders': orders.order_by('-created_at')[:100],  # Limit for preview
        'filters': {
            'search': search_term,
            'payment_type': payment_type,
            'date_from': date_from,
            'date_to': date_to,
        },
        'summary': {
            'total_orders': total_orders,
            'total_sales': float(total_sales),
            'total_discount': float(total_discount),
            'amount_paid': float(amount_paid),
            'pending_balance': float(pending_balance),
        },
        'payment_summary': list(payment_summary),
    }
    
    return render(request, 'sales/export_preview.html', context)


@login_required
def export_sales_orders_pdf(request):
    """Export sales orders to PDF based on filters"""
    
    # Get filter parameters
    search_term = request.GET.get('search', '')
    payment_type = request.GET.get('payment_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    format_type = request.GET.get('format', 'summary')  # summary or detailed
    
    # Build query
    orders = SalesOrder.objects.select_related('customer', 'created_by').prefetch_related(
        'sales_order_items__product'
    ).order_by('-created_at')
    
    # Apply filters
    if search_term:
        orders = orders.filter(
            Q(so_number__icontains=search_term) |
            Q(customer__name__icontains=search_term)
        )
    
    if payment_type:
        orders = orders.filter(payment_type=payment_type)
    
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
    
    if format_type == 'detailed':
        _generate_detailed_pdf(buffer, orders, search_term, payment_type, date_from, date_to)
    else:
        _generate_summary_pdf(buffer, orders, search_term, payment_type, date_from, date_to)
    
    buffer.seek(0)
    
    filename = f"sales_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def _generate_summary_pdf(buffer, orders, search_term, payment_type, date_from, date_to):
    """Generate summary PDF with table view"""
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Sales Orders Report', title_style))
    
    # Report details
    report_info = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if date_from or date_to:
        date_range = f"Date Range: {date_from or 'All'} to {date_to or 'All'}"
        report_info += f" | {date_range}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.15*inch))
    
    # Summary statistics
    total_orders = orders.count()
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
    amount_paid = orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
    pending_balance = orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
    
    summary_data = [
        [f'Total Orders: {total_orders}', f'Total Sales: ₱{float(total_sales):,.2f}',
         f'Paid: ₱{float(amount_paid):,.2f}', f'Balance: ₱{float(pending_balance):,.2f}']
    ]
    summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Orders table
    table_data = [
        ['SO Number', 'Customer', 'Items', 'Amount', 'Discount', 'Paid', 'Balance', 'Type', 'Date']
    ]
    
    for order in orders[:200]:  # Limit to 200 for PDF size
        payment_type_label = dict(SalesOrder.PAYMENT_CHOICES).get(order.payment_type, order.payment_type)
        table_data.append([
            order.so_number or '-',
            order.customer.name[:20],
            str(order.sales_order_items.count()),
            f"₱{float(order.total_amount):,.2f}",
            f"₱{float(order.discount_amount):,.2f}" if order.discount_amount > 0 else '-',
            f"₱{float(order.amount_paid):,.2f}",
            f"₱{float(order.balance):,.2f}",
            payment_type_label,
            order.created_at.strftime('%m/%d/%Y'),
        ])
    
    # Create table
    table = Table(table_data, colWidths=[1.1*inch, 1.2*inch, 0.6*inch, 1*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)


def _generate_detailed_pdf(buffer, orders, search_term, payment_type, date_from, date_to):
    """Generate detailed PDF with individual sales order details"""
    
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Sales Orders - Detailed Report', title_style))
    
    # Report details
    report_info = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Process each order
    for idx, order in enumerate(orders[:50]):  # Limit to 50 for PDF size
        
        if idx > 0:
            elements.append(PageBreak())
        
        # Order header
        order_header_style = ParagraphStyle(
            'OrderHeader',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=6,
        )
        elements.append(Paragraph(f'Sales Order: {order.so_number}', order_header_style))
        
        # Order info
        info_data = [
            ['SO Number:', order.so_number or '-', 'Date:', order.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Customer:', order.customer.name, 'Phone:', order.customer.phone_number or '-'],
            ['Email:', order.customer.email or '-', 'Address:', (order.customer.address or '-')[:30]],
        ]
        info_table = Table(info_data, colWidths=[1*inch, 2*inch, 1*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Order items
        items_header = ParagraphStyle(
            'ItemsHeader',
            parent=styles['Heading3'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
        )
        elements.append(Paragraph('Order Items', items_header))
        
        items_data = [['Product', 'Qty (pcs)', 'Unit Price', 'Board Feet', 'Subtotal']]
        
        for item in order.sales_order_items.all():
            items_data.append([
                item.product.name[:25],
                str(item.quantity_pieces),
                f"₱{float(item.unit_price):,.2f}",
                f"{float(item.board_feet):.2f}",
                f"₱{float(item.subtotal):,.2f}",
            ])
        
        items_table = Table(items_data, colWidths=[2.5*inch, 0.8*inch, 1*inch, 0.9*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Order summary
        payment_type_label = dict(SalesOrder.PAYMENT_CHOICES).get(order.payment_type, order.payment_type)
        
        summary_data = [
            ['Total Amount:', f"₱{float(order.total_amount):,.2f}"],
            ['Discount (20%):', f"-₱{float(order.discount_amount):,.2f}" if order.discount_amount > 0 else '₱0.00'],
            ['Amount Paid:', f"₱{float(order.amount_paid):,.2f}"],
            ['Balance:', f"₱{float(order.balance):,.2f}"],
            ['Payment Type:', payment_type_label],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(summary_table)
        
        if order.notes:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f'<b>Notes:</b> {order.notes}', styles['Normal']))
    
    # Build PDF
    doc.build(elements)
