from django.contrib import admin
from django.db.models import Count
from .models import Category, Course, Topic, Lesson, Enrollment, LessonProgress


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'student_type', 'academic_year', 'parent', 'order')
    list_editable = ('order',)
    list_filter   = ('student_type', 'academic_year')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class TopicInline(admin.StackedInline):
    model = Topic
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display   = ('title', 'instructor', 'category', 'price', 'enrollment_count', 'is_published')
    list_filter    = ('is_published', 'category__academic_year', 'category__student_type')
    search_fields  = ('title', 'instructor__phone')
    list_editable  = ('is_published',)
    inlines        = [TopicInline]
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(enrollment_count=Count('enrollment'))

    def enrollment_count(self, obj):
        return obj.enrollment_count
    enrollment_count.short_description = 'الطلاب'
    enrollment_count.admin_order_field = 'enrollment_count'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter  = ('course',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'video_source', 'view_limit', 'is_free_preview')
    list_filter  = ('video_source', 'is_free_preview')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('student', 'course', 'status', 'payment_method', 'enrolled_at')
    list_filter   = ('status', 'payment_method', 'course__category__academic_year')
    search_fields = ('student__phone', 'course__title')
    raw_id_fields = ('student', 'course', 'order')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display  = ('student', 'lesson', 'view_count', 'completed', 'last_watched')
    list_filter   = ('completed',)
    search_fields = ('student__phone',)
