from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app_sales.models import (
    ShoppingCart,
    CartItem,
    SalesOrder,
    SalesOrderItem,
    Customer,
)
from app_sales.serializers import ShoppingCartSerializer, CartItemSerializer
from app_sales.services import SalesService


class ShoppingCartViewSet(ModelViewSet):
    """API for managing shopping cart"""

    serializer_class = ShoppingCartSerializer
    queryset = ShoppingCart.objects.all()

    def get_queryset(self):
        """Filter by current user"""
        if self.request.user.is_authenticated:
            return ShoppingCart.objects.filter(user=self.request.user)
        return ShoppingCart.objects.none()

    @action(detail=False, methods=["get"])
    def my_cart(self, request):
        """Get current user's shopping cart"""
        try:
            cart, created = ShoppingCart.objects.get_or_create(user=request.user)
            serializer = ShoppingCartSerializer(cart)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": f"Error retrieving cart: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def add_to_cart(self, request):
        """Add item to shopping cart"""
        try:
            cart, created = ShoppingCart.objects.get_or_create(user=request.user)

            product_id = request.data.get("product_id")
            quantity = request.data.get("quantity", 1)

            if not product_id:
                return Response(
                    {"error": "Product ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if item already exists in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, product_id=product_id, defaults={"quantity": quantity}
            )

            if not created:
                # Update quantity if item already exists
                cart_item.quantity += quantity
                cart_item.save()

            serializer = ShoppingCartSerializer(cart)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"Error adding to cart: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def update_cart_item(self, request):
        """Update quantity of item in cart"""
        try:
            cart = ShoppingCart.objects.get(user=request.user)

            product_id = request.data.get("product_id")
            quantity = request.data.get("quantity")

            if not product_id or quantity is None:
                return Response(
                    {"error": "Product ID and quantity are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)

                if quantity <= 0:
                    cart_item.delete()
                else:
                    cart_item.quantity = quantity
                    cart_item.save()

                serializer = ShoppingCartSerializer(cart)
                return Response(serializer.data)

            except CartItem.DoesNotExist:
                return Response(
                    {"error": "Item not found in cart"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": f"Error updating cart: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def remove_from_cart(self, request):
        """Remove item from shopping cart"""
        try:
            cart = ShoppingCart.objects.get(user=request.user)

            product_id = request.data.get("product_id")

            if not product_id:
                return Response(
                    {"error": "Product ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                cart_item.delete()

                serializer = ShoppingCartSerializer(cart)
                return Response(serializer.data)

            except CartItem.DoesNotExist:
                return Response(
                    {"error": "Item not found in cart"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": f"Error removing from cart: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def clear_cart(self, request):
        """Clear all items from shopping cart"""
        try:
            cart = ShoppingCart.objects.get(user=request.user)
            cart.items.all().delete()

            serializer = ShoppingCartSerializer(cart)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"Error clearing cart: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """Create a sales order from cart or update existing order if editing"""
        try:
            cart = ShoppingCart.objects.get(user=request.user)
        except ShoppingCart.DoesNotExist:
            return Response(
                {"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if cart.items.count() == 0:
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if we're editing an existing order
        editing_order_id = request.session.get("editing_order_id")
        should_create_new_order = False

        if editing_order_id:
            # UPDATE existing order
            try:
                with transaction.atomic():
                    # Get the existing order
                    order = SalesOrder.objects.get(id=editing_order_id)

                    # Verify ownership
                    if order.customer.email != request.user.email:
                        return Response(
                            {"error": "You do not have permission to edit this order"},
                            status=status.HTTP_403_FORBIDDEN,
                        )

                    # Check if order is confirmed
                    if order.is_confirmed:
                        # Clean up the stale editing_order_id from session and create new order instead
                        del request.session["editing_order_id"]
                        request.session.modified = True
                        should_create_new_order = True
                    else:
                        # Prepare items for updating
                        items = []
                        for cart_item in cart.items.all():
                            items.append({
                                "product_id": cart_item.product.id,
                                "quantity_pieces": cart_item.quantity,
                            })

                        # Use SalesService to update the order
                        order = SalesService.update_sales_order(
                            sales_order_id=editing_order_id,
                            items=items,
                            created_by=request.user
                        )

                        # Clear session and cart
                        if "editing_order_id" in request.session:
                            del request.session["editing_order_id"]
                        cart.clear()

                        from app_sales.serializers import SalesOrderSerializer
                        serializer = SalesOrderSerializer(order)
                        return Response(serializer.data, status=status.HTTP_200_OK)

            except SalesOrder.DoesNotExist:
                # Order was deleted, fall through to create new order
                if "editing_order_id" in request.session:
                    del request.session["editing_order_id"]
                should_create_new_order = True
            except Exception as e:
                return Response(
                    {"error": f"Error updating order: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # CREATE new order (original logic)
        # Get or create customer using improved lookup logic
        customer = None
        customer_email = request.user.email if request.user.email else None

        if customer_email:
            try:
                customer, created = Customer.objects.get_or_create(
                    email=customer_email,
                    defaults={
                        "name": request.user.get_full_name() or request.user.username,
                        "phone_number": getattr(request.user, "phone_number", ""),
                    },
                )
            except Exception:
                # If get_or_create fails due to constraint, try to get existing customer
                try:
                    customer = Customer.objects.get(email=customer_email)
                except Customer.DoesNotExist:
                    # If customer doesn't exist, create with a generated identifier to avoid constraint
                    customer = Customer.objects.create(
                        name=request.user.get_full_name() or request.user.username,
                        phone_number=getattr(request.user, "phone_number", ""),
                        email=None,
                    )
        
        if not customer:
            # If no email, try to find existing customer by name (don't create a new one!)
            full_name = request.user.get_full_name()
            if full_name:
                customer = Customer.objects.filter(
                    name=full_name
                ).order_by('-updated_at').first()  # Get most recently updated one
        
        if not customer:
            # Only create a new customer if none exists by name
            customer = Customer.objects.create(
                name=request.user.get_full_name() or request.user.username,
                phone_number=getattr(request.user, "phone_number", ""),
                email=None,
            )

        # Prepare items for sales order
        items = []
        for cart_item in cart.items.all():
            items.append(
                {
                    "product_id": cart_item.product.id,
                    "quantity_pieces": cart_item.quantity,
                }
            )

        payment_type = request.data.get("payment_type", "cash")

        try:
            with transaction.atomic():
                # Create sales order - customer_order is automatically set for cart checkouts
                so = SalesService.create_sales_order(
                    customer_id=customer.id,
                    items=items,
                    payment_type=payment_type,
                    created_by=request.user,
                    order_source="customer_order",
                )

                # Clear cart after successful order
                cart.clear()

                from app_sales.serializers import SalesOrderSerializer

                serializer = SalesOrderSerializer(so)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
