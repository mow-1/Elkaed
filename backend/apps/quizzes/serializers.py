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


class AdminAnswerChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AnswerChoice
        fields = ['id', 'text', 'text_en', 'is_correct', 'order', 'image']
        extra_kwargs = {'order': {'required': False}}


class AdminQuestionSerializer(serializers.ModelSerializer):
    choices = AdminAnswerChoiceSerializer(many=True)

    class Meta:
        model  = Question
        fields = ['id', 'text', 'text_en', 'question_type', 'mark', 'order',
                  'explanation', 'explanation_en', 'image', 'choices']
        extra_kwargs = {'order': {'required': False}}


class AdminQuizSerializer(serializers.ModelSerializer):
    """Writable nested serializer: a quiz with its questions and each question's
    choices, created/synced in one call — DRF doesn't do writable nested
    serializers automatically, so create()/update() are overridden below.
    order is auto-assigned from list position when not supplied, so the
    frontend never has to manage indices."""
    questions = AdminQuestionSerializer(many=True)

    class Meta:
        model  = Quiz
        fields = ['id', 'topic', 'title', 'title_en', 'order', 'time_limit', 'pass_mark',
                  'attempts_allowed', 'is_locked', 'hide_results', 'shuffle_questions',
                  'shuffle_answers', 'questions']
        extra_kwargs = {'topic': {'required': False}, 'order': {'required': False}}

    def _save_questions(self, quiz, questions_data):
        quiz.questions.all().delete()  # simplest correct sync: replace wholesale on every save
        for q_index, q_data in enumerate(questions_data):
            choices_data = q_data.pop('choices')
            q_data.setdefault('order', q_index)
            question = Question.objects.create(quiz=quiz, **q_data)
            for c_index, c_data in enumerate(choices_data):
                c_data.setdefault('order', c_index)
                AnswerChoice.objects.create(question=question, **c_data)

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        quiz = Quiz.objects.create(**validated_data)
        self._save_questions(quiz, questions_data)
        return quiz

    def update(self, quiz, validated_data):
        questions_data = validated_data.pop('questions', None)
        for attr, value in validated_data.items():
            setattr(quiz, attr, value)
        quiz.save()
        if questions_data is not None:
            self._save_questions(quiz, questions_data)
        return quiz


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
