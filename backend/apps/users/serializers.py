import re
from rest_framework import serializers
from .models import User, ShippingAddress, ImportBatch


EGYPTIAN_PHONE_RE = re.compile(r'^(0?1[0125]\d{8}|201[0125]\d{8})$')


def normalize_phone(raw: str) -> str:
    """Convert any Egyptian phone format to 201XXXXXXXXX."""
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0'):
        digits = '2' + digits
    if not digits.startswith('20'):
        digits = '20' + digits
    return digits


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        normalized = normalize_phone(value)
        if not EGYPTIAN_PHONE_RE.match(normalized):
            raise serializers.ValidationError('رقم هاتف مصري غير صالح')
        return normalized


class SendOTPSerializer(serializers.Serializer):
    PURPOSE_CHOICES = ['login', 'register', 'reset']
    phone   = PhoneField()
    purpose = serializers.ChoiceField(choices=PURPOSE_CHOICES)


class VerifyOTPSerializer(serializers.Serializer):
    PURPOSE_CHOICES = ['login', 'register', 'reset']
    phone      = PhoneField()
    code       = serializers.CharField(min_length=6, max_length=6)
    purpose    = serializers.ChoiceField(choices=PURPOSE_CHOICES)
    # only required for register
    first_name     = serializers.CharField(max_length=100, required=False)
    last_name      = serializers.CharField(max_length=100, required=False)
    student_type   = serializers.ChoiceField(choices=['center', 'online'], required=False)
    academic_year  = serializers.ChoiceField(choices=['1st', '2nd', '3rd'], required=False)
    guardian_phone = PhoneField(required=False)
    governorate    = serializers.CharField(required=False, allow_blank=True)
    school_name    = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs['purpose'] == 'register':
            for field in ('first_name', 'last_name', 'academic_year', 'guardian_phone'):
                if not attrs.get(field):
                    raise serializers.ValidationError({field: 'هذا الحقل مطلوب للتسجيل'})
            if attrs['guardian_phone'] == attrs['phone']:
                raise serializers.ValidationError(
                    {'guardian_phone': 'رقم ولي الأمر يجب أن يختلف عن رقم الطالب'}
                )
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'guardian_phone',
                  'student_type', 'academic_year', 'wallet_balance', 'role', 'date_joined',
                  'must_change_password')
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'guardian_phone')


class CreateStudentSerializer(serializers.Serializer):
    phone          = PhoneField()
    first_name     = serializers.CharField(max_length=100)
    last_name      = serializers.CharField(max_length=100)
    guardian_phone = PhoneField(required=False, allow_blank=True)
    academic_year  = serializers.ChoiceField(choices=['1st', '2nd', '3rd'])
    student_type   = serializers.ChoiceField(choices=['center', 'online'])


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ShippingAddress
        fields = ['id', 'label', 'governorate', 'city', 'street', 'is_default']


class CustomerListSerializer(serializers.ModelSerializer):
    enrollment_count = serializers.IntegerField(read_only=True)
    full_name        = serializers.SerializerMethodField()
    group_name       = serializers.CharField(source='group.name_ar', read_only=True, default=None)

    class Meta:
        model  = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'full_name',
                  'academic_year', 'student_type', 'date_joined', 'is_active', 'enrollment_count',
                  'group', 'group_name')

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()


class CustomerDetailSerializer(serializers.ModelSerializer):
    enrollments = serializers.SerializerMethodField()
    orders      = serializers.SerializerMethodField()
    full_name   = serializers.SerializerMethodField()
    group_name  = serializers.CharField(source='group.name_ar', read_only=True, default=None)

    class Meta:
        model  = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'full_name', 'guardian_phone',
                  'email', 'academic_year', 'student_type', 'wallet_balance',
                  'prepaid_lessons_remaining', 'role',
                  'date_joined', 'is_active', 'enrollments', 'orders', 'group', 'group_name')

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()

    def get_enrollments(self, obj):
        from apps.courses.models import Enrollment
        return list(
            Enrollment.objects.filter(student=obj)
            .select_related('course')
            .values('id', 'course__title', 'course__slug', 'status', 'enrolled_at')
        )

    def get_orders(self, obj):
        from apps.commerce.models import Order
        return list(
            Order.objects.filter(user=obj)
            .order_by('-created_at')[:10]
            .values('id', 'status', 'total_price', 'payment_method', 'created_at')
        )


class PasswordLoginSerializer(serializers.Serializer):
    phone    = PhoneField()
    password = serializers.CharField(write_only=True)


class RegistrationSettingsSerializer(serializers.Serializer):
    show_governorate_field = serializers.BooleanField()
    show_school_field      = serializers.BooleanField()


class ImportBatchListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ImportBatch
        fields = ('id', 'status', 'total_rows', 'imported_count', 'failed_count',
                  'uploaded_by', 'created_at', 'completed_at')


class ImportBatchDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ImportBatch
        fields = ('id', 'status', 'total_rows', 'imported_count', 'failed_count',
                  'row_results', 'uploaded_by', 'created_at', 'completed_at')
