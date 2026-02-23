from django import forms
from django.contrib.auth.models import User

from .models import Comment, Ticket, UserProfile, Tag


class TicketForm(forms.ModelForm):
    """Форма для создания и редактирования тикета (для администраторов)"""

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги',
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'assigned_to', 'priority', 'status', 'tags', 'workstation', 'due_date', 'estimated_hours']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок тикета'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Подробное описание проблемы'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'workstation': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Расчетное количество часов'}),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'assigned_to': 'Назначить',
            'priority': 'Приоритет',
            'status': 'Статус',
            'workstation': 'Рабочее место/Компьютер',
            'due_date': 'Срок выполнения',
            'estimated_hours': 'Расчетные часы',
        }


class TicketFormUser(forms.ModelForm):
    """Упрощённая форма для обычных пользователей."""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'user_urgency', 'workstation', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок тикета'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Подробное описание проблемы'}),
            'user_urgency': forms.Select(attrs={'class': 'form-control'}),
            'workstation': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'user_urgency': 'Срочность',
            'workstation': 'Рабочее место/Компьютер',
            'due_date': 'Срок выполнения',
        }


class CommentForm(forms.ModelForm):
    """Форма для добавления комментария"""

    class Meta:
        model = Comment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Напишите комментарий...'}),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'content': 'Комментарий',
            'is_internal': 'Внутренний комментарий (не видно клиентам)',
        }


class UserProfileForm(forms.ModelForm):
    """Форма для редактирования профиля пользователя"""

    class Meta:
        model = UserProfile
        fields = ['office_room', 'department', 'phone']
        widgets = {
            'office_room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кабинет'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название отдела'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
        }
        labels = {
            'office_room': 'Кабинет',
            'department': 'Отдел',
            'phone': 'Телефон',
        }


class ApprovalProfileEditForm(forms.ModelForm):
    """Редактирование заявки перед одобрением."""

    class Meta:
        model = UserProfile
        fields = ['office_room', 'department', 'phone']
        widgets = {
            'office_room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кабинет'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Отдел'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
        }
        labels = {
            'office_room': 'Кабинет',
            'department': 'Отдел',
            'phone': 'Телефон',
        }


class NotificationSettingsForm(forms.ModelForm):
    """Настройки уведомлений пользователя."""

    class Meta:
        model = UserProfile
        fields = ['notify_email', 'notify_email_address', 'notify_vk', 'notify_browser', 'vk_user_id']
        widgets = {
            'notify_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_email_address': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Например: admin@example.com'}),
            'notify_vk': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_browser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vk_user_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: id12345678'}),
        }
        labels = {
            'notify_email': 'Получать email уведомления',
            'notify_email_address': 'Email для уведомлений',
            'notify_vk': 'Получать VK уведомления',
            'notify_browser': 'Показывать уведомления в браузере',
            'vk_user_id': 'VK ID',
        }

    def clean_notify_email_address(self):
        return (self.cleaned_data.get('notify_email_address') or '').strip()

    def clean_vk_user_id(self):
        return (self.cleaned_data.get('vk_user_id') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('notify_vk') and not cleaned_data.get('vk_user_id'):
            self.add_error('vk_user_id', 'Укажите VK ID для уведомлений.')
        return cleaned_data


class UserApprovalForm(forms.Form):
    """Форма для одобрения пользователей администратором"""

    reason = forms.CharField(
        label='Причина одобрения',
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительные комментарии (опционально)',
            }
        ),
    )


class UserRejectionForm(forms.Form):
    """Форма для отклонения пользователей администратором"""

    reason = forms.CharField(
        label='Причина отклонения',
        required=True,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Укажите причину отклонения'}
        ),
    )


class RegistrationForm(forms.ModelForm):
    """Форма для регистрации новых пользователей"""

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'}),
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите пароль'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Электронная почта'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
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
