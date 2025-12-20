from django import forms
from .models import Ticket, Comment, Priority, Status, Tag, UserProfile
from django.contrib.auth.models import User


class TicketForm(forms.ModelForm):
    """Форма для создания и редактирования тикета"""
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги'
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'assigned_to', 'priority', 'status', 'tags', 'due_date', 'estimated_hours']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Заголовок тикета'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробное описание проблемы'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Расчетное количество часов'
            }),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'assigned_to': 'Назначить',
            'priority': 'Приоритет',
            'status': 'Статус',
            'due_date': 'Срок выполнения',
            'estimated_hours': 'Расчетные часы',
        }


class CommentForm(forms.ModelForm):
    """Форма для добавления комментария"""
    class Meta:
        model = Comment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Напишите комментарий...'
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'content': 'Комментарий',
            'is_internal': 'Внутренний комментарий (не видно клиентам)',
        }


class UserProfileForm(forms.ModelForm):
    """Форма для редактирования профиля пользователя"""
    class Meta:
        model = UserProfile
        fields = ['department', 'phone']
        widgets = {
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название отдела'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Телефон'
            }),
        }
        labels = {
            'department': 'Отдел',
            'phone': 'Телефон',
        }


class UserApprovalForm(forms.Form):
    """Форма для одобрения пользователей администратором"""
    reason = forms.CharField(
        label='Причина одобрения',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные комментарии (опционально)'
        })
    )


class UserRejectionForm(forms.Form):
    """Форма для отклонения пользователей администратором"""
    reason = forms.CharField(
        label='Причина отклонения',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Укажите причину отклонения'
        })
    )


class RegistrationForm(forms.ModelForm):
    """Форма для регистрации новых пользователей"""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Электронная почта'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Фамилия'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
            'email': 'Электронная почта',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }
    
    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError('Пароли не совпадают!')
        return password2
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует!')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован!')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
