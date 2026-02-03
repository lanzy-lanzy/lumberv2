from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from app_sales.models import ShoppingCart, CartItem, SalesOrder, Customer
from app_inventory.models import LumberProduct, LumberCategory

User = get_user_model()


class CheckoutTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123",
            user_type='customer'
        )

        # Create test product
        self.product = LumberProduct.objects.create(
            name="Test Lumber",
            category=LumberCategory.objects.create(name="Test Category"),
            thickness=2,
            width=4,
            length=10,
            price_per_board_foot=10.0,
            price_per_piece=50.0,
            sku="TEST-SKU"
        )
        from app_inventory.models import Inventory
        Inventory.objects.create(product=self.product, quantity_pieces=100, total_board_feet=1000)

        # Create test customer
        self.customer = Customer.objects.create(
            email="test@example.com", name="Test User"
        )

        # Create confirmed order
        self.confirmed_order = SalesOrder.objects.create(
            customer=self.customer,
            so_number="SO-001",
            total_amount=100.0,
            is_confirmed=True,
            created_by=self.user,
        )

    def test_checkout_with_confirmed_order_in_session(self):
        """Test that checkout works when confirmed order ID is in session"""
        # Log in user
        self.client.login(username="testuser", password="testpass123")

        # Set up session with confirmed order ID
        session = self.client.session
        session["editing_order_id"] = str(self.confirmed_order.id)
        session.save()

        # Get shopping cart (created via signal for customers)
        cart, _ = ShoppingCart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        # Attempt checkout - should succeed and create new order
        response = self.client.post(
            "/api/cart/checkout/",
            {"payment_type": "cash"},
            content_type="application/json",
        )

        # Should succeed (201 or 200)
        self.assertIn(response.status_code, [200, 201])

        # Session should be cleared of editing_order_id
        session = self.client.session
        self.assertNotIn("editing_order_id", session)

        # Should have created a new order (not updated the confirmed one)
        new_orders = SalesOrder.objects.filter(
            customer=self.customer, is_confirmed=False
        ).count()
        self.assertGreater(new_orders, 0)

    def test_cannot_edit_confirmed_order_directly(self):
        """Test that direct attempt to edit confirmed order fails"""
        # Log in user
        self.client.login(username="testuser", password="testpass123")

        # Try to load confirmed order for editing
        response = self.client.get(
            f"/customer/cart/?edit_order={self.confirmed_order.id}"
        )

        # Should redirect to my-orders with error message
        self.assertEqual(response.status_code, 302)

        # Check that error message was set
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("confirmed and cannot be edited" in str(msg) for msg in messages)
        )
    def test_order_total_with_price_per_piece(self):
        """Test that order total is correct for products with price_per_piece"""
        # Create a product where BF-based price would be different from piece-based price
        # Dimensions: 2x5x8 = 6.67 BF
        # Price per BF = 100 -> BF price = 666.67
        # Price per piece = 280 -> Piece price = 280
        ppp_product = LumberProduct.objects.create(
            name="Piece Price Product",
            category=self.product.category,
            thickness=2,
            width=5,
            length=8,
            price_per_board_foot=100.0,
            price_per_piece=280.0,
            sku="PPP-001"
        )
        from app_inventory.models import Inventory
        Inventory.objects.create(product=ppp_product, quantity_pieces=100, total_board_feet=1000)
        
        from app_sales.services import SalesService
        items = [{"product_id": ppp_product.id, "quantity_pieces": 2}]
        
        # Create order
        so = SalesService.create_sales_order(
            customer_id=self.customer.id,
            items=items,
            payment_type='cash',
            created_by=self.user,
            order_source='customer_order'
        )
        
        # Total should be 280 * 2 = 560.00
        self.assertEqual(float(so.total_amount), 560.00)
        
        # Verify line item
        item = so.sales_order_items.first()
        self.assertEqual(float(item.unit_price), 280.00)
        self.assertEqual(float(item.subtotal), 560.00)
