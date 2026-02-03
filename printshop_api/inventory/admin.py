# inventory/admin.py

from django.contrib import admin
from .models import Machine, MachineCapability, Material, MaterialStock

class MachineCapabilityInline(admin.TabularInline):
    model = MachineCapability
    extra = 1
    fields = ['feed_type', 'max_width', 'max_height']

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop_link', 'type', 'is_active', 'created_at']
    list_filter = ['shop', 'type', 'is_active']
    search_fields = ['name', 'shop__name']
    inlines = [MachineCapabilityInline]
    ordering = ['shop', 'name']
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_link(self, obj):
        return obj.shop.name

class MaterialStockInline(admin.TabularInline):
    model = MaterialStock
    extra = 1
    fields = ['label', 'width', 'height', 'current_stock_level']

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop_link', 'type', 'cost_per_unit', 'unit_type', 'is_active']
    list_filter = ['shop', 'type', 'unit_type', 'is_active']
    search_fields = ['name', 'shop__name']
    inlines = [MaterialStockInline]
    ordering = ['shop', 'name']

    @admin.display(description="Shop", ordering="shop__name")
    def shop_link(self, obj):
        return obj.shop.name

# Optional: Register discrete Capability/Stock models if you need specific search
@admin.register(MachineCapability)
class MachineCapabilityAdmin(admin.ModelAdmin):
    list_display = ['machine', 'feed_type', 'max_width', 'max_height']
    list_filter = ['feed_type', 'machine__shop']
    search_fields = ['machine__name']

@admin.register(MaterialStock)
class MaterialStockAdmin(admin.ModelAdmin):
    list_display = ['label', 'material', 'width', 'height', 'current_stock_level']
    list_filter = ['material__shop', 'material__type']
    search_fields = ['label', 'material__name']