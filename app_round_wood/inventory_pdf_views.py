from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from .models import RoundWoodInventory


@login_required
def export_inventory_pdf(request):
    """Export round wood inventory to PDF"""
    
    # Get inventory data
    inventory = RoundWoodInventory.objects.select_related("wood_type").order_by(
        "wood_type__name"
    )
    
    # Summary
    summary = RoundWoodInventory.objects.aggregate(
        total_logs=Sum("total_logs_in_stock"),
        total_volume=Sum("total_cubic_feet_in_stock"),
        total_cost=Sum("total_cost_invested"),
    )
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4), 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch
    )
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
    elements.append(Paragraph('Round Wood Inventory Report', title_style))
    
    # Report details
    report_info = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.15*inch))
    
    # Summary statistics
    total_logs = summary['total_logs'] or 0
    total_volume = summary['total_volume'] or 0
    total_cost = summary['total_cost'] or 0
    
    summary_data = [
        [
            f'Total Wood Types: {inventory.count()}',
            f'Total Logs: {total_logs}',
            f'Total Volume: {float(total_volume):,.2f} cu ft',
            f'Total Invested: ₱{float(total_cost):,.2f}'
        ]
    ]
    summary_table = Table(
        summary_data, 
        colWidths=[2.5*inch, 2*inch, 2.5*inch, 2.5*inch]
    )
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
    
    # Inventory table
    table_data = [
        ['Wood Type', 'Species', 'Logs in Stock', 'Volume (cu ft)', 'Avg Cost/cu ft', 'Total Cost', 'Last Updated']
    ]
    
    for item in inventory:
        table_data.append([
            item.wood_type.name,
            item.wood_type.get_species_display(),
            str(item.total_logs_in_stock),
            f"{float(item.total_cubic_feet_in_stock):,.2f}",
            f"₱{float(item.average_cost_per_cubic_foot):,.2f}",
            f"₱{float(item.total_cost_invested):,.2f}",
            item.last_stock_in_date.strftime('%m/%d/%Y') if item.last_stock_in_date else 'Never',
        ])
    
    # Create table
    table = Table(
        table_data, 
        colWidths=[1.8*inch, 1.3*inch, 1*inch, 1.2*inch, 1.2*inch, 1.3*inch, 1*inch]
    )
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
        ('ALIGN', (0, 1), (2, -1), 'LEFT'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    
    filename = f"round_wood_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
