from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache
from datetime import timedelta
from django.db import transaction as db_transaction
from app_inventory.models import LumberCategory, LumberProduct, Inventory, StockTransaction
from app_inventory.serializers import (
    LumberCategorySerializer, LumberProductSerializer, 
    InventorySerializer, StockTransactionSerializer
)
from app_inventory.services import InventoryService
from app_inventory.reporting import InventoryReports


class ProductPagination(PageNumberPagination):
    """Pagination for products list"""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LumberCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for lumber categories - public read access"""
    queryset = LumberCategory.objects.all()
    serializer_class = LumberCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Public read, authenticated write


class LumberProductViewSet(viewsets.ModelViewSet):
    """API endpoint for lumber products with caching and pagination - public read access"""
    queryset = LumberProduct.objects.select_related('category').prefetch_related('inventory').filter(is_active=True)
    serializer_class = LumberProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Public read, authenticated write
    pagination_class = ProductPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """Cache the queryset for better performance"""
        return super().get_queryset()
    
    def list(self, request, *args, **kwargs):
        """Override list to add caching"""
        # Generate cache key based on request parameters and global version
        version = self._get_products_list_version()
        cache_key = f"products_list_v{version}_{request.query_params.urlencode()}"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        # Get from database
        response = super().list(request, *args, **kwargs)
        
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, response.data, 300)
        
        return response
    
    def retrieve(self, request, *args, **kwargs):
        """Cache individual product details"""
        cache_key = f"product_{kwargs.get('pk')}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 600)  # 10 minutes
        
        return response
    
    def create(self, request, *args, **kwargs):
        """Create and clear list cache. Wrap with debug logging to capture file upload issues."""
        try:
            response = super().create(request, *args, **kwargs)
            self._clear_product_cache()
            try:
                self._bump_products_list_version()
            except Exception:
                pass
            return response
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Log request summary to help debug file upload issues
            try:
                files = list(request.FILES.keys())
            except Exception:
                files = str(type(request.FILES))
            try:
                data_keys = list(request.data.keys()) if hasattr(request.data, 'keys') else str(type(request.data))
            except Exception:
                data_keys = str(type(request.data))
            print(f"[ProductCreateDebug] FILES: {files}")
            print(f"[ProductCreateDebug] DATA_KEYS: {data_keys}")
            return Response({'error': 'Error creating product', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update and clear caches"""
        try:
            response = super().update(request, *args, **kwargs)
            self._clear_product_cache()
            try:
                self._bump_products_list_version()
            except Exception:
                pass
            cache.delete(f"product_{kwargs.get('pk')}")
            return response
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                files = list(request.FILES.keys())
            except Exception:
                files = str(type(request.FILES))
            try:
                data_keys = list(request.data.keys()) if hasattr(request.data, 'keys') else str(type(request.data))
            except Exception:
                data_keys = str(type(request.data))
            print(f"[ProductUpdateDebug] FILES: {files}")
            print(f"[ProductUpdateDebug] DATA_KEYS: {data_keys}")
            return Response({'error': 'Error updating product', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Delete and clear caches"""
        self._clear_product_cache()
        cache.delete(f"product_{kwargs.get('pk')}")
        resp = super().destroy(request, *args, **kwargs)
        try:
            self._bump_products_list_version()
        except Exception:
            pass
        return resp
    
    def _clear_product_cache(self):
        """Clear all product-related caches"""
        # Clear list cache patterns
        for pattern in ['products_list_', 'product_']:
            cache.delete_pattern(pattern) if hasattr(cache, 'delete_pattern') else None
        # Alternative: clear all caches matching pattern by iterating
        # This is a fallback for locmem cache
        keys = list(cache._cache.keys()) if hasattr(cache, '_cache') else []
        for key in keys:
            if key.startswith('products_list_') or key.startswith('product_'):
                cache.delete(key)

    def _get_products_list_version(self):
        """Return current products list cache version (int); initialize if missing."""
        try:
            v = cache.get('products_list_version')
            if v is None:
                cache.set('products_list_version', 1)
                return 1
            return int(v)
        except Exception:
            # Fallback to 1 if cache backend incompatible
            return 1

    def _bump_products_list_version(self):
        """Increment products list cache version so existing cached lists become stale."""
        try:
            v = cache.get('products_list_version')
            if v is None:
                cache.set('products_list_version', 2)
            else:
                try:
                    cache.set('products_list_version', int(v) + 1)
                except Exception:
                    cache.set('products_list_version', 2)
        except Exception:
            try:
                cache.incr('products_list_version')
            except Exception:
                cache.set('products_list_version', 2)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get products by category"""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({'error': 'category_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        products = LumberProduct.objects.filter(category_id=category_id, is_active=True)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search products by name or SKU"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'error': 'Query must be at least 2 characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        products = LumberProduct.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query),
            is_active=True
        )
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_delete(self, request):
        """
        Bulk delete products by IDs with optional force deletion
        
        Expected payload:
        {
            "ids": [1, 2, 3],
            "force": false
        }
        
        When force=true, deletes product even if it has related:
        - Stock transactions
        - Sales order items
        - Inventory snapshots
        - Shopping cart items
        
        All related records are cascade deleted.
        """
        import traceback
        
        ids = request.data.get('ids', [])
        force = request.data.get('force', False)
        
        if not ids:
            return Response({'error': 'ids array is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(ids, list):
            return Response({'error': 'ids must be an array'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            products = list(LumberProduct.objects.filter(id__in=ids))
            
            if not products:
                return Response(
                    {'error': 'No products found with the provided IDs'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            deleted_count = 0
            failed_deletions = []
            deletion_summary = []
            
            # Delete products one by one
            for product in products:
                try:
                    # Collect deletion info for summary BEFORE deletion
                    deletion_info = {
                        'product_id': product.id,
                        'product_name': str(product),
                        'deleted_items': {}
                    }
                    
                    # Count related records before deletion
                    deletion_info['deleted_items']['stock_transactions'] = product.stock_transactions.count()
                    deletion_info['deleted_items']['sales_order_items'] = product.salesorderitem_set.count()
                    deletion_info['deleted_items']['inventory_snapshots'] = product.inventory_snapshots.count()
                    deletion_info['deleted_items']['cart_items'] = product.cartitem_set.count()
                    
                    # If force=False and has critical references, warn but still delete (CASCADE)
                    if not force and (deletion_info['deleted_items']['sales_order_items'] > 0):
                        deletion_info['warning'] = (
                            f"Product is referenced in {deletion_info['deleted_items']['sales_order_items']} "
                            "sales order(s). Set force=true to ignore."
                        )
                    
                    # Delete the product (CASCADE handles all related records)
                    with db_transaction.atomic():
                        product.delete()
                    
                    deleted_count += 1
                    deletion_summary.append(deletion_info)
                    
                except Exception as e:
                    error_details = {
                        'product_id': product.id,
                        'product_name': str(product),
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    failed_deletions.append(error_details)
                    # Log the error for debugging
                    print(f"Error deleting product {product.id}: {str(e)}")
                    traceback.print_exc()
            
            # Clear product caches after all deletion attempts
            self._clear_product_cache()
            try:
                self._bump_products_list_version()
            except Exception:
                pass
            
            # Build response
            response_data = {
                'success': deleted_count > 0,
                'deleted_count': deleted_count,
                'total_requested': len(ids),
                'force': force,
            }
            
            if deletion_summary:
                response_data['deletion_details'] = deletion_summary
            
            if failed_deletions:
                response_data['failed_deletions'] = failed_deletions
            
            # Always return 200 OK so frontend can process the response
            return Response(response_data, status=status.HTTP_200_OK)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Bulk deletion failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for inventory levels (read-only)"""
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        threshold = request.query_params.get('threshold', 100)
        inventory = Inventory.objects.filter(total_board_feet__lt=float(threshold))
        serializer = self.get_serializer(inventory, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get inventory for a specific product"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'error': 'product_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            inventory = Inventory.objects.get(product_id=product_id)
            serializer = self.get_serializer(inventory)
            return Response(serializer.data)
        except Inventory.DoesNotExist:
            return Response({'error': 'Inventory not found'}, status=status.HTTP_404_NOT_FOUND)


class StockTransactionViewSet(viewsets.ModelViewSet):
    """API endpoint for stock transactions"""
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get', 'post'])
    def stock_in(self, request):
        """
        GET: Retrieve recent stock in transactions
        POST: Receive stock (Stock In)
        
        Expected POST payload:
        {
            "product_id": 1,
            "quantity_pieces": 100,
            "supplier_id": 1,
            "cost_per_unit": 25.50,
            "reference_id": "PO-20241208-0001"
        }
        """
        if request.method == 'GET':
            # Get recent stock_in transactions
            limit = request.query_params.get('limit', 10)
            transactions = StockTransaction.objects.filter(transaction_type='stock_in').order_by('-created_at')[:int(limit)]
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
        
        # POST - Create new stock in
        product_id = request.data.get('product_id')
        quantity_pieces = request.data.get('quantity_pieces')
        supplier_id = request.data.get('supplier_id')
        cost_per_unit = request.data.get('cost_per_unit')
        reference_id = request.data.get('reference_id') or request.data.get('po_number')
        
        if not product_id or not quantity_pieces:
            return Response({'error': 'product_id and quantity_pieces are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction_obj = InventoryService.stock_in(
                product_id=product_id,
                quantity_pieces=int(quantity_pieces),
                supplier_id=supplier_id,
                cost_per_unit=float(cost_per_unit) if cost_per_unit else None,
                created_by=request.user,
                reference_id=reference_id
            )
            serializer = self.get_serializer(transaction_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def stock_out(self, request):
        """
        Remove stock (Stock Out)
        
        Expected payload:
        {
            "product_id": 1,
            "quantity_pieces": 50,
            "reason": "sales",
            "reference_id": "SO-20241208-0001"
        }
        """
        product_id = request.data.get('product_id')
        quantity_pieces = request.data.get('quantity_pieces')
        reason = request.data.get('reason', 'sales')
        reference_id = request.data.get('reference_id')
        
        if not product_id or not quantity_pieces:
            return Response({'error': 'product_id and quantity_pieces are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction_obj = InventoryService.stock_out(
                product_id=product_id,
                quantity_pieces=int(quantity_pieces),
                reason=reason,
                created_by=request.user,
                reference_id=reference_id
            )
            serializer = self.get_serializer(transaction_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def adjust_stock(self, request):
        """
        Adjust stock (Damaged, Lost, Miscount, Recut)
        
        Expected payload:
        {
            "product_id": 1,
            "quantity_change": -10,
            "reason": "damaged"
        }
        """
        product_id = request.data.get('product_id')
        quantity_change = request.data.get('quantity_change')
        reason = request.data.get('reason')
        
        if not product_id or quantity_change is None or not reason:
            return Response({'error': 'product_id, quantity_change, and reason are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction_obj = InventoryService.adjust_stock(
                product_id=product_id,
                quantity_change=int(quantity_change),
                reason=reason,
                created_by=request.user
            )
            serializer = self.get_serializer(transaction_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get transactions for a specific product"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'error': 'product_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        transactions = StockTransaction.objects.filter(product_id=product_id)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'post'])
    def by_type(self, request):
        """Get transactions by type"""
        tx_type = request.query_params.get('type')
        if not tx_type:
            return Response({'error': 'type parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        transactions = StockTransaction.objects.filter(transaction_type=tx_type)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)


class AdjustmentViewSet(viewsets.ViewSet):
    """API endpoint specifically for stock adjustments"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get recent adjustments"""
        limit = int(request.query_params.get('limit', 10))
        adjustments = StockTransaction.objects.filter(
            transaction_type='adjustment'
        ).order_by('-created_at')[:limit]
        
        # Check if request wants HTML or JSON
        if request.accepted_renderer.format == 'html' or request.query_params.get('format') == 'html':
            serializer = StockTransactionSerializer(adjustments, many=True)
            return Response({
                'adjustments': serializer.data
            })
        
        serializer = StockTransactionSerializer(adjustments, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """
        Create a new stock adjustment
        
        Expected payload:
        {
            "product_id": 1,
            "quantity_pieces": 10,
            "adjustment_type": "increase" or "decrease",
            "reason": "damaged",
            "description": "Detailed reason"
        }
        """
        product_id = request.data.get('product_id')
        quantity_pieces = request.data.get('quantity_pieces')
        adjustment_type = request.data.get('adjustment_type')
        reason = request.data.get('reason')
        description = request.data.get('description')
        
        if not all([product_id, quantity_pieces, adjustment_type, reason]):
            return Response(
                {'error': 'product_id, quantity_pieces, adjustment_type, and reason are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Determine quantity change based on type
            quantity_change = int(quantity_pieces)
            if adjustment_type == 'decrease':
                quantity_change = -quantity_change
            
            # Create adjustment using service
            transaction_obj = InventoryService.adjust_stock(
                product_id=product_id,
                quantity_change=quantity_change,
                reason=reason,
                created_by=request.user
            )
            serializer = StockTransactionSerializer(transaction_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InventoryReportViewSet(viewsets.ViewSet):
    """API endpoints for inventory reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def monthly_usage(self, request):
        """Get monthly usage vs purchases report"""
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        report = InventoryReports.monthly_usage_vs_purchases(year, month)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def wastage(self, request):
        """Get wastage report"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        report = InventoryReports.wastage_report(start_date=start_date)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def turnover(self, request):
        """Get inventory turnover analysis"""
        days = int(request.query_params.get('days', 30))
        
        report = InventoryReports.inventory_turnover(days=days)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def stock_value(self, request):
        """Get total stock value by category"""
        report = InventoryReports.stock_value_report()
        return Response(report)
