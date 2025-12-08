from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

# Role choices for users
ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('inventory_manager', 'Inventory Manager'),
    ('cashier', 'Cashier'),
    ('warehouse_staff', 'Warehouse Staff'),
]


class CustomUser(AbstractUser):
    """Extended User model with role-based access control"""
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='warehouse_staff'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def is_admin(self):
        return self.role == 'admin'

    def is_inventory_manager(self):
        return self.role == 'inventory_manager'

    def is_cashier(self):
        return self.role == 'cashier'

    def is_warehouse_staff(self):
        return self.role == 'warehouse_staff'
