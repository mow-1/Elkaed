import json
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Enrollment
from apps.users.models import User
from .models import Coupon, CouponRedemption, Order, OrderItem, WalletTransaction
from .serializers import CouponRedeemSerializer, WalletTransactionSerializer, KangaPayInitSerializer
from apps.notifications.tasks import send_whatsapp_task
from .services import verify_kanga_hmac, wallet_credit, wallet_debit, InsufficientBalance

logger = logging.getLogger(__name__)


class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        txns = (
            WalletTransaction.objects
            .filter(user=request.user)
            .order_by('-created_at')[:20]
        )
        return Response({
            'balance':      request.user.wallet_balance,
            'transactions': WalletTransactionSerializer(txns, many=True).data,
        })


class WalletHistoryView(generics.ListAPIView):
    """Portal Account tab: FULL paginated wallet history (kept separate from WalletView
    so its working [:20] slice for the dashboard card stays untouched)."""
    serializer_class   = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(user=self.request.user).order_by('-created_at')


class CouponRedeemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CouponRedeemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        code = ser.validated_data['code'].upper()

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response({'detail': 'الكوبون غير موجود.'}, status=status.HTTP_404_NOT_FOUND)

        if not coupon.is_valid():
            return Response({'detail': 'الكوبون منتهي أو مستخدم.'}, status=status.HTTP_400_BAD_REQUEST)

        if CouponRedemption.objects.filter(user=request.user, coupon=coupon).exists():
            return Response({'detail': 'استخدمت هذا الكوبون من قبل.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            CouponRedemption.objects.create(user=request.user, coupon=coupon, amount=coupon.amount)
            Coupon.objects.filter(pk=coupon.pk).update(usage_count=coupon.usage_count + 1)
            wallet_credit(
                request.user,
                coupon.amount,
                reference=f'coupon_{code}',
                note=f'شحن من كوبون: {code}',
            )

        return Response({'detail': f'تم إضافة {coupon.amount} جنيه للمحفظة.', 'amount': coupon.amount})


@method_decorator(csrf_exempt, name='dispatch')
class KangaPayWebhookView(APIView):
    permission_classes = []  # authenticated via HMAC, not JWT

    def post(self, request):
        signature = request.headers.get('X-Kanga-Signature', '')
        if not verify_kanga_hmac(request.body, signature):
            logger.warning('Kanga Pay webhook: invalid HMAC signature')
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        payment_status = payload.get('status')
        order_id       = payload.get('order_id')
        transaction_id = payload.get('payment_id', '')

        if payment_status != 'completed' or not order_id:
            return Response({'detail': 'ignored'})

        try:
            order = Order.objects.get(pk=order_id, status='pending')
        except Order.DoesNotExist:
            return Response({'detail': 'ignored'})

        with transaction.atomic():
            order.status         = 'completed'
            order.transaction_id = transaction_id
            order.save(update_fields=['status', 'transaction_id'])

            for item in order.items.select_related('course').all():
                _, created = Enrollment.objects.get_or_create(
                    student=order.user,
                    course=item.course,
                    defaults={'payment_method': 'kanga_pay', 'order': order},
                )
                if created:
                    from apps.courses.views import _check_enrollment_cap
                    _check_enrollment_cap(item.course)

        send_whatsapp_task.delay(
            order.user.phone,
            f'تم تسجيلك في المنصة! تم دفع طلبك #{order.pk} بنجاح.',
        )
        return Response({'detail': 'ok'})


from django.utils.timezone import now as tz_now
from .models import FlashSale, Bundle
from .serializers import (FlashSaleSerializer, BundleSerializer,
                           FlashSaleCreateSerializer, BundleCreateSerializer)


class ActiveFlashSalesView(generics.ListAPIView):
    serializer_class   = FlashSaleSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        n = tz_now()
        return FlashSale.objects.filter(
            is_active=True, starts_at__lte=n, ends_at__gte=n
        ).select_related('course')


class BundleListView(generics.ListAPIView):
    serializer_class   = BundleSerializer
    permission_classes = [AllowAny]
    queryset           = Bundle.objects.filter(is_active=True).prefetch_related('courses')


class BundlePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, bundle_id):
        bundle = get_object_or_404(Bundle, pk=bundle_id, is_active=True)
        user   = request.user
        already, enrolled_now = [], []

        try:
            with transaction.atomic():
                locked_user = User.objects.select_for_update().get(pk=user.pk)

                order = Order.objects.create(
                    user=locked_user,
                    status='completed',
                    payment_method='wallet',
                    total_price=bundle.price,
                )
                for course in bundle.courses.all():
                    _, created = Enrollment.objects.get_or_create(
                        student=locked_user, course=course,
                        defaults={'payment_method': 'wallet', 'order': order},
                    )
                    OrderItem.objects.get_or_create(order=order, course=course, defaults={'price': course.price})
                    if created:
                        from apps.courses.views import _check_enrollment_cap
                        _check_enrollment_cap(course)
                        enrolled_now.append(course.title)
                    else:
                        already.append(course.title)

                # raises InsufficientBalance -> propagates out of this atomic
                # block, rolling back the order/enrollments created above too
                wallet_debit(
                    locked_user, bundle.price, reason_code='bundle',
                    related_object=order, created_by=user,
                    note=f'شراء باقة: {bundle.title}',
                )
        except InsufficientBalance:
            return Response({'detail': 'رصيد المحفظة غير كافٍ.'}, status=status.HTTP_400_BAD_REQUEST)

        send_whatsapp_task.delay(user.phone, f'تم شراء باقة {bundle.title} بنجاح! تم تسجيلك في {len(enrolled_now)} كورس.')
        return Response({'enrolled': enrolled_now, 'already_enrolled': already})


class OrderListView(generics.ListAPIView):
    """Student's own order history, newest first."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import OrderSerializer
        return OrderSerializer

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related('items__course')
            .order_by('-created_at')
        )


def _admin_check(user):
    return user.role in ('admin', 'staff')


class AdminFlashSaleView(APIView):
    """Admin: list all flash sales + create."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = FlashSale.objects.select_related('course').order_by('-starts_at')
        return Response(FlashSaleSerializer(qs, many=True).data)

    def post(self, request):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = FlashSaleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(created_by=request.user, is_active=True)
        return Response(FlashSaleSerializer(obj).data, status=status.HTTP_201_CREATED)


class AdminFlashSaleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(FlashSale, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        sale = get_object_or_404(FlashSale, pk=pk)
        ser  = FlashSaleCreateSerializer(sale, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(FlashSaleSerializer(sale).data)


class AdminBundleView(APIView):
    """Admin: list all bundles + create."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = Bundle.objects.prefetch_related('courses').order_by('-created_at')
        return Response(BundleSerializer(qs, many=True).data)

    def post(self, request):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = BundleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(created_by=request.user, is_active=True)
        return Response(BundleSerializer(obj).data, status=status.HTTP_201_CREATED)


class AdminBundleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(Bundle, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk):
        if not _admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bundle = get_object_or_404(Bundle, pk=pk)
        title  = request.data.get('title')
        price  = request.data.get('price')
        if title:
            bundle.title = title
        if price:
            bundle.price = price
        bundle.save()
        return Response(BundleSerializer(bundle).data)
