from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from django.db.models import Q
from django.utils.timezone import now as tz_now
from apps.commerce.services import wallet_purchase, create_kanga_payment, InsufficientBalance, AlreadyEnrolled
from apps.attendance.services import effective_price as apply_discount
from apps.commerce.models import FlashSale, Order, OrderItem
from apps.notifications.tasks import send_whatsapp_task
from apps.users.models import User as UserModel
from apps.users.permissions import is_admin
from .models import Course, Enrollment, Lesson, LessonAccessGrant, LessonProgress, Material
from .serializers import (CourseListSerializer, CourseDetailSerializer, EnrollmentSerializer,
                           MaterialSerializer, AdminMaterialSerializer, MyLessonSerializer)


def _check_enrollment_cap(course):
    if course.max_students == 0:
        return
    count = Enrollment.objects.filter(course=course, status='active').count()
    if count >= course.max_students:
        from apps.notifications.tasks import notify_admins_task
        notify_admins_task.delay(
            f'تنبيه: الكورس "{course.title}" بلغ الحد الأقصى ({course.max_students} طالب).'
        )


class CourseListView(generics.ListAPIView):
    serializer_class   = CourseListSerializer
    permission_classes = [AllowAny]
    search_fields      = ['title', 'title_en', 'description']
    filterset_fields   = ['category', 'category__student_type', 'category__academic_year']
    ordering_fields    = ['price', 'created_at']

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True).select_related('instructor', 'category')
        user = self.request.user
        if user.is_authenticated and user.student_type and user.academic_year:
            qs = qs.filter(
                category__student_type=user.student_type,
                category__academic_year=user.academic_year,
            )
        return qs


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class   = CourseDetailSerializer
    permission_classes = [AllowAny]
    lookup_field       = 'slug'
    queryset           = Course.objects.filter(is_published=True).prefetch_related(
                             'topics__lessons', 'category'
                         ).select_related('instructor')


class EnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id, is_published=True)

        # apply flash sale if active
        now = tz_now()
        sale = FlashSale.objects.filter(
            course=course, is_active=True, starts_at__lte=now, ends_at__gte=now
        ).first()
        effective_price = sale.effective_price() if sale else course.price
        price_before_discount = effective_price
        effective_price, discount_obj = apply_discount(request.user, effective_price, scope='online_only')

        # free courses — direct enrollment (only when no per-student discount is
        # involved; a discount-driven zero price still has to go through
        # wallet_purchase below so the ledger records the exemption)
        if effective_price == 0 and discount_obj is None:
            enrollment, created = Enrollment.objects.get_or_create(
                student=request.user, course=course,
                defaults={'payment_method': 'free'},
            )
            if not created:
                return Response({'detail': 'أنت مشترك بالفعل.'}, status=status.HTTP_400_BAD_REQUEST)
            _check_enrollment_cap(course)
            return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

        try:
            order = wallet_purchase(
                request.user, course, price=effective_price,
                original_price=price_before_discount if discount_obj else None,
                discount=discount_obj,
            )
        except AlreadyEnrolled:
            return Response({'detail': 'أنت مشترك بالفعل.'}, status=status.HTTP_400_BAD_REQUEST)
        except InsufficientBalance:
            # insufficient wallet — create pending order and return Kanga Pay URL
            pending_order = Order.objects.create(
                user=request.user,
                status='pending',
                payment_method='kanga_pay',
                total_price=effective_price,
            )
            OrderItem.objects.create(order=pending_order, course=course, price=course.price)
            return_url = request.build_absolute_uri(f'/student/courses/{course.slug}/')
            payment_url = create_kanga_payment(pending_order, course, return_url)
            return Response({'payment_url': payment_url}, status=status.HTTP_402_PAYMENT_REQUIRED)

        _check_enrollment_cap(course)
        send_whatsapp_task.delay(request.user.phone, f'تم التسجيل في {course.title} بنجاح!')
        enrollment = Enrollment.objects.get(student=request.user, course=course)
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


class MyEnrollmentsView(generics.ListAPIView):
    serializer_class   = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Enrollment.objects
            .filter(student=self.request.user, status='active')
            .select_related('course')
        )


class BulkEnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('instructor', 'admin', 'staff'):
            return Response({'detail': 'غير مصرح.'}, status=status.HTTP_403_FORBIDDEN)
        course_id  = request.data.get('course_id')
        phone_list = request.data.get('phones', [])
        if not course_id or not phone_list:
            return Response({'detail': 'course_id و phones مطلوبان.'}, status=status.HTTP_400_BAD_REQUEST)
        course = get_object_or_404(Course, pk=course_id)
        enrolled, skipped = [], []
        for phone in phone_list:
            try:
                student = UserModel.objects.get(phone=phone)
                _, created = Enrollment.objects.get_or_create(
                    student=student, course=course,
                    defaults={'payment_method': 'manual', 'enrolled_by': request.user},
                )
                (enrolled if created else skipped).append(phone)
            except UserModel.DoesNotExist:
                skipped.append(phone)
        return Response({'enrolled': enrolled, 'skipped': skipped})


class WatchlistToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        """Toggle: adds if not bookmarked, removes if already bookmarked."""
        from .models import LessonWatchlist
        from .serializers import WatchlistSerializer
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        obj, created = LessonWatchlist.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        if not created:
            obj.delete()
            return Response({'status': 'removed'})
        return Response(WatchlistSerializer(obj).data, status=status.HTTP_201_CREATED)

    def get(self, request, lesson_id=None):
        """GET /watchlist/ — list all bookmarks for current user."""
        from .models import LessonWatchlist
        from .serializers import WatchlistSerializer
        qs = LessonWatchlist.objects.filter(user=request.user).select_related(
            'lesson__topic__course'
        )
        return Response(WatchlistSerializer(qs, many=True).data)


class InstructorCoursesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import InstructorCourseSerializer
        return InstructorCourseSerializer

    def get_queryset(self):
        from django.db.models import Count
        if self.request.user.role not in ('instructor', 'admin', 'staff'):
            return Course.objects.none()
        return (
            Course.objects
            .filter(instructor=self.request.user)
            .annotate(enrollment_count=Count('enrollment'))
            .order_by('-created_at')
        )


class CourseStudentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import EnrollmentStudentSerializer
        return EnrollmentStudentSerializer

    def get_queryset(self):
        if self.request.user.role not in ('instructor', 'admin', 'staff'):
            return Enrollment.objects.none()
        course = get_object_or_404(
            Course, pk=self.kwargs['course_id'], instructor=self.request.user
        )
        return (
            Enrollment.objects
            .filter(course=course, status='active')
            .select_related('student')
            .order_by('student__first_name')
        )


class MaterialListView(generics.ListAPIView):
    """Student-facing: materials/revisions visible to the current student.
    ?kind=material|revision filters the portal's Materials vs Revisions tab."""
    serializer_class   = MaterialSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields    = ['kind']

    def get_queryset(self):
        user = self.request.user
        qs = Material.objects.filter(is_published=True).filter(
            Q(academic_year='') | Q(academic_year=user.academic_year)
        ).filter(
            Q(visibility_student_type='') | Q(visibility_student_type=user.student_type)
        )
        return qs.select_related('lesson', 'course')


class AdminMaterialListView(generics.ListCreateAPIView):
    serializer_class = AdminMaterialSerializer
    permission_classes = [IsAuthenticated]
    queryset = Material.objects.all()

    def list(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class AdminMaterialDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        material = get_object_or_404(Material, pk=pk)
        ser = AdminMaterialSerializer(material, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        if not is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        get_object_or_404(Material, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyLessonsView(APIView):
    """Union of lessons from active Enrollments and non-revoked LessonAccessGrants
    (e.g. absence-granted makeup videos), each annotated with view progress."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        progress_by_lesson = {
            p.lesson_id: p.view_count
            for p in LessonProgress.objects.filter(student=user)
        }

        rows = []
        seen_lesson_ids = set()

        enrolled_lessons = Lesson.objects.filter(
            topic__course__enrollment__student=user,
            topic__course__enrollment__status='active',
        ).select_related('topic__course')
        for lesson in enrolled_lessons:
            if lesson.id in seen_lesson_ids:
                continue
            seen_lesson_ids.add(lesson.id)
            rows.append({
                'id': lesson.id, 'title': lesson.title,
                'course_title': lesson.topic.course.title,
                'course_slug': lesson.topic.course.slug,
                'view_limit': lesson.view_limit,
                'view_count': progress_by_lesson.get(lesson.id, 0),
                'source': 'enrollment',
            })

        grants = LessonAccessGrant.objects.filter(
            student=user, revoked=False,
        ).select_related('lesson__topic__course')
        for grant in grants:
            lesson = grant.lesson
            if lesson.id in seen_lesson_ids:
                continue
            seen_lesson_ids.add(lesson.id)
            rows.append({
                'id': lesson.id, 'title': lesson.title,
                'course_title': lesson.topic.course.title,
                'course_slug': lesson.topic.course.slug,
                'view_limit': lesson.view_limit,
                'view_count': progress_by_lesson.get(lesson.id, 0),
                'source': 'absence_grant',
            })

        return Response(MyLessonSerializer(rows, many=True).data)
