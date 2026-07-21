from rest_framework import serializers
from .models import (HomepageBanner, NotificationPreference,
                     LandingHero, LandingFeature, LandingTestimonial,
                     LandingDarkBand, LandingCTA)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = HomepageBanner
        fields = ['id', 'image', 'title_ar', 'title_en', 'link_url', 'order']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationPreference
        fields = ['notif_type', 'enabled']


class LandingHeroSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LandingHero
        fields = '__all__'


class LandingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LandingFeature
        fields = '__all__'


class LandingTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LandingTestimonial
        fields = '__all__'


class LandingDarkBandSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LandingDarkBand
        fields = '__all__'


class LandingCTASerializer(serializers.ModelSerializer):
    class Meta:
        model  = LandingCTA
        fields = '__all__'


class AdminBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = HomepageBanner
        fields = ['id', 'image', 'title_ar', 'title_en', 'link_url', 'order', 'is_active']
