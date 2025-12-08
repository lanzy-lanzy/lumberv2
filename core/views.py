from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from core.models import CustomUser
from core.serializers import UserSerializer, UserCreateSerializer


@require_http_methods(["GET"])
def home(request):
    """Landing page - main entry point"""
    # If user is authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Show landing page to unauthenticated users
    context = {}
    return render(request, 'landing.html', context)


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    """Dashboard page - role-based view"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'dashboard.html', context)


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for user management"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get users by role"""
        role = request.query_params.get('role')
        if not role:
            return Response({'error': 'role parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = CustomUser.objects.filter(role=role)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
