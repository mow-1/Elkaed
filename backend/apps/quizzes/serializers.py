from rest_framework import serializers
from .models import Quiz, Question, AnswerChoice, QuizAttempt, AttemptAnswer


class AnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AnswerChoice
        fields = ['id', 'text', 'order', 'image']


class QuestionSerializer(serializers.ModelSerializer):
    choices = AnswerChoiceSerializer(many=True, read_only=True)

    class Meta:
        model  = Question
        fields = ['id', 'text', 'question_type', 'mark', 'order', 'image', 'choices']


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model  = Quiz
        fields = ['id', 'title', 'time_limit', 'pass_mark', 'attempts_allowed',
                  'is_locked', 'shuffle_questions', 'questions']


class AttemptAnswerInputSerializer(serializers.Serializer):
    question_id  = serializers.IntegerField()
    given_answer = serializers.CharField()


class SubmitAttemptSerializer(serializers.Serializer):
    answers = AttemptAnswerInputSerializer(many=True)


class AttemptAnswerResultSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(source='question.id')

    class Meta:
        model  = AttemptAnswer
        fields = ['question_id', 'given_answer', 'is_correct', 'marks_achieved']


class AttemptResultSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title')
    answers    = AttemptAnswerResultSerializer(many=True, read_only=True)

    class Meta:
        model  = QuizAttempt
        fields = ['id', 'quiz_title', 'total_marks', 'earned_marks',
                  'status', 'result', 'started_at', 'ended_at', 'answers']


class MyAttemptSerializer(serializers.ModelSerializer):
    quiz_title   = serializers.CharField(source='quiz.title')
    course_title = serializers.CharField(source='course.title')

    class Meta:
        model  = QuizAttempt
        fields = ['id', 'quiz_title', 'course_title', 'total_marks', 'earned_marks',
                  'status', 'result', 'started_at', 'ended_at']
        read_only_fields = fields
