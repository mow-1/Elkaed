from django.urls import path
from .views import (
    WalletView, WalletHistoryView, CouponRedeemView, KangaPayWebhookView,
    ActiveFlashSalesView, BundleListView, BundlePurchaseView, CheckoutView,
    OrderListView, AdminFlashSaleView, AdminFlashSaleDetailView,
    AdminBundleView, AdminBundleDetailView,
)

urlpatterns = [
    path('wallet/',                             WalletView.as_view(),              name='wallet'),
    path('wallet/history/',                     WalletHistoryView.as_view(),       name='wallet_history'),
    path('checkout/',                           CheckoutView.as_view(),            name='checkout'),
    path('coupons/redeem/',                     CouponRedeemView.as_view(),        name='coupon_redeem'),
    path('kanga-pay/webhook/',                  KangaPayWebhookView.as_view(),     name='kanga_webhook'),
    path('flash-sales/',                        ActiveFlashSalesView.as_view(),    name='flash_sales'),
    path('bundles/',                            BundleListView.as_view(),          name='bundle_list'),
    path('bundles/<int:bundle_id>/purchase/',   BundlePurchaseView.as_view(),      name='bundle_purchase'),
    path('orders/',                             OrderListView.as_view(),            name='order_list'),
    path('admin/flash-sales/',                  AdminFlashSaleView.as_view(),      name='admin_flash_sales'),
    path('admin/flash-sales/<int:pk>/',         AdminFlashSaleDetailView.as_view(), name='admin_flash_sale_detail'),
    path('admin/bundles/',                      AdminBundleView.as_view(),         name='admin_bundles'),
    path('admin/bundles/<int:pk>/',             AdminBundleDetailView.as_view(),   name='admin_bundle_detail'),
]
