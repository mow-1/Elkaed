from decimal import Decimal

from django.db.models import Case, CharField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.commerce.models import WalletTransaction
from apps.commerce.serializers import WalletTransactionSerializer
from apps.commerce.services import InsufficientBalance, wallet_credit, wallet_debit
from apps.courses.models import LessonAccessGrant
from apps.users.models import User
from apps.users.permissions import is_admin, is_ops
from .models import AttendanceRecord, CenterGroup, LessonPackage, PhysicalSession, PricingSettings, StudentDiscount
from .serializers import (AttendanceRecordSerializer, CenterGroupSerializer, LessonPackageSerializer,
                           PhysicalSessionSerializer, PricingSettingsSerializer,
                           StudentDiscountSerializer)
from .services import mark, resend_whatsapp, revoke_access, set_attendance_status


class PricingSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(PricingSettingsSerializer(PricingSettings.get_solo()).data)

    def patch(self, request):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = PricingSettingsSerializer(PricingSettings.get_solo(), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


def _discount_snapshot(discount):
    return {
        'student_id': discount.student_id,
        'discount_type': discount.discount_type,
        'value': str(discount.value),
        'scope': discount.scope,
        'reason': discount.reason,
        'active': discount.active,
    }


class AdminDiscountListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentDiscountSerializer

    def get_queryset(self):
        qs = StudentDiscount.objects.select_related('student', 'created_by')
        student = self.request.query_params.get('student')
        if student:
            qs = qs.filter(student_id=student)
        active = self.request.query_params.get('active')
        if active is not None:
            qs = qs.filter(active=active.lower() == 'true')
        return qs

    def list(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        discount = serializer.save(created_by=self.request.user)
        log_action(
            self.request.user, 'discount_granted', target=discount,
            after=_discount_snapshot(discount),
        )


class AdminDiscountDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role not in ('admin', 'staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        discount = get_object_or_404(StudentDiscount, pk=pk)
        before = _discount_snapshot(discount)
        ser = StudentDiscountSerializer(discount, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        discount.refresh_from_db()
        action = 'discount_revoked' if before['active'] and not discount.active else 'discount_granted'
        log_action(
            request.user, action, target=discount,
            before=before, after=_discount_snapshot(discount),
        )
        return Response(ser.data)


class CenterGroupListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CenterGroupSerializer
    queryset = CenterGroup.objects.all()

    def list(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class CenterGroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        group = get_object_or_404(CenterGroup, pk=pk)
        ser = CenterGroupSerializer(group, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class LessonPackageListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LessonPackageSerializer
    queryset = LessonPackage.objects.filter(is_active=True).order_by('price')

    def list(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class LessonPackageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        package = get_object_or_404(LessonPackage, pk=pk)
        ser = LessonPackageSerializer(package, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ApplyLessonPackageView(APIView):
    """Admin sells a lesson package to a student: deducts the package price from
    their wallet and credits prepaid_lessons_remaining, which attendance marking
    consumes before falling back to a per-lesson wallet debit."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        package = get_object_or_404(LessonPackage, pk=pk, is_active=True)
        student = get_object_or_404(User, pk=request.data.get('student_id'), role='student')

        try:
            wallet_debit(
                student, package.price, reason_code='package_purchase',
                related_object=package, created_by=request.user,
                note=f'شراء باقة: {package.name}',
            )
        except InsufficientBalance:
            return Response({'detail': 'رصيد المحفظة غير كافٍ.'}, status=status.HTTP_400_BAD_REQUEST)

        User.objects.filter(pk=student.pk).update(
            prepaid_lessons_remaining=F('prepaid_lessons_remaining') + package.lesson_count
        )
        student.refresh_from_db(fields=['wallet_balance', 'prepaid_lessons_remaining'])
        return Response({
            'wallet_balance': student.wallet_balance,
            'prepaid_lessons_remaining': student.prepaid_lessons_remaining,
        })


class PhysicalSessionListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PhysicalSessionSerializer
    queryset = PhysicalSession.objects.select_related('group')

    def list(self, request, *args, **kwargs):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class PhysicalSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = get_object_or_404(PhysicalSession, pk=pk)
        return Response(PhysicalSessionSerializer(session).data)


class SessionChecklistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = get_object_or_404(PhysicalSession, pk=pk)
        records = {r.student_id: r for r in session.attendance_records.all()}
        rows = []
        for student in User.objects.filter(group_id=session.group_id).order_by('first_name', 'last_name'):
            record = records.get(student.id)
            rows.append({
                'student': {'id': student.id, 'phone': student.phone, 'full_name': student.full_name},
                'record': AttendanceRecordSerializer(record).data if record else None,
                'status': record.status if record else None,
            })
        return Response(rows)


class MarkAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = get_object_or_404(PhysicalSession, pk=pk)
        student_id = request.data.get('student_id')
        status_value = request.data.get('status')
        if status_value not in dict(AttendanceRecord.STATUS_CHOICES):
            return Response({'detail': 'حالة غير صالحة'}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(User, pk=student_id)
        record = mark(session, student, status_value, request.user)
        return Response(AttendanceRecordSerializer(record).data)


class MarkAllPresentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = get_object_or_404(PhysicalSession, pk=pk)
        already_marked = set(session.attendance_records.values_list('student_id', flat=True))
        students = User.objects.filter(group_id=session.group_id).exclude(id__in=already_marked)
        count = 0
        for student in students:
            mark(session, student, 'present', request.user)
            count += 1
        return Response({'marked_count': count})


class ApplyPackageCreditView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        group = get_object_or_404(CenterGroup, pk=pk)
        amount = PricingSettings.get_solo().monthly_package_price
        count = 0
        for student in group.students.all():
            wallet_credit(
                student, amount, reason_code='package_credit',
                created_by=request.user, note='باقة شهرية',
            )
            count += 1
        return Response({'credited_count': count})


class StudentAttendanceHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        student = get_object_or_404(User, pk=pk)
        records = (
            AttendanceRecord.objects
            .filter(student=student)
            .select_related('session', 'session__group')
            .order_by('-created_at')[:100]
        )
        transactions = student.wallet_transactions.all()[:100]
        return Response({
            'attendance': AttendanceRecordSerializer(records, many=True).data,
            'wallet_transactions': WalletTransactionSerializer(transactions, many=True).data,
        })


class ArrearsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        students = User.objects.filter(wallet_balance__lt=0).select_related('group')
        return Response([
            {
                'id': s.id, 'phone': s.phone, 'full_name': s.full_name,
                'wallet_balance': str(s.wallet_balance),
                'group': s.group.name_ar if s.group else None,
            }
            for s in students
        ])


class RevokeAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        record = get_object_or_404(AttendanceRecord, pk=pk)
        grant = get_object_or_404(
            LessonAccessGrant, student=record.student, session=record.session, revoked=False,
        )
        revoke_access(grant, actor=request.user)
        return Response({'detail': 'تم سحب الصلاحية'})


class ResendWhatsappView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        record = get_object_or_404(AttendanceRecord, pk=pk)
        resend_whatsapp(record, request.user)
        return Response({'detail': 'تم إعادة الإرسال'})


class GroupIdCardsPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        group = get_object_or_404(CenterGroup, pk=pk)
        from apps.users.idcards import render_bulk_cards_pdf
        pdf = render_bulk_cards_pdf(group.students.all())
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="cards-{group.pk}.pdf"'
        return response


class ScanAttendanceView(APIView):
    """POST {token, session_id, resolution?}. Kept minimal (single lookup + delegate to
    `mark()`) to hit the <300ms target for a line of students being scanned in sequence."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        token = (request.data.get('token') or '').strip()
        session_id = request.data.get('session_id')
        resolution = request.data.get('resolution')  # None | 'makeup' | 'add_anyway'
        if not token or not session_id:
            return Response({'result': 'error', 'detail': 'token و session_id مطلوبان.'},
                             status=status.HTTP_400_BAD_REQUEST)

        session = get_object_or_404(PhysicalSession, pk=session_id)
        student = User.objects.select_related('group').filter(attendance_token=token).first()
        if student is None:
            return Response(
                {'result': 'not_found', 'detail': 'الكود غير موجود أو تم تجديده.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if student.group_id != session.group_id and resolution is None:
            return Response({
                'result': 'group_mismatch',
                'detail': 'الطالب ليس في هذه المجموعة.',
                'student': {'id': student.id, 'phone': student.phone, 'full_name': student.full_name,
                            'group': student.group.name_ar if student.group else None},
            }, status=status.HTTP_409_CONFLICT)

        mark_status = 'makeup' if resolution == 'makeup' else 'present'
        existing = AttendanceRecord.objects.filter(session=session, student=student).first()
        already_marked = existing is not None and existing.status == mark_status

        record = mark(session, student, mark_status, request.user)
        student.refresh_from_db()
        log_action(request.user, 'attendance_changed', target=record, note='مسح QR')

        return Response({
            'result': 'already_present' if already_marked else 'ok',
            'student': {'id': student.id, 'phone': student.phone, 'full_name': student.full_name,
                        'group': student.group.name_ar if student.group else None},
            'wallet_balance': str(student.wallet_balance),
            'deducted': record.deducted,
            'insufficient_balance': mark_status == 'present' and not record.deducted,
        })


PHYSICAL_REASONS = ('attendance_present', 'attendance_absent', 'package_credit', 'package_purchase')
ONLINE_REASONS = ('purchase', 'bundle', 'coupon', 'kanga_topup', 'csv_import', 'admin_credit', 'admin_debit')


class RevenueReportView(APIView):
    """Computed ONLY from the WalletTransaction ledger (never wallet_balance) so manual
    edits/overrides never silently corrupt the report — gross/net/discounts per period,
    physical (attendance) vs online (purchases), plus refunds/reversals."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        granularity = request.query_params.get('granularity', 'day')
        trunc_fn = {'day': TruncDay, 'week': TruncWeek, 'month': TruncMonth}.get(granularity, TruncDay)

        # ponytail: any reason_code not explicitly bucketed above (e.g. a future one)
        # folds into 'online' as the safe default — revisit if that ever misclassifies.
        category_case = Case(
            When(reason_code__in=PHYSICAL_REASONS, then=Value('physical')),
            default=Value('online'),
            output_field=CharField(),
        )

        debit_rows = (
            WalletTransaction.objects
            .filter(type='debit')
            .exclude(reason_code='reversal')
            .annotate(period=trunc_fn('created_at'), category=category_case)
            .values('period', 'category')
            .annotate(gross=Sum(Coalesce('original_amount', 'amount')), net=Sum('amount'))
            .order_by('period')
        )

        refund_rows = (
            WalletTransaction.objects
            .filter(reason_code='reversal')
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(total=Sum('amount'))
        )

        def _blank_period(key):
            return {
                'period': key,
                'physical': {'gross': Decimal('0'), 'net': Decimal('0'), 'discounts': Decimal('0')},
                'online':   {'gross': Decimal('0'), 'net': Decimal('0'), 'discounts': Decimal('0')},
                'refunds': Decimal('0'),
            }

        periods = {}
        for row in debit_rows:
            key = row['period'].isoformat()
            p = periods.setdefault(key, _blank_period(key))
            gross = row['gross'] or Decimal('0')
            net = row['net'] or Decimal('0')
            bucket = p[row['category']]
            bucket['gross'] += gross
            bucket['net'] += net
            bucket['discounts'] += (gross - net)

        for row in refund_rows:
            key = row['period'].isoformat()
            p = periods.setdefault(key, _blank_period(key))
            p['refunds'] += row['total'] or Decimal('0')

        result = sorted(periods.values(), key=lambda r: r['period'])
        for p in result:
            p['physical'] = {k: str(v) for k, v in p['physical'].items()}
            p['online'] = {k: str(v) for k, v in p['online'].items()}
            p['refunds'] = str(p['refunds'])
        return Response(result)


class SessionSearchView(APIView):
    """Manual search-by-name/phone fallback for students who forgot their card/phone."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = get_object_or_404(PhysicalSession, pk=pk)
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response([])
        students = User.objects.filter(group_id=session.group_id).filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q)
        )[:20]
        return Response([{'id': s.id, 'phone': s.phone, 'full_name': s.full_name} for s in students])
