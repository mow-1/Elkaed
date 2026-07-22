from rest_framework import serializers
from .models import Category, Course, Topic, Lesson, Enrollment, LessonProgress, LessonWatchlist, Material


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ('id', 'name', 'slug', 'student_type', 'academic_year')


class InstructorSerializer(serializers.Serializer):
    id        = serializers.IntegerField()
    full_name = serializers.CharField()


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Lesson
        fields = ('id', 'title', 'order', 'duration_seconds', 'is_free_preview',
                  'view_limit', 'video_source', 'youtube_id')


class TopicSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model  = Topic
        fields = ('id', 'title', 'order', 'lessons')


class CourseListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.full_name', read_only=True)
    category_name   = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Course
        fields = ('id', 'title', 'slug', 'price', 'thumbnail',
                  'instructor_name', 'category_name', 'is_published')


class CourseDetailSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.full_name', read_only=True)
    category        = CategorySerializer(read_only=True)
    topics          = TopicSerializer(many=True, read_only=True)

    class Meta:
        model  = Course
        fields = ('id', 'title', 'slug', 'description', 'price', 'thumbnail',
                  'instructor_name', 'category', 'topics', 'is_published', 'created_at')


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_slug  = serializers.CharField(source='course.slug', read_only=True)

    class Meta:
        model  = Enrollment
        fields = ('id', 'course', 'course_title', 'course_slug', 'status', 'payment_method', 'enrolled_at')
        read_only_fields = fields


class WatchlistSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    topic_title  = serializers.CharField(source='lesson.topic.title', read_only=True)
    course_slug  = serializers.CharField(source='lesson.topic.course.slug', read_only=True)

    class Meta:
        model  = LessonWatchlist
        fields = ['id', 'lesson', 'lesson_title', 'topic_title', 'course_slug', 'added_at']


class InstructorCourseSerializer(serializers.ModelSerializer):
    enrollment_count = serializers.IntegerField(read_only=True)
    category_name    = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Course
        fields = ['id', 'title', 'slug', 'price', 'is_published',
                  'enrollment_count', 'category_name', 'created_at']


class MaterialSerializer(serializers.ModelSerializer):
    lesson_id   = serializers.IntegerField(source='lesson.id', read_only=True, default=None)
    course_slug = serializers.CharField(source='course.slug', read_only=True, default=None)

    class Meta:
        model  = Material
        fields = ['id', 'title_ar', 'title_en', 'kind', 'file', 'lesson_id',
                  'course_slug', 'academic_year', 'created_at']
        read_only_fields = fields


class AdminMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Material
        fields = ['id', 'title_ar', 'title_en', 'kind', 'file', 'lesson', 'course',
                  'academic_year', 'visibility_student_type', 'is_published',
                  'uploaded_by', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class MyLessonSerializer(serializers.Serializer):
    id                = serializers.IntegerField()
    title             = serializers.CharField()
    course_title      = serializers.CharField()
    course_slug       = serializers.CharField()
    view_limit        = serializers.IntegerField()
    view_count        = serializers.IntegerField()
    source            = serializers.CharField()  # 'enrollment' | 'absence_grant'


class EnrollmentStudentSerializer(serializers.ModelSerializer):
    """Enrollment with student details for instructor view."""
    phone      = serializers.CharField(source='student.phone')
    full_name  = serializers.CharField(source='student.full_name')
    academic_year = serializers.CharField(source='student.academic_year')

    class Meta:
        model  = Enrollment
        fields = ['id', 'phone', 'full_name', 'academic_year',
                  'payment_method', 'enrolled_at', 'status']
