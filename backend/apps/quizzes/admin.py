from django.contrib import admin
from .models import Quiz, Question, AnswerChoice, QuizAttempt, AttemptAnswer


class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 2


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'is_locked', 'hide_results', 'attempts_allowed')
    list_filter  = ('is_locked', 'hide_results')
    actions      = ['lock_quizzes', 'unlock_quizzes']

    @admin.action(description='قفل الاختبارات المحددة')
    def lock_quizzes(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description='فتح الاختبارات المحددة')
    def unlock_quizzes(self, request, queryset):
        queryset.update(is_locked=False)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'mark', 'order')
    list_filter  = ('question_type',)
    inlines      = [AnswerChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display  = ('student', 'quiz', 'status', 'result', 'earned_marks', 'total_marks', 'started_at')
    list_filter   = ('status', 'result')
    search_fields = ('student__phone',)
