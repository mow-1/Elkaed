from django.urls import path
from .views import (
    BannerListView, NotificationPreferenceView, LandingContentView,
    AdminBannerListView, BannerDetailView,
    CampaignListCreateView, CampaignSendView,
)

urlpatterns = [
    path('banners/',                     BannerListView.as_view(),             name='banner_list'),
    path('banners/admin/',               AdminBannerListView.as_view(),        name='admin_banner_list'),
    path('banners/<int:pk>/',            BannerDetailView.as_view(),           name='banner_detail'),
    path('preferences/',                 NotificationPreferenceView.as_view(), name='notif_preferences'),
    path('landing/',                     LandingContentView.as_view(),         name='landing_content'),
    path('campaigns/',                   CampaignListCreateView.as_view(),     name='campaign_list'),
    path('campaigns/<int:pk>/send/',     CampaignSendView.as_view(),           name='campaign_send'),
]
