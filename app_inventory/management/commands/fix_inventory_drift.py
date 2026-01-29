from django.core.management.base import BaseCommand
from app_inventory.services import InventoryService

class Command(BaseCommand):
    help = 'Recalculates total board feet for all inventory items based on current piece count and product dimensions.'

    def handle(self, *args, **options):
        self.stdout.write('Starting inventory recalculation...')
        
        results = InventoryService.recalculate_inventory_stats()
        
        if not results:
            self.stdout.write(self.style.SUCCESS('No drift detected. Inventory is consistent.'))
        else:
            for res in results:
                self.stdout.write(
                    self.style.WARNING(
                        f"Fixed {res['product']}: {res['old_bf']} BF -> {res['new_bf']} BF"
                    )
                )
            self.stdout.write(self.style.SUCCESS(f'Successfully recalculated {len(results)} items.'))
