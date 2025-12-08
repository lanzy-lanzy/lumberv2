from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.shortcuts import render
from datetime import timedelta
from app_inventory.models import LumberCategory, LumberProduct, Inventory, StockTransaction
from app_inventory.serializers import (
    LumberCategorySerializer, LumberProductSerializer, 
    InventorySerializer, StockTransactionSerializer
)
from app_inventory.services import InventoryService
from app_inventory.reporting import InventoryReports


class LumberCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for lumber categories"""
    queryset = LumberCategory.objects.all()
    serializer_class = LumberCategorySerializer
    permission_classes = [IsAuthenticated]


class LumberProductViewSet(viewsets.ModelViewSet):
    """API endpoint for lumber products"""
    queryset = LumberProduct.objects.filter(is_active=True)
    serializer_class = LumberProductSerializer
    permission_classes = [IsAuthenticated]
    
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
