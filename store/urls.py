from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # صفحه اصلی
    path('', views.home_view, name='home'),
    
    # جزئیات محصول
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    
    # سبد خرید
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # پرداخت
    path('payment/', views.payment_view, name='payment'),
    path('checkout/', views.checkout, name='checkout'),
    
    # پنل فروشنده
    path('seller-panel/', views.seller_panel_view, name='seller_panel'),
    path('create-store/', views.create_store, name='create_store'),
    path('add-product/', views.add_product_view, name='add_product'),
    path('product/delete/<int:pk>/', views.delete_product_view, name='delete_product'),
    
    # پنل مشتری
    path('customer-panel/', views.customer_panel_view, name='customer_panel'),
    
    #کیف پول 
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallet/withdraw/', views.seller_withdraw, name='seller_withdraw'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    
    #  کدهای تخفیف 
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.coupon_create, name='coupon_create'),
    path('coupons/edit/<int:pk>/', views.coupon_edit, name='coupon_edit'),
    path('coupons/delete/<int:pk>/', views.coupon_delete, name='coupon_delete'),
    path('coupons/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupons/remove/', views.remove_coupon, name='remove_coupon'),
    
    # مدیریت محصولات فروشنده 
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/product/edit/<int:pk>/', views.seller_product_edit, name='seller_product_edit'),
    path('seller/product/stock/<int:pk>/', views.seller_product_stock, name='seller_product_stock'),
    path('seller/product/delete/<int:pk>/', views.seller_product_delete, name='seller_product_delete'),
    path('seller/product/toggle/<int:pk>/', views.seller_product_toggle, name='seller_product_toggle'),
]