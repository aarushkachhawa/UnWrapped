from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import CustomUser, Feedback

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("username", "name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'  # Add 'form-control' class for Bootstrap

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


class AddFeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["feedback", "rating", "email"]

    feedback = forms.CharField(
        label='Please leave your feedback here',
        max_length=1000
    )
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        label='How would you rate our web app? (from 1 to 5)'
    )
    email = forms.EmailField(
        label='Your Email',
        max_length=254,
        required=True
    )

# class CustomLoginForm(forms.Form):
#     username = forms.CharField(max_length=150, label="Username")
#     password = forms.CharField(widget=forms.PasswordInput, label="Password")

#     def clean(self):
#         cleaned_data = super().clean()
#         username = cleaned_data.get("username")
#         password = cleaned_data.get("password")

#         # Check if the user can be authenticated
#         if username and password:
#             user = authenticate(username=username, password=password)
#             if user is None:
#                 raise forms.ValidationError("Invalid username or password.")

#         return cleaned_data