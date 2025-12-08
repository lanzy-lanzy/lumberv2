from django.core.management.base import BaseCommand
from django.utils import timezone
from app_inventory.models import Inventory, InventorySnapshot


class Command(BaseCommand):
    help = 'Create daily inventory snapshots for historical tracking'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        created_count = 0
        
        for inventory in Inventory.objects.all():
            snapshot, created = InventorySnapshot.objects.get_or_create(
                product=inventory.product,
                snapshot_date=today,
                defaults={
                    'quantity_pieces': inventory.quantity_pieces,
                    'total_board_feet': inventory.total_board_feet,
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} inventory snapshots for {today}')
        )
