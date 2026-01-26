from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from app_supplier.models import Supplier
from core.models import CustomUser


class WoodType(models.Model):
    """Types of round wood (logs) available for purchase"""

    SPECIES_CHOICES = [
        ("hardwood", "Hardwood"),
        ("softwood", "Softwood"),
        ("tropical", "Tropical"),
        ("mixed", "Mixed Species"),
    ]

    name = models.CharField(max_length=200, unique=True)
    species = models.CharField(max_length=50, choices=SPECIES_CHOICES)
    description = models.TextField(blank=True)

    # Standard measurements for this wood type
    default_diameter_inches = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Default log diameter in inches",
    )
    default_length_feet = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Default log length in feet",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Wood Types"

    def __str__(self):
        return f"{self.name} ({self.get_species_display()})"


class RoundWoodPurchase(models.Model):
    """SIMPLIFIED: Single-user direct purchase record for round wood (logs)"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    # Supplier information
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="round_wood_purchases"
    )

    # Wood details
    wood_type = models.ForeignKey(
        WoodType, on_delete=models.PROTECT, related_name="purchases"
    )

    quantity_logs = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Number of logs purchased"
    )

    diameter_inches = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Average log diameter in inches",
    )

    length_feet = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Average log length in feet",
    )

    # Dimensions for board feet calculation (L × W × T / 12)
    length_inches = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Length in inches for board feet calculation",
    )
    width_inches = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Width in inches for board feet calculation",
    )
    thickness_inches = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Thickness in inches for board feet calculation",
    )

    # Board feet (calculated: L × W × T / 12)
    board_feet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
        help_text="Total board feet (L × W × T / 12)",
    )

    # Volume (calculated and stored)
    volume_cubic_feet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
        help_text="Total volume in cubic feet",
    )

    # Financial
    unit_cost_per_board_feet = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal("0"),
        help_text="Cost per board foot",
    )

    total_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total purchase cost",
    )

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    purchase_date = models.DateField(default=timezone.now)

    # Notes
    notes = models.TextField(blank=True)

    # Audit trail
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="round_wood_purchases_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchase_date", "-created_at"]
        verbose_name = "Round Wood Purchase"
        verbose_name_plural = "Round Wood Purchases"
        indexes = [
            models.Index(fields=["supplier", "-purchase_date"]),
            models.Index(fields=["status", "-purchase_date"]),
            models.Index(fields=["wood_type", "-purchase_date"]),
        ]

    def __str__(self):
        return f"{self.wood_type.name} - {self.quantity_logs} logs - {self.supplier.company_name}"

    def calculate_board_feet(self):
        """Calculate board feet using formula: L × W × T / 12"""
        if self.length_inches and self.width_inches and self.thickness_inches:
            return Decimal(
                str(float(self.length_inches)
                * float(self.width_inches)
                * float(self.thickness_inches)
                / 12)
            )
        return Decimal("0")

    def calculate_volume(self):
        """Calculate volume using log formula"""
        import math

        diameter_feet = float(self.diameter_inches) / 12
        radius_feet = diameter_feet / 2
        volume_per_log = math.pi * (radius_feet**2) * float(self.length_feet)
        total_volume = volume_per_log * self.quantity_logs
        return Decimal(str(total_volume))

    def save(self, *args, **kwargs):
        """Calculate board feet and total cost before saving"""
        # Calculate board feet if dimensions are provided
        if self.length_inches and self.width_inches and self.thickness_inches:
            self.board_feet = self.calculate_board_feet()
        else:
            self.board_feet = Decimal("0")

        # Calculate total cost using board feet price (ensure both are Decimal)
        self.total_cost = Decimal(str(self.board_feet)) * Decimal(str(self.unit_cost_per_board_feet))

        super().save(*args, **kwargs)

        # Update inventory if completed
        if self.status == "completed":
            self._update_inventory()

    def mark_completed(self):
        """Mark purchase as completed and update inventory"""
        self.status = "completed"
        self.save()

    def _update_inventory(self):
        """Update RoundWoodInventory when purchase is completed"""
        inventory, created = RoundWoodInventory.objects.get_or_create(
            wood_type=self.wood_type
        )

        inventory.total_logs_in_stock += int(self.quantity_logs)
        inventory.total_cubic_feet_in_stock += Decimal(str(self.volume_cubic_feet))
        inventory.total_cost_invested += Decimal(str(self.total_cost))

        # Recalculate average cost
        if inventory.total_cubic_feet_in_stock > 0:
            inventory.average_cost_per_cubic_foot = (
                inventory.total_cost_invested / inventory.total_cubic_feet_in_stock
            )

        inventory.last_stock_in_date = timezone.now().date()
        inventory.save()


class RoundWoodInventory(models.Model):
    """Tracks stocked round wood in inventory"""

    wood_type = models.OneToOneField(
        WoodType, on_delete=models.CASCADE, related_name="round_wood_inventory"
    )

    # Current stock
    total_logs_in_stock = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )

    total_cubic_feet_in_stock = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    # Cost tracking
    total_cost_invested = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total cost of all stocked round wood",
    )

    average_cost_per_cubic_foot = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    # Warehouse location
    warehouse_location = models.CharField(
        max_length=200, blank=True, help_text="e.g., Yard A, Section B, Stack 3"
    )

    last_updated = models.DateTimeField(auto_now=True)
    last_stock_in_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Round Wood Inventory"
        verbose_name_plural = "Round Wood Inventories"

    def __str__(self):
        return f"{self.wood_type.name} - {self.total_logs_in_stock} logs"
