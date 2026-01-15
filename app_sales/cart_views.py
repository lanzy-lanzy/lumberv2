from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from app_sales.models import ShoppingCart, CartItem
from app_sales.serializers import ShoppingCartSerializer, CartItemSerializer
from app_inventory.models import LumberProduct


class ShoppingCartViewSet(viewsets.ViewSet):
    """API endpoints for shopping cart operations"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        """Get current user's shopping cart"""
        cart, created = ShoppingCart.objects.get_or_create(user=request.user)
        serializer = ShoppingCartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response(
                    {'error': 'quantity must be at least 1'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'quantity must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = LumberProduct.objects.get(id=product_id, is_active=True)
        except LumberProduct.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check inventory
        inventory = getattr(product, 'inventory', None)
        if not inventory or inventory.quantity_pieces < quantity:
            available = inventory.quantity_pieces if inventory else 0
            return Response(
                {'error': f'Insufficient stock. Available: {available}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            cart, created = ShoppingCart.objects.get_or_create(user=request.user)
            
            # Add or update cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                # If item already exists, add to quantity
                cart_item.quantity += quantity
                
                # Check if total quantity exceeds stock
                if inventory.quantity_pieces < cart_item.quantity:
                    return Response(
                        {'error': f'Cannot add {quantity} more. Only {inventory.quantity_pieces - (cart_item.quantity - quantity)} available'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                cart_item.save()
        
        cart.refresh_from_db()
        serializer = ShoppingCartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update quantity of item in cart"""
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or quantity is None:
            return Response(
                {'error': 'item_id and quantity are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            if quantity < 0:
                return Response(
                    {'error': 'quantity must be 0 or greater'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'quantity must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart = ShoppingCart.objects.get(user=request.user)
            item = CartItem.objects.get(id=item_id, cart=cart)
        except (ShoppingCart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # If quantity is 0, delete the item
        if quantity == 0:
            item.delete()
        else:
            # Check inventory
            inventory = getattr(item.product, 'inventory', None)
            if not inventory or inventory.quantity_pieces < quantity:
                available = inventory.quantity_pieces if inventory else 0
                return Response(
                    {'error': f'Insufficient stock. Available: {available}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            item.quantity = quantity
            item.save()
        
        cart.refresh_from_db()
        serializer = ShoppingCartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Remove item from cart"""
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response(
                {'error': 'item_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart = ShoppingCart.objects.get(user=request.user)
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
        except (ShoppingCart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart.refresh_from_db()
        serializer = ShoppingCartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def clear_cart(self, request):
        """Clear all items from cart"""
        try:
            cart = ShoppingCart.objects.get(user=request.user)
            cart.clear()
        except ShoppingCart.DoesNotExist:
            pass
        
        cart, created = ShoppingCart.objects.get_or_create(user=request.user)
        serializer = ShoppingCartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Create a sales order from cart or update existing order if editing"""
        from app_sales.models import Customer, SalesOrder, SalesOrderItem
        from app_sales.services import SalesService
        
        try:
            cart = ShoppingCart.objects.get(user=request.user)
        except ShoppingCart.DoesNotExist:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if cart.items.count() == 0:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if we're editing an existing order
        editing_order_id = request.session.get('editing_order_id')
        
        if editing_order_id:
            # UPDATE existing order
            try:
                with transaction.atomic():
                    # Get the existing order
                    order = SalesOrder.objects.get(id=editing_order_id)
                    
                    # Verify ownership
                    if order.customer.email != request.user.email:
                        return Response(
                            {'error': 'You do not have permission to edit this order'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
                    # Check if order is confirmed
                    if order.is_confirmed:
                        return Response(
                            {'error': 'Cannot edit a confirmed order'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
                    # Delete existing order items
                    order.sales_order_items.all().delete()
                    
                    # Add new items from cart
                    total_amount = Decimal('0')
                    for cart_item in cart.items.all():
                        product = cart_item.product
                        quantity_pieces = cart_item.quantity
                        
                        # Calculate using product's method (same as create_sales_order)
                        board_feet = Decimal(str(product.calculate_board_feet(quantity_pieces)))
                        unit_price = product.price_per_board_foot
                        subtotal = board_feet * unit_price
                        
                        SalesOrderItem.objects.create(
                            sales_order=order,
                            product=product,
                            quantity_pieces=quantity_pieces,
                            unit_price=unit_price,
                            board_feet=board_feet,
                            subtotal=subtotal
                        )
                        total_amount += subtotal
                    
                    # Update order totals and save
                    order.total_amount = total_amount
                    order.save()  # Save first to persist total_amount
                    
                    # Recalculate discount and balance (important for partial payments!)
                    order.apply_discount()  # This recalculates balance even if no discount
                    order.save()
                    
                    # Clear session and cart
                    del request.session['editing_order_id']
                    cart.clear()
                    
                    from app_sales.serializers import SalesOrderSerializer
                    serializer = SalesOrderSerializer(order)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                    
            except SalesOrder.DoesNotExist:
                # Order was deleted, fall through to create new order
                if 'editing_order_id' in request.session:
                    del request.session['editing_order_id']
            except Exception as e:
                return Response(
                    {'error': f'Error updating order: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # CREATE new order (original logic)
        # Get or create customer from user email
        customer_email = request.user.email if request.user.email else None
        
        if customer_email:
            customer, created = Customer.objects.get_or_create(
                email=customer_email,
                defaults={
                    'name': request.user.get_full_name() or request.user.username,
                    'phone_number': getattr(request.user, 'phone_number', ''),
                }
            )
        else:
            # If no email, create without using email as lookup
            customer, created = Customer.objects.get_or_create(
                name=request.user.get_full_name() or request.user.username,
                defaults={
                    'email': '',
                    'phone_number': getattr(request.user, 'phone_number', ''),
                }
            )
        
        # Prepare items for sales order
        items = []
        for cart_item in cart.items.all():
            items.append({
                'product_id': cart_item.product.id,
                'quantity_pieces': cart_item.quantity,
            })
        
        payment_type = request.data.get('payment_type', 'cash')
        
        try:
            with transaction.atomic():
                # Create sales order - customer_order is automatically set for cart checkouts
                so = SalesService.create_sales_order(
                    customer_id=customer.id,
                    items=items,
                    payment_type=payment_type,
                    created_by=request.user,
                    order_source='customer_order'
                )
                
                # Clear cart after successful order
                cart.clear()
                
                from app_sales.serializers import SalesOrderSerializer
                serializer = SalesOrderSerializer(so)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
