from rest_framework import serializers
from .models import Order, OrderItem, WalletTransaction


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WalletTransaction
        fields = ('id', 'type', 'amount', 'original_amount', 'reason_code',
                  'balance_after', 'reference', 'note', 'created_at')
        read_only_fields = fields


class WalletSerializer(serializers.Serializer):
    balance      = serializers.DecimalField(max_digits=10, decimal_places=2)
    transactions = WalletTransactionSerializer(many=True)


class CouponRedeemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


class OrderItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_slug  = serializers.CharField(source='course.slug', read_only=True)

    class Meta:
        model  = OrderItem
        fields = ['id', 'course_title', 'course_slug', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = ['id', 'status', 'payment_method', 'total_price',
                  'coupon_amount', 'created_at', 'items']
        read_only_fields = fields


class KangaPayInitSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()


from .models import FlashSale, Bundle
from apps.courses.serializers import CourseListSerializer


class FlashSaleSerializer(serializers.ModelSerializer):
    course_title   = serializers.CharField(source='course.title', read_only=True)
    original_price = serializers.DecimalField(source='course.price', max_digits=10, decimal_places=2, read_only=True)
    sale_price     = serializers.SerializerMethodField()

    class Meta:
        model  = FlashSale
        fields = ('id', 'course', 'course_title', 'discount_pct', 'original_price', 'sale_price', 'starts_at', 'ends_at')

    def get_sale_price(self, obj):
        return obj.effective_price()


class BundleSerializer(serializers.ModelSerializer):
    courses = CourseListSerializer(many=True, read_only=True)

    class Meta:
        model  = Bundle
        fields = ('id', 'title', 'price', 'courses', 'created_at')


class FlashSaleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FlashSale
        fields = ('course', 'discount_pct', 'starts_at', 'ends_at')


class BundleCreateSerializer(serializers.ModelSerializer):
    course_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    class Meta:
        model  = Bundle
        fields = ('title', 'price', 'course_ids')

    def create(self, validated_data):
        course_ids = validated_data.pop('course_ids', [])
        bundle     = Bundle.objects.create(**validated_data)
        bundle.courses.set(course_ids)
        return bundle
