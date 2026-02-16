# inventory/urls.py

from django.urls import path
from .views import (
    MachineViewSet,
    MachineCapabilityViewSet,
    MaterialViewSet,
    MaterialStockViewSet,
    PaperStockViewSet,
)

# 1. This is required to fix the "ImproperlyConfigured" error
app_name = "inventory"

urlpatterns = [
    # ==========================================
    # Machine Routes
    # URL: /api/shops/<slug>/machines/
    # ==========================================
    path(
        'shops/<slug:shop_slug>/machines/', 
        MachineViewSet.as_view({'get': 'list', 'post': 'create'}), 
        name='machine-list'
    ),
    path(
        'shops/<slug:shop_slug>/machines/<int:pk>/', 
        MachineViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
        name='machine-detail'
    ),

    # ==========================================
    # Machine Capabilities (Nested)
    # URL: /api/shops/<slug>/machines/<id>/capabilities/
    # ==========================================
    path(
        'shops/<slug:shop_slug>/machines/<int:machine_pk>/capabilities/', 
        MachineCapabilityViewSet.as_view({'get': 'list', 'post': 'create'}), 
        name='machine-capability-list'
    ),
    path(
        'shops/<slug:shop_slug>/machines/<int:machine_pk>/capabilities/<int:pk>/', 
        MachineCapabilityViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), 
        name='machine-capability-detail'
    ),

    # ==========================================
    # Material Routes
    # URL: /api/shops/<slug>/materials/
    # ==========================================
    path(
        'shops/<slug:shop_slug>/materials/', 
        MaterialViewSet.as_view({'get': 'list', 'post': 'create'}), 
        name='material-list'
    ),
    path(
        'shops/<slug:shop_slug>/materials/<int:pk>/', 
        MaterialViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
        name='material-detail'
    ),

    # ==========================================
    # Material Stock (Nested)
    # URL: /api/shops/<slug>/materials/<id>/stock/
    # ==========================================
    path(
        'shops/<slug:shop_slug>/materials/<int:material_pk>/stock/', 
        MaterialStockViewSet.as_view({'get': 'list', 'post': 'create'}), 
        name='stock-list'
    ),
    path(
        'shops/<slug:shop_slug>/materials/<int:material_pk>/stock/<int:pk>/', 
        MaterialStockViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), 
        name='stock-detail'
    ),
    path(
        'shops/<slug:shop_slug>/materials/<int:material_pk>/stock/<int:pk>/adjust/', 
        MaterialStockViewSet.as_view({'post': 'adjust_stock'}), 
        name='stock-adjust'
    ),

    # ==========================================
    # Paper Stock (inventory - sheet_size, gsm, paper_type)
    # URL: /api/shops/<slug>/paper-stock/
    # ==========================================
    path(
        'shops/<slug:shop_slug>/paper-stock/',
        PaperStockViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='paper-stock-list'
    ),
    path(
        'shops/<slug:shop_slug>/paper-stock/<int:pk>/',
        PaperStockViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='paper-stock-detail'
    ),
    path(
        'shops/<slug:shop_slug>/paper-stock/<int:pk>/adjust/',
        PaperStockViewSet.as_view({'post': 'adjust'}),
        name='paper-stock-adjust'
    ),
]