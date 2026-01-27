import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append('c:/Users/gerla/revision/lumber')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumber.settings')
django.setup()

from app_inventory.models import LumberProduct, LumberCategory, Inventory
from app_sales.models import Customer, SalesOrder
from app_sales.services import SalesService

def test_calculations():
    print("Starting calculation tests...")
    
    # Create or get a category
    category = LumberCategory.objects.filter(name="Calculations Test Category").first()
    if not category:
        category = LumberCategory.objects.create(name="Calculations Test Category")
    
    # Create or get a customer
    customer = Customer.objects.filter(email="calc@example.com").first()
    if not customer:
        customer = Customer.objects.create(
            name="Test Calc Customer",
            email="calc@example.com",
            phone_number="1234567"
        )
    
    import time
    ts = int(time.time())
    
    # 1. Test Piece Pricing
    print("\nProcessing Piece Pricing Test...")
    product_piece = LumberProduct.objects.create(
        name="Piece Priced Lumber",
        category=category,
        thickness=1,
        width=4,
        length=10,
        price_per_board_foot=Decimal("10.00"),
        price_per_piece=Decimal("50.00"),
        sku=f"SKU-PIECE-{ts}"
    )
    
    # INITIALIZE INVENTORY
    Inventory.objects.create(
        product=product_piece,
        quantity_pieces=100,
        total_board_feet=Decimal("1000.00")
    )
    
    items = [
        {'product_id': product_piece.id, 'quantity_pieces': 2}
    ]
    
    so = SalesService.create_sales_order(
        customer_id=customer.id,
        items=items,
        payment_type='cash',
        order_source='point_of_sale'
    )
    
    print(f"Order {so.so_number} Total: {so.total_amount}")
    expected_piece = Decimal("100.00")
    if so.total_amount == expected_piece:
        print("✅ Piece pricing calculation correct!")
    else:
        print(f"❌ Piece pricing calculation WRONG! Expected {expected_piece}, got {so.total_amount}")

    # 2. Test Board Foot Pricing
    print("\nProcessing Board Foot Pricing Test...")
    product_bf = LumberProduct.objects.create(
        name="BF Priced Lumber",
        category=category,
        thickness=2,
        width=6,
        length=12,
        price_per_board_foot=Decimal("20.00"),
        price_per_piece=None,
        sku=f"SKU-BF-{ts}"
    )
    
    # INITIALIZE INVENTORY
    Inventory.objects.create(
        product=product_bf,
        quantity_pieces=100,
        total_board_feet=Decimal("1200.00")
    )
    
    # BF for 2x6x12 = (2 * 6 * 12) / 12 = 12 BF
    # For 2 pieces = 24 BF
    # Total = 24 * 20 = 480
    
    items_bf = [
        {'product_id': product_bf.id, 'quantity_pieces': 2}
    ]
    
    so_bf = SalesService.create_sales_order(
        customer_id=customer.id,
        items=items_bf,
        payment_type='cash',
        order_source='point_of_sale'
    )
    
    print(f"Order {so_bf.so_number} Total: {so_bf.total_amount}")
    expected_bf = Decimal("480.00")
    if so_bf.total_amount == expected_bf:
        print("✅ Board foot pricing calculation correct!")
    else:
        print(f"❌ Board foot pricing calculation WRONG! Expected {expected_bf}, got {so_bf.total_amount}")

    # Cleanup
    product_piece.delete()
    product_bf.delete()
    so.delete()
    so_bf.delete()
    print("\nTests complete and cleaned up.")

if __name__ == "__main__":
    test_calculations()
