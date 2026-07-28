from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            ('CUSTOMER', 'مشتری'),
            ('SELLER', 'فروشنده'),
            ('ADMIN', 'ادمین')
        ],
        label="نقش کاربری",
        initial='CUSTOMER',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    admin_secret_code = forms.CharField(
        required=False,
        label="کد اختصاصی ادمین ( ثبت‌نام ادمین)",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'فقط اگر ادمین هستید...'})
    )
    
    phone_number = forms.CharField(
        max_length=11,
        required=False,
        label="شماره تلفن",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثلاً 09123456789'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone_number', 'password1', 'password2', 'role')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        admin_code = cleaned_data.get("admin_secret_code")
        
        if role == 'ADMIN' and admin_code != 'admin':
            raise forms.ValidationError("کد اختصاصی ادمین اشتباه است!")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get("role")
        
        if role == 'ADMIN':
            user.role = 'ADMIN'
            user.is_staff = True
            user.is_superuser = True
        else:
            user.role = role
            user.is_staff = False
            user.is_superuser = False
        
        user.phone_number = self.cleaned_data.get("phone_number", "")
        
        if commit:
            user.save()
        return user