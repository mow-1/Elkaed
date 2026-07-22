from rest_framework import serializers
from .models import (Category, Course, Topic, Lesson, Enrollment, LessonProgress,
                      LessonWatchlist, Material, Assignment, AssignmentSubmission)


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
    items   = serializers.SerializerMethodField()

    class Meta:
        model  = Topic
        fields = ('id', 'title', 'order', 'lessons', 'items')

    def get_items(self, topic):
        """Unified, ordered curriculum list: lessons + quizzes + assignments,
        merged and sorted — feeds both the public course page and the builder's
        curriculum step. Deliberately metadata-only (no question/answer data —
        that's fetched separately via QuizDetailView once a student starts a
        quiz, which already enforces its own enrollment check)."""
        items = []
        for lesson in topic.lessons.all():
            items.append({
                'id': lesson.id, 'type': 'lesson', 'title': lesson.title, 'order': lesson.order,
                'duration_seconds': lesson.duration_seconds, 'is_free_preview': lesson.is_free_preview,
                'view_limit': lesson.view_limit,
            })
        for quiz in topic.quiz_set.all():
            items.append({
                'id': quiz.id, 'type': 'quiz', 'title': quiz.title, 'order': quiz.order,
                'time_limit': quiz.time_limit, 'attempts_allowed': quiz.attempts_allowed,
                'is_locked': quiz.is_locked,
            })
        for assignment in topic.assignments.all():
            items.append({
                'id': assignment.id, 'type': 'assignment', 'title': assignment.title_ar,
                'order': assignment.order, 'due_at': assignment.due_at,
                'has_attachment': bool(assignment.attachment),
            })
        return sorted(items, key=lambda i: i['order'])


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


class AdminCourseSerializer(serializers.ModelSerializer):
    # Draft courses (is_published=False) are invisible on the public course-detail
    # endpoint, so the builder's curriculum step reads topics/items from here instead —
    # same TopicSerializer.items shape, just reachable before publishing.
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model  = Course
        fields = ['id', 'title', 'title_en', 'slug', 'description', 'description_en',
                  'instructor', 'category', 'price', 'thumbnail', 'is_published',
                  'max_students', 'topics', 'created_at', 'updated_at']
        read_only_fields = ['id', 'instructor', 'created_at', 'updated_at']


class AdminTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Topic
        fields = ['id', 'course', 'title', 'title_en', 'order']
        read_only_fields = ['id', 'course', 'order']


class AdminLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Lesson
        fields = ['id', 'topic', 'title', 'title_en', 'order', 'video', 'video_source',
                  'youtube_id', 'view_limit', 'is_free_preview', 'duration_seconds']
        read_only_fields = ['id', 'topic', 'order', 'video', 'duration_seconds']


class AdminAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Assignment
        fields = ['id', 'topic', 'title_ar', 'title_en', 'instructions', 'attachment',
                  'due_at', 'order', 'created_at']
        read_only_fields = ['id', 'topic', 'order', 'created_at']


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'assignment', 'file', 'submitted_at']
        read_only_fields = ['id', 'assignment', 'submitted_at']


class EnrollmentStudentSerializer(serializers.ModelSerializer):
    """Enrollment with student details for instructor view."""
    phone      = serializers.CharField(source='student.phone')
    full_name  = serializers.CharField(source='student.full_name')
    academic_year = serializers.CharField(source='student.academic_year')

    class Meta:
        model  = Enrollment
        fields = ['id', 'phone', 'full_name', 'academic_year',
                  'payment_method', 'enrolled_at', 'status']
