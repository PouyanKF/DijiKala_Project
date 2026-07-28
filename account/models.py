from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'مدیر اصلی'),
        ('SELLER', 'فروشنده'),
        ('CUSTOMER', 'مشتری'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='CUSTOMER',
        verbose_name="نقش کاربری"
    )
    phone_number = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name="شماره تلفن"
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="آدرس"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="موجودی کیف پول (تومان)"
    )
    balance_hold = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="موجودی مسدود شده"
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.username

    @property
    def is_seller(self):
        return self.role == 'SELLER'

    @property
    def is_customer(self):
        return self.role == 'CUSTOMER'

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def available_balance(self):
        """موجودی قابل استفاده"""
        return self.balance - self.balance_hold