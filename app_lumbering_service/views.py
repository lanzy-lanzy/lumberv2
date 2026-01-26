from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count
from django.http import JsonResponse
from decimal import Decimal
from .models import (
    LumberingServiceOrder,
    LumberingServiceOutput,
    ShavingsRecord
)
from .serializers import (
    LumberingServiceOrderSerializer,
    LumberingServiceOutputSerializer,
    ShavingsRecordSerializer
)


class LumberingServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = LumberingServiceOrder.objects.all()
    serializer_class = LumberingServiceOrderSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark lumbering service order as completed"""
        order = self.get_object()
        order.status = 'completed'
        order.completed_date = timezone.now().date()
        order.calculate_service_fee()
        order.save()
        return Response({'status': 'Order marked as completed'})
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get summary of order with calculations"""
        order = self.get_object()
        outputs = order.outputs.all()
        total_bf = outputs.aggregate(Sum('board_feet'))['board_feet__sum'] or 0
        
        return Response({
            'id': order.id,
            'customer': order.customer.name,
            'status': order.status,
            'wood_type': order.wood_type,
            'logs': order.quantity_logs,
            'total_board_feet': total_bf,
            'service_fee_per_bf': order.service_fee_per_bf,
            'total_service_fee': order.total_service_fee,
            'output_count': outputs.count(),
            'shavings_ownership': order.shavings_ownership,
        })


class LumberingServiceOutputViewSet(viewsets.ModelViewSet):
    queryset = LumberingServiceOutput.objects.all()
    serializer_class = LumberingServiceOutputSerializer
    
    @action(detail=False, methods=['get'])
    def by_order(self, request):
        """Get all outputs for a specific order"""
        order_id = request.query_params.get('order_id')
        if order_id:
            outputs = LumberingServiceOutput.objects.filter(service_order_id=order_id)
            serializer = self.get_serializer(outputs, many=True)
            return Response(serializer.data)
        return Response({'error': 'order_id required'}, status=status.HTTP_400_BAD_REQUEST)


class ShavingsRecordViewSet(viewsets.ModelViewSet):
    queryset = ShavingsRecord.objects.all()
    serializer_class = ShavingsRecordSerializer
    
    @action(detail=False, methods=['get'])
    def by_order(self, request):
        """Get all shavings records for a specific order"""
        order_id = request.query_params.get('order_id')
        if order_id:
            shavings = ShavingsRecord.objects.filter(service_order_id=order_id)
            serializer = self.get_serializer(shavings, many=True)
            return Response(serializer.data)
        return Response({'error': 'order_id required'}, status=status.HTTP_400_BAD_REQUEST)


# Frontend Views for Admin Dashboard

@login_required
def lumbering_dashboard(request):
    """Main dashboard for lumbering service"""
    orders = LumberingServiceOrder.objects.all().prefetch_related('outputs', 'shavings')
    
    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'completed_orders': orders.filter(status='completed').count(),
        'total_board_feet': sum(order.actual_output_bf for order in orders),
        'total_service_fees': sum(order.total_service_fee or 0 for order in orders),
    }
    
    return render(request, 'lumbering_service/dashboard.html', {
        'orders': orders,
        'stats': stats,
    })


@login_required
def lumbering_order_list(request):
    """List all lumbering service orders"""
    status_filter = request.GET.get('status')
    orders = LumberingServiceOrder.objects.all().prefetch_related('outputs')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    return render(request, 'lumbering_service/order_list.html', {
        'orders': orders,
        'status_filter': status_filter,
    })


@login_required
def lumbering_order_detail(request, pk):
    """View detailed information about a lumbering service order"""
    order = get_object_or_404(LumberingServiceOrder, pk=pk)
    outputs = order.outputs.all()
    shavings = order.shavings.all()
    
    context = {
        'order': order,
        'outputs': outputs,
        'shavings': shavings,
        'total_bf': sum(o.board_feet for o in outputs),
    }
    return render(request, 'lumbering_service/order_detail.html', context)


@login_required
def lumbering_order_create(request):
    """Create a new lumbering service order"""
    from app_round_wood.models import WoodType
    from app_sales.models import Customer

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        wood_type = request.POST.get('wood_type')
        quantity_logs = request.POST.get('quantity_logs')
        estimated_bf = request.POST.get('estimated_board_feet')
        service_fee = request.POST.get('service_fee_per_bf')
        shavings_ownership = request.POST.get('shavings_ownership')
        notes = request.POST.get('notes')
        
        # Validate customer selection
        if not customer_id or customer_id == '':
            return render(request, 'lumbering_service/order_create.html', {
                'customers': Customer.objects.all(),
                'wood_types': WoodType.objects.filter(is_active=True),
                'error': 'Please select or create a customer before proceeding.'
            })
        
        customer = get_object_or_404(Customer, pk=customer_id)
        
        order = LumberingServiceOrder.objects.create(
            customer=customer,
            wood_type=wood_type,
            quantity_logs=int(quantity_logs),
            estimated_board_feet=estimated_bf or None,
            service_fee_per_bf=service_fee or '5.00',
            shavings_ownership=shavings_ownership,
            notes=notes,
            created_by=request.user,
        )
        
        return redirect('lumbering_service:order_detail', pk=order.pk)
    
    customers = Customer.objects.all()
    wood_types = WoodType.objects.filter(is_active=True)
    
    return render(request, 'lumbering_service/order_create.html', {
        'customers': customers,
        'wood_types': wood_types,
    })


