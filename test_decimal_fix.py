#!/usr/bin/env python
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumber.settings')
django.setup()

from app_round_wood.models import RoundWoodPurchase, WoodType
from app_supplier.models import Supplier
from core.models import CustomUser

# Get or create test data
supplier = Supplier.objects.first()
wood_type = WoodType.objects.first()
user = CustomUser.objects.filter(is_staff=True).first()

if supplier and wood_type and user:
    # Test creating a purchase with dimensions
    purchase = RoundWoodPurchase(
        supplier=supplier,
        wood_type=wood_type,
        quantity_logs=5,
        length_inches=Decimal("120"),
        width_inches=Decimal("8"),
        thickness_inches=Decimal("4"),
        unit_cost_per_board_feet=Decimal("2.50"),
        created_by=user,
        status="completed",
    )
    
    try:
        purchase.save()
        print("SUCCESS: Purchase created successfully!")
        print(f"  Board Feet: {purchase.board_feet}")
        print(f"  Total Cost: {purchase.total_cost}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("Missing test data (supplier, wood_type, or user)")
