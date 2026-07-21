from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (HomepageBanner, NotificationPreference, EmailCampaign,
                     LandingHero, LandingFeature, LandingTestimonial,
                     LandingDarkBand, LandingCTA)
from .serializers import (BannerSerializer, NotificationPreferenceSerializer,
                           LandingHeroSerializer, LandingFeatureSerializer,
                           LandingTestimonialSerializer, LandingDarkBandSerializer,
                           LandingCTASerializer, AdminBannerSerializer)


class BannerListView(generics.ListAPIView):
    """Active banners for the homepage, ordered by display order."""
    serializer_class   = BannerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        n = now()
        return HomepageBanner.objects.filter(
            is_active=True
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=n)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=n)
        )


class NotificationPreferenceView(APIView):
    """GET returns all 4 pref types with current enabled state.
       PATCH updates one or more types — accepts {} or [{}]."""
    permission_classes = [IsAuthenticated]

    TYPES = ['quiz_result', 'enrollment_confirmed', 'order_status', 'campaign']

    def get(self, request):
        prefs = {p.notif_type: p.enabled
                 for p in NotificationPreference.objects.filter(user=request.user)}
        data = [{'notif_type': t, 'enabled': prefs.get(t, True)} for t in self.TYPES]
        return Response(data)

    def patch(self, request):
        # Accepts: {"notif_type": "campaign", "enabled": false}
        #      or: [{"notif_type": "campaign", "enabled": false}, ...]
        items = request.data if isinstance(request.data, list) else [request.data]
        for item in items:
            t = item.get('notif_type')
            if t not in self.TYPES:
                continue
            NotificationPreference.objects.update_or_create(
                user=request.user, notif_type=t,
                defaults={'enabled': bool(item.get('enabled', True))},
            )
        return self.get(request)


class LandingContentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        hero      = LandingHero.objects.first()
        dark_band = LandingDarkBand.objects.first()
        cta       = LandingCTA.objects.first()
        return Response({
            'hero':         LandingHeroSerializer(hero).data if hero else None,
            'features':     LandingFeatureSerializer(LandingFeature.objects.all(), many=True).data,
            'dark_band':    LandingDarkBandSerializer(dark_band).data if dark_band else None,
            'testimonials': LandingTestimonialSerializer(LandingTestimonial.objects.all(), many=True).data,
            'cta':          LandingCTASerializer(cta).data if cta else None,
        })


class AdminBannerListView(APIView):
    """Admin: returns ALL banners (not filtered by active/schedule) + supports POST create."""
    permission_classes = [IsAuthenticated]

    def _admin(self, user):
        return user.role in ('admin', 'staff')

    def get(self, request):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        banners = HomepageBanner.objects.all().order_by('order')
        return Response(AdminBannerSerializer(banners, many=True).data)

    def post(self, request):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = AdminBannerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(AdminBannerSerializer(ser.instance).data, status=status.HTTP_201_CREATED)


class BannerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _admin(self, user):
        return user.role in ('admin', 'staff')

    def get(self, request, pk):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(AdminBannerSerializer(get_object_or_404(HomepageBanner, pk=pk)).data)

    def patch(self, request, pk):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        banner = get_object_or_404(HomepageBanner, pk=pk)
        ser = AdminBannerSerializer(banner, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(HomepageBanner, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _admin(self, user):
        return user.role in ('admin', 'staff')

    def get(self, request):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        campaigns = EmailCampaign.objects.all().order_by('-created_at')[:50]
        return Response([{
            'id': c.id, 'subject': c.subject, 'segment': c.segment,
            'status': c.status, 'sent_count': c.sent_count,
            'created_at': c.created_at,
        } for c in campaigns])

    def post(self, request):
        if not self._admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        subject = (request.data.get('subject') or '').strip()
        body    = (request.data.get('body_html') or '').strip()
        segment = request.data.get('segment', 'all')
        if not subject or not body:
            return Response({'detail': 'الموضوع والمحتوى مطلوبان.'}, status=status.HTTP_400_BAD_REQUEST)
        c = EmailCampaign.objects.create(
            subject=subject, body_html=body, segment=segment,
            created_by=request.user, status='draft',
        )
        return Response({'id': c.id, 'subject': c.subject, 'status': c.status}, status=status.HTTP_201_CREATED)


class CampaignSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        c = get_object_or_404(EmailCampaign, pk=pk)
        if c.status != 'draft':
            return Response({'detail': 'يمكن إرسال المسودات فقط.'}, status=status.HTTP_400_BAD_REQUEST)
        c.status = 'sending'
        c.save(update_fields=['status'])
        from .tasks import send_email_campaign_task
        send_email_campaign_task.delay(c.pk)
        return Response({'detail': 'بدأ الإرسال.'})
