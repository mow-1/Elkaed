from rest_framework import serializers
from .models import AttendanceRecord, CenterGroup, LessonPackage, PhysicalSession, PricingSettings, StudentDiscount


class PricingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PricingSettings
        fields = '__all__'


class _UserBriefSerializer(serializers.Serializer):
    id        = serializers.IntegerField()
    phone     = serializers.CharField()
    full_name = serializers.CharField()


class StudentDiscountSerializer(serializers.ModelSerializer):
    student    = _UserBriefSerializer(read_only=True)
    created_by = _UserBriefSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model  = StudentDiscount
        fields = [
            'id', 'student', 'student_id', 'discount_type', 'value', 'scope',
            'reason', 'active', 'starts_at', 'ends_at', 'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def create(self, validated_data):
        student_id = validated_data.pop('student_id')
        validated_data['student_id'] = student_id
        return super().create(validated_data)


class CenterGroupSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='students.count', read_only=True)

    class Meta:
        model  = CenterGroup
        fields = ['id', 'name_ar', 'academic_year', 'schedule_description',
                  'lesson_price_override', 'student_count']


class LessonPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LessonPackage
        fields = ['id', 'name', 'lesson_count', 'price', 'is_active']


class PhysicalSessionSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name_ar', read_only=True)

    class Meta:
        model  = PhysicalSession
        fields = ['id', 'group', 'group_name', 'date', 'title_ar', 'linked_lesson', 'lesson_price']
        extra_kwargs = {'lesson_price': {'required': False}}


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student = _UserBriefSerializer(read_only=True)

    class Meta:
        model  = AttendanceRecord
        fields = ['id', 'session', 'student', 'status', 'deducted', 'whatsapp_sent',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = fields
