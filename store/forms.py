from django import forms
from .models import Product, Store, Coupon

class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام فروشگاه...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات...'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('category', 'title', 'description', 'price', 'stock', 'image')
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام محصول...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'توضیحات...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'قیمت (تومان)'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد موجودی'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = (
            'code', 'discount_type', 'discount_value',
            'apply_type', 'products', 'category',
            'min_order_amount', 'max_discount_amount',
            'usage_limit', 'per_user_limit',
            'start_date', 'end_date', 'is_active'
        )
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً: SUMMER2024'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مقدار تخفیف'}),
            'apply_type': forms.Select(attrs={'class': 'form-control'}),
            'products': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 5}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '۰ = بدون محدودیت'}),
            'max_discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'خالی = بدون محدودیت'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد کل استفاده'}),
            'per_user_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد استفاده برای هر کاربر'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            from django.utils import timezone
            now = timezone.now()
            self.fields['start_date'].initial = now
            self.fields['end_date'].initial = now + timezone.timedelta(days=30)

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().strip()
            if Coupon.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('این کد تخفیف قبلاً ثبت شده است.')
        return code