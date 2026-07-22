import csv
import io

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.tasks import send_whatsapp_task
from apps.attendance.models import CenterGroup
from .models import User, ShippingAddress, ImportBatch
from .permissions import is_admin, is_ops
from .serializers import (SendOTPSerializer, VerifyOTPSerializer, UserProfileSerializer,
                           UserProfileUpdateSerializer, CreateStudentSerializer,
                           ShippingAddressSerializer, CustomerListSerializer, CustomerDetailSerializer,
                           PasswordLoginSerializer, RegistrationSettingsSerializer,
                           ImportBatchListSerializer, ImportBatchDetailSerializer)
from .services import generate_otp, verify_otp, validate_import_row, generate_strong_password
from .tasks import import_csv_task

OTP_ERROR_MESSAGES = {
    'no_otp': 'لم يتم طلب رمز تحقق. أرسله مجددًا.',
    'blocked': 'تم تجاوز عدد المحاولات. أرسل رمزًا جديدًا.',
    'expired': 'انتهت صلاحية الرمز. أرسل رمزًا جديدًا.',
    'wrong_code': 'رمز التحقق غير صحيح.',
}


def _issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = SendOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone   = ser.validated_data['phone']
        purpose = ser.validated_data['purpose']

        if purpose == 'login' and not User.objects.filter(phone=phone).exists():
            # don't reveal user existence — same response
            return Response({'detail': 'تم إرسال رمز التحقق إذا كان الرقم مسجلاً.'})

        code = generate_otp(phone, purpose)
        message = f'رمز التحقق الخاص بك في القائد:\n{code}\nصالح لمدة 5 دقائق.'
        send_whatsapp_task.delay(phone, message)

        return Response({'detail': 'تم إرسال رمز التحقق.'})


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = VerifyOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data    = ser.validated_data
        phone   = data['phone']
        purpose = data['purpose']

        ok, reason = verify_otp(phone, data['code'], purpose)
        if not ok:
            return Response(
                {'detail': OTP_ERROR_MESSAGES.get(reason, 'خطأ في التحقق.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if purpose == 'register':
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'first_name':     data['first_name'],
                    'last_name':      data['last_name'],
                    'student_type':   'online',  # self-registration is always online; center students come from CSV import / CreateStudentView
                    'academic_year':  data['academic_year'],
                    'guardian_phone': data['guardian_phone'],
                    'role':           'student',
                },
            )
            if not created:
                return Response(
                    {'detail': 'هذا الرقم مسجل بالفعل. استخدم تسجيل الدخول.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response({'detail': 'المستخدم غير موجود.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'user': UserProfileSerializer(user).data,
            **_issue_tokens(user),
        })


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        ser = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(UserProfileSerializer(request.user).data)


class CreateStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('instructor', 'admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        ser = CreateStudentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        phone = data['phone']
        if User.objects.filter(phone=phone).exists():
            return Response({'detail': 'هذا الرقم مسجل بالفعل.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            phone=phone,
            first_name=data['first_name'],
            last_name=data['last_name'],
            guardian_phone=data.get('guardian_phone', ''),
            academic_year=data['academic_year'],
            student_type=data['student_type'],
            role='student',
            password=data['phone'],
        )
        return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.courses.models import Enrollment
        from apps.commerce.models import Order

        user_qs = User.objects.filter(role='student')
        total_students = user_qs.count()

        by_type = dict(user_qs.values_list('student_type').annotate(c=Count('id')).values_list('student_type', 'c'))
        by_year = dict(user_qs.values_list('academic_year').annotate(c=Count('id')).values_list('academic_year', 'c'))

        revenue = Order.objects.filter(status='completed').aggregate(total=Sum('total_price'))['total'] or 0
        enrollments = Enrollment.objects.filter(status='active').count()

        top_courses = (
            Enrollment.objects
            .filter(status='active')
            .values('course__title')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return Response({
            'total_students': total_students,
            'by_student_type': by_type,
            'by_academic_year': by_year,
            'total_revenue_egp': revenue,
            'active_enrollments': enrollments,
            'top_courses': list(top_courses),
        })


class AddressListView(generics.ListCreateAPIView):
    serializer_class   = ShippingAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        is_first = not ShippingAddress.objects.filter(user=user).exists()
        serializer.save(user=user, is_default=is_first)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_obj(self, request, pk):
        return get_object_or_404(ShippingAddress, pk=pk, user=request.user)

    def get(self, request, pk):
        return Response(ShippingAddressSerializer(self._get_obj(request, pk)).data)

    def patch(self, request, pk):
        obj = self._get_obj(request, pk)
        ser = ShippingAddressSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ShippingAddressSerializer(obj).data)

    def delete(self, request, pk):
        self._get_obj(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, pk):
        """POST /addresses/<id>/set-default/ — mark as default, unset others."""
        obj = self._get_obj(request, pk)
        ShippingAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
        obj.is_default = True
        obj.save(update_fields=['is_default'])
        return Response(ShippingAddressSerializer(obj).data)


class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)

        qs = User.objects.filter(role='student').annotate(
            enrollment_count=Count('enrollments', distinct=True)
        ).order_by('-date_joined')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)  |
                Q(phone__icontains=search)
            )

        year = request.query_params.get('year', '').strip()
        if year:
            qs = qs.filter(academic_year=year)

        stype = request.query_params.get('type', '').strip()
        if stype:
            qs = qs.filter(student_type=stype)

        group = request.query_params.get('group', '').strip()
        if group:
            qs = qs.filter(group_id=group)

        page     = max(1, int(request.query_params.get('page', 1)))
        per_page = 20
        total    = qs.count()
        start    = (page - 1) * per_page
        results  = CustomerListSerializer(qs[start:start + per_page], many=True).data

        return Response({'count': total, 'page': page, 'per_page': per_page, 'results': results})


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ('admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, pk=pk)
        return Response(CustomerDetailSerializer(user).data)

    def patch(self, request, pk):
        if request.user.role not in ('admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, pk=pk)
        if 'group' in request.data:
            group_id = request.data['group']
            if group_id in (None, ''):
                user.group = None
            else:
                user.group = get_object_or_404(CenterGroup, pk=group_id)
            user.save(update_fields=['group'])
        return Response(CustomerDetailSerializer(user).data)


class PasswordLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone    = ser.validated_data['phone']
        password = ser.validated_data['password']

        user = authenticate(request, phone=phone, password=password)
        if user is None or not user.is_active:
            return Response({'detail': 'رقم الهاتف أو كلمة المرور غير صحيحة.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'user': UserProfileSerializer(user).data,
            **_issue_tokens(user),
        })


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_password = (request.data.get('new_password') or '').strip()
        if len(new_password) < 8:
            return Response(
                {'detail': 'كلمة المرور يجب أن تكون 8 أحرف على الأقل.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save(update_fields=['password', 'must_change_password'])
        return Response({'detail': 'تم تغيير كلمة المرور بنجاح.'})


class RegistrationSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.attendance.models import PricingSettings
        return Response(RegistrationSettingsSerializer(PricingSettings.get_solo()).data)


class ImportPreviewView(APIView):
    """Validate a CSV in memory, no DB writes at all."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not is_ops(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'الملف مطلوب.'}, status=status.HTTP_400_BAD_REQUEST)

        content = file.read().decode('utf-8-sig')
        seen_phones = set()
        rows = []
        for i, row in enumerate(csv.DictReader(io.StringIO(content)), start=1):
            errors = validate_import_row(row, seen_phones)
            rows.append({
                'row': i,
                'phone': (row.get('student_phone') or '').strip(),
                'status': 'ok' if not errors else 'error',
                'errors': errors,
            })

        return Response({
            'total_rows': len(rows),
            'valid_count': sum(1 for r in rows if r['status'] == 'ok'),
            'error_count': sum(1 for r in rows if r['status'] == 'error'),
            'rows': rows,
        })


class ImportConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not is_ops(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'الملف مطلوب.'}, status=status.HTTP_400_BAD_REQUEST)

        content = file.read().decode('utf-8-sig')
        total_rows = sum(1 for _ in csv.DictReader(io.StringIO(content)))
        file.seek(0)

        batch = ImportBatch.objects.create(
            file=file, uploaded_by=request.user, total_rows=total_rows, status='pending',
        )
        import_csv_task.delay(batch.id)
        return Response({'id': batch.id, 'status': batch.status}, status=status.HTTP_201_CREATED)


class ImportBatchListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_ops(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        batches = ImportBatch.objects.all()[:50]
        return Response(ImportBatchListSerializer(batches, many=True).data)


class ImportBatchDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_ops(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        batch = get_object_or_404(ImportBatch, pk=pk)
        return Response(ImportBatchDetailSerializer(batch).data)


class ImportTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_ops(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="import_template.csv"'
        w = csv.writer(response)
        w.writerow(['first_name', 'last_name', 'student_phone', 'guardian_phone',
                    'academic_year', 'initial_wallet_balance', 'center_group', 'notes'])
        w.writerow(['أحمد', 'محمد', '01012345678', '01098765432', '1st', '0', '', ''])
        return response


class ResetCustomerPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, pk=pk)
        password = generate_strong_password()
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=['password', 'must_change_password'])

        message = (
            f'أهلاً {user.first_name}،\n'
            'تم إعادة تعيين كلمة المرور الخاصة بك في منصة القائد.\n'
            f'كلمة المرور الجديدة: {password}\n'
            'غيّر كلمة المرور بعد تسجيل الدخول.'
        )
        send_whatsapp_task.delay(user.phone, message)
        return Response({'detail': 'تم إعادة تعيين كلمة المرور وإرسالها.'})


class MyQrCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .idcards import qr_png_bytes
        return HttpResponse(qr_png_bytes(request.user.attendance_token), content_type='image/png')


class MyIdCardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .idcards import render_single_card_pdf
        pdf = render_single_card_pdf(request.user)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="id-card.pdf"'
        return response


class RegenerateQrView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, pk=pk)
        from .services import regenerate_attendance_token
        token = regenerate_attendance_token(user)
        return Response({'attendance_token': token})
