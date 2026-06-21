from django import forms
from django.contrib.auth.models import User

from .models import Comment, Ticket, UserProfile, Tag, Workstation, Attachment


TICKET_TOPIC_PRESETS = (
    ('', 'Выберите тему (шаблон)'),
    ('no_internet', 'Нет интернета / сети'),
    ('printer_issue', 'Проблема с принтером'),
    ('account_access', 'Доступ к аккаунту'),
    ('software_install', 'Установка программы'),
    ('pc_slow', 'Медленно работает компьютер'),
    ('other', 'Другое'),
)

class WorkstationForm(forms.ModelForm):
    class Meta:
        model = Workstation
        fields = ['room', 'number', 'location']
        widgets = {
            'room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: 101 (IT кабинет)'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: ПК-1'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Левый угол, у окна'}),
        }
        labels = {
            'room': 'Кабинет/Офис',
            'number': 'Номер/Описание',
            'location': 'Подробное местоположение',
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Сеть'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Краткое описание тега'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
        }
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'color': 'Цвет',
        }


class TicketForm(forms.ModelForm):
    """Форма для создания и редактирования тикета (для администраторов)."""

    template_topic = forms.ChoiceField(
        choices=TICKET_TOPIC_PRESETS,
        required=False,
        label='Тема',
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
        }),
    )
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
            'title': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
                'placeholder': 'Заголовок тикета',
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
                'rows': 5,
                'placeholder': 'Подробное описание проблемы',
            }),
            'assigned_to': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'}),
            'priority': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'}),
            'status': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'}),
            'workstation': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20', 'type': 'datetime-local'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20', 'placeholder': 'Например: 2'}),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'assigned_to': 'Назначить',
            'priority': 'Приоритет',
            'status': 'Статус',
            'workstation': 'Рабочее место/Компьютер',
            'due_date': 'Желаемый срок решения',
            'estimated_hours': 'Расчётные часы',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            'template_topic',
            'title',
            'description',
            'assigned_to',
            'priority',
            'status',
            'tags',
            'workstation',
            'due_date',
            'estimated_hours',
        ])


class TicketFormUser(forms.ModelForm):
    """Упрощённая форма для обычных пользователей."""

    template_topic = forms.ChoiceField(
        choices=TICKET_TOPIC_PRESETS,
        required=False,
        label='Тема',
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
        }),
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'user_urgency', 'workstation', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
                'placeholder': 'Заголовок тикета',
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
                'rows': 5,
                'placeholder': 'Подробное описание проблемы',
            }),
            'user_urgency': forms.Select(attrs={
                'class': 'hidden',
            }),
            'workstation': forms.Select(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
                'type': 'datetime-local',
            }),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'user_urgency': 'Срочность',
            'workstation': 'Рабочее место/Компьютер',
            'due_date': 'Желаемый срок решения',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            'template_topic',
            'title',
            'description',
            'user_urgency',
            'workstation',
            'due_date',
        ])


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
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '').strip()
        
        # Валидация: должен быть либо комментарий, либо файлы
        # Проверяем файлы через контекст (они приходят в request.FILES)
        # Здесь мы просто проверяем, что не пустое
        if not content:
            # Это разрешено только при условии, что будут файлы
            # Полная проверка проходит в view
            pass
        
        return cleaned_data


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


class AdminUserEditForm(forms.ModelForm):
    """Редактирование основных данных пользователя администратором."""

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
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
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует!')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован!')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = (self.cleaned_data.get('username') or '').strip()
        user.email = (self.cleaned_data.get('email') or '').strip()
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class CommentAttachmentForm(forms.ModelForm):
    """Форма для загрузки вложений к комментарию"""
    
    class Meta:
        model = Attachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Описание файла (опционально)',
            }),
        }
        labels = {
            'file': 'Файл',
            'description': 'Описание',
        }
