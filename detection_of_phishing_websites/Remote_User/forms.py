from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com'})
    )
    phone = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'placeholder': '+1 234 567 8900'})
    )
    country = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'India'})
    )
    state = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Telangana'})
    )
    city = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Hyderabad'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
