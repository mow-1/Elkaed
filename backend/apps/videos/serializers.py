from rest_framework import serializers


class VideoTokenSerializer(serializers.Serializer):
    token           = serializers.UUIDField()
    hls_url         = serializers.CharField()
    expires_at      = serializers.DateTimeField()
    views_remaining = serializers.IntegerField(allow_null=True)


class LessonProgressUpdateSerializer(serializers.Serializer):
    position_seconds = serializers.IntegerField(min_value=0)
    completed        = serializers.BooleanField(required=False, default=False)
