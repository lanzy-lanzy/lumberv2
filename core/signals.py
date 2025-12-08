"""Signal handlers for core app"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import CustomUser


@receiver(post_save, sender=CustomUser)
def user_created(sender, instance, created, **kwargs):
    """Handle user creation"""
    if created:
        print(f"User {instance.username} created with role: {instance.role}")
