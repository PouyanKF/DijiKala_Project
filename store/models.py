from django.db import models
from django.conf import settings

class Category(models.Model):
    """دسته‌بندی محصولات با پشتیبانی از زیردسته‌ها"""
    title = models.CharField(max_length=100, verbose_name="عنوان دسته‌بندی")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ (آدرس)")
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="دسته‌بندی والد"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="آیکون (کلاس FontAwesome)",
        help_text="مثلاً: fa-laptop, fa-mobile, fa-home"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="توضیحات"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['order', 'title']

    def __str__(self):
        if self.parent:
            return f"{self.parent.title} → {self.title}"
        return self.title
    
    @property
    def full_path(self):
        if self.parent:
            return f"{self.parent.full_path} / {self.title}"
        return self.title
    
    @property
    def level(self):
        if self.parent:
            return self.parent.level + 1
        return 0
    
    @property
    def product_count(self):
        return self.products.count()


class Store(models.Model):
    """فروشگاه"""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stores',
        verbose_name="مالک فروشگاه"
    )
    name = models.CharField(max_length=255, verbose_name="نام فروشگاه")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "فروشگاه"
        verbose_name_plural = "فروشگاه‌ها"

    def __str__(self):
        return self.name


class Product(models.Model):
    """محصول (متعلق به یک فروشگاه و یک دسته‌بندی)"""
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="فروشگاه"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="فروشنده"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="دسته‌بندی"
    )
    title = models.CharField(max_length=255, verbose_name="نام محصول")
    description = models.TextField(verbose_name="توضیحات")
    price = models.IntegerField(verbose_name="قیمت (تومان)")
    stock = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="تصویر محصول"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"

    def __str__(self):
        return self.title


class Cart(models.Model):
    """سبد خرید کاربر"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name="کاربر"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="پرداخت شده؟"
    )
    
    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کد تخفیف اعمال‌شده"
    )

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self):
        return f"سبد خرید {self.user.username} - {'پرداخت شده' if self.is_paid else 'در جریان'}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    """آیتم‌های داخل سبد خرید"""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="سبد خرید"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="محصول"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"

    def __str__(self):
        return f"{self.quantity} عدد از {self.product.title}"

    @property
    def total_price(self):
        return self.quantity * self.product.price


class Transaction(models.Model):
    """تراکنش‌های کیف پول"""
    
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'شارژ کیف پول'),
        ('WITHDRAW', 'برداشت از کیف پول'),
        ('PAYMENT', 'پرداخت خرید'),
        ('REFUND', 'بازگشت وجه'),
        ('SELLER_EARNING', 'درآمد فروشنده'),
        ('SELLER_WITHDRAW', 'برداشت فروشنده'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'در انتظار'),
        ('COMPLETED', 'تکمیل شده'),
        ('FAILED', 'ناموفق'),
        ('CANCELLED', 'لغو شده'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="کاربر"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name="نوع تراکنش"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="مبلغ (تومان)"
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="موجودی پس از تراکنش"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="توضیحات"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="وضعیت"
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="شناسه مرجع"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )
    
    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.user.username} - {self.amount} تومان"


class Coupon(models.Model):
    """کد تخفیف برای محصولات یا کل سبد خرید"""
    
    DISCOUNT_TYPES = [
        ('PERCENT', 'درصدی'),
        ('FIXED', 'مبلغ ثابت'),
    ]
    
    APPLY_TYPES = [
        ('ALL', 'همه محصولات'),
        ('SPECIFIC', 'محصولات خاص'),
        ('CATEGORY', 'دسته‌بندی خاص'),
    ]
    
    code = models.CharField(max_length=50, unique=True, verbose_name="کد تخفیف")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='PERCENT', verbose_name="نوع تخفیف")
    discount_value = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="مقدار تخفیف (درصد یا تومان)")
    apply_type = models.CharField(max_length=10, choices=APPLY_TYPES, default='ALL', verbose_name="نوع اعمال")
    products = models.ManyToManyField('Product', blank=True, verbose_name="محصولات مشمول تخفیف")
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دسته‌بندی مشمول تخفیف")
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="حداقل مبلغ سفارش")
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="حداکثر مبلغ تخفیف")
    usage_limit = models.PositiveIntegerField(default=1, verbose_name="تعداد دفعات استفاده")
    used_count = models.PositiveIntegerField(default=0, verbose_name="تعداد استفاده شده")
    per_user_limit = models.PositiveIntegerField(default=1, verbose_name="حداکثر استفاده برای هر کاربر")
    start_date = models.DateTimeField(verbose_name="تاریخ شروع")
    end_date = models.DateTimeField(verbose_name="تاریخ پایان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupons', verbose_name="ایجادکننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "کد تخفیف"
        verbose_name_plural = "کدهای تخفیف"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}%"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            self.used_count < self.usage_limit
        )
    
    def apply_discount(self, amount):
        if self.discount_type == 'PERCENT':
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, amount)
        return max(0, discount)
    
    def can_use_by_user(self, user):
        if not user.is_authenticated:
            return False
        user_used_count = Cart.objects.filter(user=user, is_paid=True, coupon=self).count()
        return user_used_count < self.per_user_limit