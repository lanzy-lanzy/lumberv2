from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q, F, Count
from django.utils import timezone
from datetime import timedelta, datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app_inventory.models import (
    LumberCategory, LumberProduct, Inventory, StockTransaction, InventorySnapshot
)
from app_inventory.services import InventoryService
from app_inventory.reporting import InventoryReports


def is_admin_or_inventory_manager(user):
    """Check if user is admin or inventory manager"""
    return user.is_staff or (hasattr(user, 'role') and user.role in ['admin', 'inventory_manager'])


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def inventory_management_dashboard(request):
    """Main inventory management dashboard"""
    
    # Get inventory statistics
    total_products = LumberProduct.objects.filter(is_active=True).count()
    total_categories = LumberCategory.objects.count()
    
    # Current inventory
    inventory_data = Inventory.objects.select_related('product').all()
    total_pieces = inventory_data.aggregate(Sum('quantity_pieces'))['quantity_pieces__sum'] or 0
    total_board_feet = inventory_data.aggregate(Sum('total_board_feet'))['total_board_feet__sum'] or 0
    
    # Recent transactions
    recent_transactions = StockTransaction.objects.select_related(
        'product', 'created_by'
    ).order_by('-created_at')[:10]
    
    # Low stock alerts (less than 100 pieces or 500 board feet)
    low_stock = inventory_data.filter(
        Q(quantity_pieces__lt=100) | Q(total_board_feet__lt=500)
    ).order_by('quantity_pieces')
    
    # Stock movement summary (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    stock_in_count = StockTransaction.objects.filter(
        transaction_type='stock_in',
        created_at__gte=seven_days_ago
    ).count()
    stock_out_count = StockTransaction.objects.filter(
        transaction_type='stock_out',
        created_at__gte=seven_days_ago
    ).count()
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_pieces': total_pieces,
        'total_board_feet': total_board_feet,
        'recent_transactions': recent_transactions,
        'low_stock': low_stock,
        'stock_in_count': stock_in_count,
        'stock_out_count': stock_out_count,
        'inventory_count': inventory_data.count(),
    }
    
    return render(request, 'inventory/management/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def categories_management(request):
    """Manage lumber categories"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category_id')
        action = request.POST.get('action')
        
        if action == 'create':
            if not LumberCategory.objects.filter(name=name).exists():
                LumberCategory.objects.create(name=name, description=description)
                return JsonResponse({'success': True, 'message': 'Category created successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Category already exists'}, status=400)
        
        elif action == 'update':
            category = get_object_or_404(LumberCategory, id=category_id)
            category.name = name
            category.description = description
            category.save()
            return JsonResponse({'success': True, 'message': 'Category updated successfully'})
        
        elif action == 'delete':
            category = get_object_or_404(LumberCategory, id=category_id)
            category.delete()
            return JsonResponse({'success': True, 'message': 'Category deleted successfully'})
    
    categories = LumberCategory.objects.annotate(
        product_count=Count('lumberproduct')
    ).order_by('name')
    
    context = {'categories': categories}
    return render(request, 'inventory/management/categories.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def products_management(request):
    """Manage lumber products"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        product_id = request.POST.get('product_id')
        
        if action == 'create':
            category = get_object_or_404(LumberCategory, id=request.POST.get('category'))
            product = LumberProduct.objects.create(
                name=request.POST.get('name'),
                category=category,
                thickness=request.POST.get('thickness'),
                width=request.POST.get('width'),
                length=request.POST.get('length'),
                price_per_board_foot=request.POST.get('price_per_board_foot'),
                price_per_piece=request.POST.get('price_per_piece') or None,
                sku=request.POST.get('sku'),
            )
            # Create inventory record
            Inventory.objects.create(product=product)
            return JsonResponse({'success': True, 'message': 'Product created successfully'})
        
        elif action == 'update':
            product = get_object_or_404(LumberProduct, id=product_id)
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.thickness = request.POST.get('thickness')
            product.width = request.POST.get('width')
            product.length = request.POST.get('length')
            product.price_per_board_foot = request.POST.get('price_per_board_foot')
            product.price_per_piece = request.POST.get('price_per_piece') or None
            product.sku = request.POST.get('sku')
            product.save()
            return JsonResponse({'success': True, 'message': 'Product updated successfully'})
        
        elif action == 'delete':
            product = get_object_or_404(LumberProduct, id=product_id)
            product.delete()
            return JsonResponse({'success': True, 'message': 'Product deleted successfully'})
    
    categories = LumberCategory.objects.all()
    products = LumberProduct.objects.select_related('category', 'inventory').all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'inventory/management/products.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def stock_in_management(request):
    """Manage stock in transactions"""
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_pieces = int(request.POST.get('quantity_pieces'))
        cost_per_unit = request.POST.get('cost_per_unit') or None
        reference_id = request.POST.get('reference_id', '')
        
        try:
            product = get_object_or_404(LumberProduct, id=product_id)
            transaction = InventoryService.stock_in(
                product_id=product_id,
                quantity_pieces=quantity_pieces,
                cost_per_unit=float(cost_per_unit) if cost_per_unit else None,
                created_by=request.user,
                reference_id=reference_id
            )
            return JsonResponse({
                'success': True,
                'message': f'Successfully added {quantity_pieces} pieces to stock'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    products = LumberProduct.objects.filter(is_active=True).select_related('inventory').all()
    recent_stock_in = StockTransaction.objects.filter(
        transaction_type='stock_in'
    ).select_related('product', 'created_by').order_by('-created_at')[:20]
    
    context = {
        'products': products,
        'recent_stock_in': recent_stock_in,
    }
    return render(request, 'inventory/management/stock_in.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def stock_out_management(request):
    """Manage stock out transactions"""
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_pieces = int(request.POST.get('quantity_pieces'))
        reason = request.POST.get('reason', 'sales')
        reference_id = request.POST.get('reference_id', '')
        
        try:
            transaction = InventoryService.stock_out(
                product_id=product_id,
                quantity_pieces=quantity_pieces,
                reason=reason,
                created_by=request.user,
                reference_id=reference_id
            )
            return JsonResponse({
                'success': True,
                'message': f'Successfully removed {quantity_pieces} pieces from stock'
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    products = LumberProduct.objects.filter(is_active=True).select_related('inventory').all()
    recent_stock_out = StockTransaction.objects.filter(
        transaction_type='stock_out'
    ).select_related('product', 'created_by').order_by('-created_at')[:20]
    
    context = {
        'products': products,
        'recent_stock_out': recent_stock_out,
    }
    return render(request, 'inventory/management/stock_out.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def inventory_levels(request):
    """View current inventory levels"""
    
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search', '')
    
    inventories = Inventory.objects.select_related('product__category').all()
    
    if category_filter:
        inventories = inventories.filter(product__category_id=category_filter)
    
    if search_query:
        inventories = inventories.filter(
            Q(product__name__icontains=search_query) |
            Q(product__sku__icontains=search_query)
        )
    
    categories = LumberCategory.objects.all()
    
    context = {
        'inventories': inventories.order_by('product__name'),
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'inventory/management/inventory_levels.html', context)


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def transaction_history(request):
    """View transaction history"""
    
    transaction_type = request.GET.get('type')
    product_id = request.GET.get('product')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    transactions = StockTransaction.objects.select_related(
        'product', 'created_by'
    ).order_by('-created_at')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    
    if start_date:
        transactions = transactions.filter(created_at__gte=start_date)
    
    if end_date:
        transactions = transactions.filter(created_at__lte=end_date)
    
    products = LumberProduct.objects.all()
    
    context = {
        'transactions': transactions[:100],  # Limit for performance
        'products': products,
        'selected_type': transaction_type,
        'selected_product': product_id,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'inventory/management/transaction_history.html', context)


# PDF Export Functions

@login_required
@user_passes_test(is_admin_or_inventory_manager)
def export_inventory_pdf(request):
    """Export inventory levels to PDF"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Inventory Levels Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Get inventory data
    inventories = Inventory.objects.select_related('product__category').all()
    
    # Create table data
    table_data = [
        ['Product Name', 'Category', 'SKU', 'Pieces', 'Board Feet', 'Last Updated']
    ]
    
    for inv in inventories:
        table_data.append([
            inv.product.name,
            inv.product.category.name,
            inv.product.sku,
            str(inv.quantity_pieces),
            f"{inv.total_board_feet:.2f}",
            inv.last_updated.strftime('%Y-%m-%d'),
        ])
        
        # Create and style table
        table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.2*inch, 1*inch, 1.2*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventory_levels_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def export_stock_transactions_pdf(request):
    """Export stock transactions to PDF"""
    
    transaction_type = request.GET.get('type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    title_text = 'Stock Transactions Report'
    if transaction_type:
        title_text += f' - {transaction_type.replace("_", " ").title()}'
    
    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Get transactions
    transactions = StockTransaction.objects.select_related('product', 'created_by').order_by('-created_at')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if start_date:
        transactions = transactions.filter(created_at__gte=start_date)
    
    if end_date:
        transactions = transactions.filter(created_at__lte=end_date)
    
    # Create table data
    table_data = [
        ['Date', 'Product', 'Type', 'Qty (pcs)', 'Board Feet', 'Reference ID', 'Created By']
    ]
    
    for tx in transactions[:200]:  # Limit for PDF size
        table_data.append([
            tx.created_at.strftime('%Y-%m-%d %H:%M'),
            tx.product.name,
            tx.get_transaction_type_display(),
            str(tx.quantity_pieces),
            f"{tx.board_feet:.2f}",
            tx.reference_id or '-',
            tx.created_by.username if tx.created_by else '-',
        ])
    
    # Create and style table
    table = Table(table_data, colWidths=[1.2*inch, 2*inch, 1*inch, 0.9*inch, 1.1*inch, 1.2*inch, 1.1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="stock_transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def export_products_pdf(request):
    """Export products catalog to PDF"""
    
    category_filter = request.GET.get('category')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Products Catalog', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Get products
    products = LumberProduct.objects.select_related('category').filter(is_active=True)
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Create table data
    table_data = [
        ['Product Name', 'Category', 'SKU', 'Dimensions (T"×W"×L\')', 'Board Feet', 'Price/BF', 'Price/Pcs']
    ]
    
    for product in products:
        table_data.append([
            product.name,
            product.category.name,
            product.sku,
            f'{float(product.thickness):.2f}" × {float(product.width):.2f}" × {float(product.length):.2f}\'',
            f"{product.board_feet:.3f}",
            f"${float(product.price_per_board_foot):.2f}",
            f"${float(product.price_per_piece):.2f}" if product.price_per_piece else '-',
        ])
    
    # Create and style table
    table = Table(table_data, colWidths=[2*inch, 1.3*inch, 1*inch, 2*inch, 0.9*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="products_catalog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def export_category_summary_pdf(request):
    """Export category inventory summary to PDF"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph('Category Inventory Summary', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Get categories with inventory
    categories = LumberCategory.objects.annotate(
        total_pieces=Sum('lumberproduct__inventory__quantity_pieces'),
        total_bf=Sum('lumberproduct__inventory__total_board_feet'),
        product_count=Count('lumberproduct')
    ).order_by('name')
    
    # Create table data
    table_data = [
        ['Category', 'Products', 'Total Pieces', 'Total Board Feet']
    ]
    
    total_pieces = 0
    total_bf = 0
    
    for category in categories:
        pieces = category.total_pieces or 0
        bf = category.total_bf or 0
        total_pieces += pieces
        total_bf += bf
        
        table_data.append([
            category.name,
            str(category.product_count),
            str(pieces),
            f"{float(bf):.2f}",
        ])
    
    # Add totals row
    table_data.append([
        'TOTAL',
        '',
        str(total_pieces),
        f"{float(total_bf):.2f}",
    ])
    
    # Create and style table
    table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 2*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="category_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response


@login_required
@user_passes_test(is_admin_or_inventory_manager)
def export_inventory_report_pdf(request):
    """Export comprehensive inventory report to PDF"""
    
    report_type = request.GET.get('type', 'overview')  # overview, stock_levels, low_stock, stock_value
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
        spaceBefore=10,
    )
    
    # Generate report based on type
    if report_type == 'overview':
        elements.extend(_generate_overview_report(styles, title_style, subtitle_style, heading_style))
    elif report_type == 'stock_levels':
        elements.extend(_generate_stock_levels_report(styles, title_style, subtitle_style, heading_style))
    elif report_type == 'low_stock':
        elements.extend(_generate_low_stock_report(styles, title_style, subtitle_style, heading_style))
    elif report_type == 'stock_value':
        elements.extend(_generate_stock_value_report(styles, title_style, subtitle_style, heading_style))
    elif report_type == 'transactions':
        elements.extend(_generate_transactions_report(styles, title_style, subtitle_style, heading_style))
    elif report_type == 'turnover':
        elements.extend(_generate_turnover_report(styles, title_style, subtitle_style, heading_style))
    else:
        elements.append(Paragraph(f'Invalid report type: {report_type}', styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response


def _generate_overview_report(styles, title_style, subtitle_style, heading_style):
    """Generate overview report elements"""
    elements = []
    
    elements.append(Paragraph('Inventory Overview Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Summary statistics
    inventories = Inventory.objects.select_related('product', 'product__category').all()
    
    total_products = LumberProduct.objects.filter(is_active=True).count()
    total_pieces = inventories.aggregate(Sum('quantity_pieces'))['quantity_pieces__sum'] or 0
    total_bf = inventories.aggregate(Sum('total_board_feet'))['total_board_feet__sum'] or 0
    total_value = sum(inv.total_board_feet * inv.product.price_per_board_foot for inv in inventories)
    
    # Summary cards table
    summary_data = [
        ['Total Products', 'Total Stock (Pcs)', 'Total Board Feet', 'Total Value'],
        [str(total_products), f'{total_pieces:,}', f'{total_bf:.2f}', f'₱{total_value:,.2f}']
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f0fe')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Stock by category
    elements.append(Paragraph('Stock Distribution by Category', heading_style))
    
    categories = LumberCategory.objects.annotate(
        total_pieces=Sum('lumberproduct__inventory__quantity_pieces'),
        total_bf=Sum('lumberproduct__inventory__total_board_feet'),
        product_count=Count('lumberproduct')
    ).order_by('-total_bf')
    
    cat_data = [['Category', 'Products', 'Total Pieces', 'Total Board Feet', 'Estimated Value']]
    
    for cat in categories:
        pieces = cat.total_pieces or 0
        bf = cat.total_bf or 0
        value = bf * 500  # approximate value (can be calculated more accurately)
        cat_data.append([
            cat.name,
            str(cat.product_count),
            f'{pieces:,}',
            f'{float(bf):.2f}',
            f'₱{float(value):,.2f}'
        ])
    
    cat_table = Table(cat_data, colWidths=[2*inch, 1.2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Recent transactions
    elements.append(Paragraph('Recent Stock Transactions', heading_style))
    
    recent_txs = StockTransaction.objects.select_related('product', 'created_by').order_by('-created_at')[:15]
    
    tx_data = [['Date', 'Product', 'Type', 'Quantity (Pcs)', 'Board Feet', 'User']]
    for tx in recent_txs:
        tx_type = 'In' if tx.transaction_type == 'stock_in' else 'Out' if tx.transaction_type == 'stock_out' else 'Adj'
        product_name = tx.product.name if tx.product else 'Unknown'
        tx_data.append([
            tx.created_at.strftime('%Y-%m-%d'),
            product_name,
            tx_type,
            f'{tx.quantity_pieces:,}',
            f'{float(tx.board_feet):.2f}',
            tx.created_by.username if tx.created_by else 'System'
        ])
    
    tx_table = Table(tx_data, colWidths=[1.2*inch, 2*inch, 0.8*inch, 1.3*inch, 1.2*inch, 1.2*inch])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(tx_table)
    
    return elements


def _generate_stock_levels_report(styles, title_style, subtitle_style, heading_style):
    """Generate stock levels report elements"""
    elements = []
    
    elements.append(Paragraph('Stock Levels Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # All inventory items
    inventories = Inventory.objects.select_related('product', 'product__category').order_by('product__name')
    
    table_data = [['Product Name', 'Category', 'SKU', 'Pieces', 'Board Feet', 'Status']]
    
    for inv in inventories:
        pieces = inv.quantity_pieces
        if pieces == 0:
            status = 'Out of Stock'
        elif pieces < 50:
            status = 'Low Stock'
        else:
            status = 'In Stock'
        
        table_data.append([
            inv.product.name,
            inv.product.category.name,
            inv.product.sku,
            f'{pieces:,}',
            f'{float(inv.total_board_feet):.2f}',
            status
        ])
    
    table = Table(table_data, colWidths=[2.2*inch, 1.3*inch, 0.9*inch, 1*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(table)
    
    return elements


def _generate_low_stock_report(styles, title_style, subtitle_style, heading_style):
    """Generate low stock report elements"""
    elements = []
    
    elements.append(Paragraph('Low Stock Alert Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Get low stock items (less than 100 pieces or 500 board feet)
    low_stock = Inventory.objects.select_related('product', 'product__category').filter(
        Q(quantity_pieces__lt=100) | Q(total_board_feet__lt=500)
    ).order_by('quantity_pieces')
    
    if low_stock.exists():
        table_data = [['Product', 'Category', 'Current Stock (Pcs)', 'Board Feet', 'Urgency']]
        
        for inv in low_stock:
            pieces = inv.quantity_pieces
            if pieces == 0:
                urgency = 'CRITICAL'
            elif pieces < 20:
                urgency = 'HIGH'
            else:
                urgency = 'MEDIUM'
            
            table_data.append([
                inv.product.name,
                inv.product.category.name,
                f'{pieces:,}',
                f'{float(inv.total_board_feet):.2f}',
                urgency
            ])
        
        table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c41e3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ffe0e0')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.red),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph('No low stock items found - all products are well stocked', styles['Normal']))
    
    return elements


def _generate_stock_value_report(styles, title_style, subtitle_style, heading_style):
    """Generate stock value report elements"""
    elements = []
    
    elements.append(Paragraph('Stock Value Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Calculate stock value by category
    report = InventoryReports.stock_value_report()
    total_value = report['total_inventory_value']
    by_category = report['by_category']
    
    # Category value summary
    elements.append(Paragraph('Stock Value by Category', heading_style))
    
    cat_data = [['Category', 'Value', '% of Total', 'Product Count']]
    
    for cat_name, cat_data_item in sorted(by_category.items(), key=lambda x: x[1]['value'], reverse=True):
        cat_value = cat_data_item['value']
        percentage = (cat_value / total_value * 100) if total_value > 0 else 0
        product_count = len(cat_data_item['products'])
        
        cat_data.append([
            cat_name,
            f'₱{cat_value:,.2f}',
            f'{percentage:.1f}%',
            str(product_count)
        ])
    
    cat_table = Table(cat_data, colWidths=[2.5*inch, 2*inch, 1.5*inch, 1.5*inch])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Total value summary
    summary_para = Paragraph(f'<b>Total Inventory Value: ₱{total_value:,.2f}</b>', styles['Normal'])
    elements.append(summary_para)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Top value products
    elements.append(Paragraph('Top 15 Products by Stock Value', heading_style))
    
    all_products = []
    for cat_name, cat_data_item in by_category.items():
        for product in cat_data_item['products']:
            all_products.append({
                'name': product['product_name'],
                'bf': product['bf'],
                'price_per_bf': product['price_per_bf'],
                'value': product['value']
            })
    
    all_products.sort(key=lambda x: x['value'], reverse=True)
    
    prod_data = [['Product', 'Board Feet', 'Price/BF', 'Total Value']]
    
    for product in all_products[:15]:
        prod_data.append([
            product['name'],
            f"{product['bf']:.2f}",
            f"₱{product['price_per_bf']:.2f}",
            f"₱{product['value']:,.2f}"
        ])
    
    prod_table = Table(prod_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.8*inch])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(prod_table)
    
    return elements


def _generate_transactions_report(styles, title_style, subtitle_style, heading_style):
    """Generate stock transactions report elements"""
    elements = []
    
    elements.append(Paragraph('Stock Transactions Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Get all transactions
    transactions = StockTransaction.objects.select_related('product', 'created_by').order_by('-created_at')
    
    # Summary statistics
    total_in = StockTransaction.objects.filter(transaction_type='stock_in').count()
    total_out = StockTransaction.objects.filter(transaction_type='stock_out').count()
    total_adj = StockTransaction.objects.filter(transaction_type='adjustment').count()
    
    summary_data = [
        ['Stock In', 'Stock Out', 'Adjustments', 'Total'],
        [str(total_in), str(total_out), str(total_adj), str(total_in + total_out + total_adj)]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f0fe')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Detailed transactions table
    elements.append(Paragraph('Detailed Transaction History', heading_style))
    
    tx_data = [['Date', 'Time', 'Product', 'Type', 'Qty (Pcs)', 'Board Feet', 'Reference', 'User']]
    
    for tx in transactions[:100]:  # Limit to 100 most recent transactions
        tx_type_display = 'IN' if tx.transaction_type == 'stock_in' else 'OUT' if tx.transaction_type == 'stock_out' else 'ADJ'
        product_name = tx.product.name if tx.product else 'Unknown'
        tx_data.append([
            tx.created_at.strftime('%Y-%m-%d'),
            tx.created_at.strftime('%H:%M:%S'),
            product_name,
            tx_type_display,
            f'{tx.quantity_pieces:,}',
            f'{float(tx.board_feet):.2f}',
            tx.reference_id or tx.reason or '-',
            tx.created_by.username if tx.created_by else 'System'
        ])
    
    tx_table = Table(tx_data, colWidths=[1.1*inch, 0.9*inch, 1.5*inch, 0.7*inch, 0.9*inch, 1*inch, 1*inch, 1*inch])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(tx_table)
    
    return elements


def _generate_turnover_report(styles, title_style, subtitle_style, heading_style):
    """Generate inventory turnover report elements"""
    elements = []
    
    elements.append(Paragraph('Inventory Turnover Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} (Last 30 Days)', subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Calculate turnover for last 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    products = LumberProduct.objects.filter(is_active=True).annotate(
        stock_outs=Count(
            'stock_transactions',
            filter=Q(stock_transactions__transaction_type='stock_out',
                    stock_transactions__created_at__gte=cutoff_date)
        )
    ).filter(stock_outs__gt=0).order_by('-stock_outs')
    
    if products.exists():
        table_data = [['Product', 'Category', 'Units Sold', 'Avg Daily Sale', 'Turnover Status']]
        
        for product in products[:20]:
            avg_daily = product.stock_outs / 30
            if product.stock_outs > 50:
                status = 'Fast Moving'
            elif product.stock_outs > 20:
                status = 'Good'
            else:
                status = 'Slow'
            
            table_data.append([
                product.name,
                product.category.name if product.category else 'N/A',
                f'{product.stock_outs:,}',
                f'{avg_daily:.2f}',
                status
            ])
        
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.3*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph('No turnover data available for the last 30 days', styles['Normal']))
    
    return elements
