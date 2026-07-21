from django.urls import path
from .views import (PricingSettingsView, AdminDiscountListView, AdminDiscountDetailView,
                     CenterGroupListView, CenterGroupDetailView, PhysicalSessionListView,
                     PhysicalSessionDetailView, SessionChecklistView, MarkAttendanceView,
                     MarkAllPresentView, ApplyPackageCreditView, StudentAttendanceHistoryView,
                     ArrearsView, RevokeAccessView, ResendWhatsappView, GroupIdCardsPdfView,
                     ScanAttendanceView, SessionSearchView, RevenueReportView)

urlpatterns = [
    path('pricing-settings/', PricingSettingsView.as_view(), name='pricing_settings'),
    path('discounts/', AdminDiscountListView.as_view(), name='discount_list'),
    path('discounts/<int:pk>/', AdminDiscountDetailView.as_view(), name='discount_detail'),

    path('groups/', CenterGroupListView.as_view(), name='group_list'),
    path('groups/<int:pk>/', CenterGroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/apply-package-credit/', ApplyPackageCreditView.as_view(), name='group_package_credit'),
    path('groups/<int:pk>/id-cards.pdf', GroupIdCardsPdfView.as_view(), name='group_id_cards'),

    path('sessions/', PhysicalSessionListView.as_view(), name='session_list'),
    path('sessions/<int:pk>/', PhysicalSessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:pk>/checklist/', SessionChecklistView.as_view(), name='session_checklist'),
    path('sessions/<int:pk>/mark/', MarkAttendanceView.as_view(), name='session_mark'),
    path('sessions/<int:pk>/mark-all-present/', MarkAllPresentView.as_view(), name='session_mark_all_present'),
    path('sessions/<int:pk>/search/', SessionSearchView.as_view(), name='session_search'),

    path('scan/', ScanAttendanceView.as_view(), name='scan_attendance'),

    path('students/<int:pk>/history/', StudentAttendanceHistoryView.as_view(), name='student_history'),
    path('arrears/', ArrearsView.as_view(), name='arrears'),
    path('revenue-report/', RevenueReportView.as_view(), name='revenue_report'),

    path('records/<int:pk>/revoke-access/', RevokeAccessView.as_view(), name='record_revoke_access'),
    path('records/<int:pk>/resend-whatsapp/', ResendWhatsappView.as_view(), name='record_resend_whatsapp'),
]
