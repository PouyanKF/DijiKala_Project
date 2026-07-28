from django.contrib import admin
from .models import Category, Store, Product, Cart, CartItem, Transaction, Coupon

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'parent', 'is_active', 'order', 'product_count')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('title', 'slug', 'parent', 'icon', 'description')
        }),
        ('تنظیمات نمایش', {
            'fields': ('is_active', 'order')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'تعداد محصولات'


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'owner__username')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'store', 'seller', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category', 'store', 'created_at')
    search_fields = ('title', 'description', 'seller__username')
    readonly_fields = ('created_at',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'is_paid', 'total_price')
    list_filter = ('is_paid', 'created_at')
    readonly_fields = ('created_at',)

    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'جمع کل'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart__is_paid',)
    search_fields = ('product__title',)

    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'قیمت کل'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'balance_after', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'description', 'reference_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_value', 'discount_type', 'is_active', 'is_valid', 'used_count', 'usage_limit')
    list_filter = ('is_active', 'discount_type', 'apply_type')
    search_fields = ('code', 'created_by__username')
    readonly_fields = ('used_count', 'created_at', 'updated_at')