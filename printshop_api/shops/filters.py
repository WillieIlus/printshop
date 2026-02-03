# shops/filters.py

"""
Django Filter classes for the shops app.
"""

import django_filters
from .models import Shop, ShopClaim


class ShopFilter(django_filters.FilterSet):
    """Filter class for Shop model."""
    
    name = django_filters.CharFilter(lookup_expr="icontains")
    city = django_filters.CharFilter(lookup_expr="iexact")
    state = django_filters.CharFilter(lookup_expr="iexact")
    country = django_filters.CharFilter(lookup_expr="iexact")
    is_verified = django_filters.BooleanFilter()
    
    # Range filters for GPS coordinates
    min_lat = django_filters.NumberFilter(field_name="latitude", lookup_expr="gte")
    max_lat = django_filters.NumberFilter(field_name="latitude", lookup_expr="lte")
    min_lng = django_filters.NumberFilter(field_name="longitude", lookup_expr="gte")
    max_lng = django_filters.NumberFilter(field_name="longitude", lookup_expr="lte")
    
    class Meta:
        model = Shop
        fields = ["name", "city", "state", "country", "is_verified"]


class ShopClaimFilter(django_filters.FilterSet):
    """Filter class for ShopClaim model."""
    
    status = django_filters.ChoiceFilter(choices=ShopClaim.Status.choices)
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    
    class Meta:
        model = ShopClaim
        fields = ["status"]