@login_required
def lumbering_output_create(request, order_pk):
    """Add lumber output to a service order"""
    order = get_object_or_404(LumberingServiceOrder, pk=order_pk)
    
    if request.method == 'POST':
        lumber_type = request.POST.get('lumber_type')
        quantity = request.POST.get('quantity_pieces')
        length_feet = request.POST.get('length_feet')
        width_inches = request.POST.get('width_inches')
        thickness_inches = request.POST.get('thickness_inches')
        grade = request.POST.get('grade')
        notes = request.POST.get('notes')
        
        output = LumberingServiceOutput.objects.create(
            service_order=order,
            lumber_type=lumber_type,
            quantity_pieces=int(quantity),
            length_feet=Decimal(length_feet),
            width_inches=Decimal(width_inches),
            thickness_inches=Decimal(thickness_inches),
            grade=grade or 'common1',
            notes=notes,
        )
        
        return redirect('lumbering_service:order_detail', pk=order.pk)
    
    return render(request, 'lumbering_service/output_create.html', {
        'order': order,
    })


@login_required
def lumbering_shavings_create(request, order_pk):
    """Record shavings from lumbering service"""
    order = get_object_or_404(LumberingServiceOrder, pk=order_pk)
    
    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        notes = request.POST.get('notes')
        
        shavings = ShavingsRecord.objects.create(
            service_order=order,
            quantity=quantity,
            unit=unit,
            notes=notes,
        )
        
        return redirect('lumbering_service:order_detail', pk=order.pk)
    
    return render(request, 'lumbering_service/shavings_create.html', {
        'order': order,
    })


from django.utils import timezone
from django.http import HttpResponseRedirect


@login_required
def lumbering_order_mark_completed(request, pk):
    """Mark a lumbering service order as completed"""
    if request.method == 'POST':
        order = get_object_or_404(LumberingServiceOrder, pk=pk)
        order.status = 'completed'
        order.completed_date = timezone.now().date()
        order.calculate_service_fee()
        order.save()
    
    return redirect('lumbering_service:order_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def create_walkin_customer(request):
    """Create a new walk-in customer for lumbering service"""
    from app_sales.models import Customer
    from django.db import IntegrityError
    
    try:
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Validation
        if not name:
            return JsonResponse({'message': 'Customer name is required'}, status=400)
        if not phone_number:
            return JsonResponse({'message': 'Phone number is required'}, status=400)
        
        # Check for duplicate email
        if email and Customer.objects.filter(email=email).exists():
            return JsonResponse({'message': 'A customer with this email already exists'}, status=400)
        
        # Create customer
        customer = Customer.objects.create(
            name=name,
            phone_number=phone_number,
            email=email or None,
            address=address or '',
        )
        
        return JsonResponse({
            'id': customer.id,
            'name': customer.name,
            'phone_number': customer.phone_number,
        }, status=201)
    
    except IntegrityError as e:
        # Fallback for any other integrity errors
        if 'email' in str(e):
            return JsonResponse({'message': 'A customer with this email already exists'}, status=400)
        return JsonResponse({'message': f'Error creating customer: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'message': f'Error creating customer: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def create_wood_type(request):
    """Create a new wood type for lumbering service"""
    from app_round_wood.models import WoodType
    
    try:
        name = request.POST.get('name', '').strip()
        species = request.POST.get('species', 'hardwood').strip()
        description = request.POST.get('description', '').strip()
        
        # Validation
        if not name:
            return JsonResponse({'message': 'Wood type name is required'}, status=400)
        
        # Check if already exists
        if WoodType.objects.filter(name__iexact=name).exists():
            return JsonResponse({'message': 'This wood type already exists'}, status=400)
            
        # Create wood type
        wood_type = WoodType.objects.create(
            name=name,
            species=species,
            description=description,
            is_active=True
        )
        
        return JsonResponse({
            'id': wood_type.id,
            'name': wood_type.name,
        }, status=201)
    
    except Exception as e:
        return JsonResponse({'message': f'Error creating wood type: {str(e)}'}, status=500)
