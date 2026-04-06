from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from .notifications import send_ticket_notifications


class Priority(models.Model):
    """Приоритет тикета"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    
    PRIORITY_CHOICES = [
        (LOW, 'Низкий'),
        (MEDIUM, 'Средний'),
        (HIGH, 'Высокий'),
        (CRITICAL, 'Критический'),
    ]
    
    name = models.CharField(max_length=20, choices=PRIORITY_CHOICES, unique=True)
    color = models.CharField(max_length=7, default='#000000', help_text='HEX цвет')
    
    class Meta:
        verbose_name = 'Приоритет'
        verbose_name_plural = 'Приоритеты'
        ordering = ['-name']
    
    def __str__(self):
        return self.get_name_display()


class Status(models.Model):
    """Статус тикета"""
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    WAITING = 'waiting'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    REOPENED = 'reopened'
    
    STATUS_CHOICES = [
        (OPEN, 'Открыт'),
        (IN_PROGRESS, 'В работе'),
        (WAITING, 'Ожидание'),
        (RESOLVED, 'Решен'),
        (CLOSED, 'Закрыт'),
        (REOPENED, 'Переоткрыт'),
    ]
    
    name = models.CharField(max_length=20, choices=STATUS_CHOICES, unique=True)
    color = models.CharField(max_length=7, default='#808080', help_text='HEX цвет')
    is_final = models.BooleanField(default=False, help_text='Финальный статус')
    
    class Meta:
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


class Tag(models.Model):
    """Тег для категоризации тикетов."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#0066cc')
    
    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Workstation(models.Model):
    """Рабочее место в кабинете или офисе."""
    room = models.CharField(max_length=100, verbose_name='Кабинет/Офис')
    number = models.CharField(
        max_length=50,
        verbose_name='Номер/Описание',
        help_text='Например: "ПК-1", "Левый стол", "Монитор 3".',
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Подробное местоположение',
        help_text='Опционально: уточненное место расположения.',
    )
    
    class Meta:
        verbose_name = 'Рабочее место'
        verbose_name_plural = 'Рабочие места'
        ordering = ['room', 'number']
        unique_together = [('room', 'number')]
    
    def __str__(self):
        return f"{self.room} - {self.number}"


class Ticket(models.Model):
    """Основная модель тикета."""
    URGENCY_LOW = 'low'
    URGENCY_NORMAL = 'normal'
    URGENCY_URGENT = 'urgent'
    URGENCY_CRITICAL = 'critical'

    USER_URGENCY_CHOICES = [
        (URGENCY_LOW, 'РќРёР·РєР°СЏ'),
        (URGENCY_NORMAL, 'РћР±С‹С‡РЅР°СЏ'),
        (URGENCY_URGENT, 'РЎСЂРѕС‡РЅРѕ'),
        (URGENCY_CRITICAL, 'РљСЂРёС‚РёС‡РЅРѕ'),
    ]
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    
    # Р С›РЎвЂљР Р…Р С•РЎв‚¬Р ВµР Р…Р С‘РЎРЏ
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tickets', verbose_name='Создатель')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name='Назначено',
    )
    
    # Р С™Р В»Р В°РЎРѓРЎРѓР С‘РЎвЂћР С‘Р С”Р В°РЎвЂ Р С‘РЎРЏ
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, default=Priority.MEDIUM, verbose_name='Приоритет')
    user_urgency = models.CharField(max_length=20, choices=USER_URGENCY_CHOICES, default=URGENCY_NORMAL, verbose_name='Запрошенная срочность')
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, default=Status.OPEN, verbose_name='Статус')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='Теги')
    
    # Р вЂ™РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р Вµ Р СР ВµРЎвЂљР С”Р С‘
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Решено')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Закрыто')
    
    # Р вЂќР С•Р С—Р С•Р В»Р Р…Р С‘РЎвЂљР ВµР В»РЎРЉР Р…РЎвЂ№Р Вµ Р С—Р С•Р В»РЎРЏ
    room = models.CharField(max_length=50, null=True, blank=True, verbose_name='Кабинет/Офис')
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        verbose_name='Рабочее место/Компьютер',
    )
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Желаемый срок решения')
    estimated_hours = models.FloatField(null=True, blank=True, verbose_name='Расчетные часы')
    
    class Meta:
        verbose_name = 'Тикет'
        verbose_name_plural = 'Тикеты'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.title}"
    
    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                Ticket.objects.filter(pk=self.pk)
                .values('status_id', 'priority_id', 'assigned_to_id')
                .first()
            )
            self._previous_state = previous or {}

        # Р Р€РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р С‘РЎвЂљРЎРЉ resolved_at Р С”Р С•Р С–Р Т‘Р В° РЎРѓРЎвЂљР В°РЎвЂљРЎС“РЎРѓ Р С‘Р В·Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ Р Р…Р В° RESOLVED
        if self.status and self.status.name == Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        # Р Р€РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р С‘РЎвЂљРЎРЉ closed_at Р С”Р С•Р С–Р Т‘Р В° РЎРѓРЎвЂљР В°РЎвЂљРЎС“РЎРѓ Р С‘Р В·Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ Р Р…Р В° CLOSED
        if self.status and self.status.name == Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Комментарий к тикету."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name='Тикет')
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Автор')
    content = models.TextField(blank=True, verbose_name='Содержание')
    
    # Р вЂ™РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р Вµ Р СР ВµРЎвЂљР С”Р С‘
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    # Р В¤Р В»Р В°Р С–Р С‘
    is_internal = models.BooleanField(default=False, verbose_name='Внутренний комментарий')
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
        ]
    
    def __str__(self):
        return f"Комментарий от {self.author} к тикету #{self.ticket.id}"


class Attachment(models.Model):
    """Вложение к тикету или комментарию."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True, verbose_name='Тикет')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True, verbose_name='Комментарий')
    
    file = models.FileField(
        upload_to='tickets/attachments/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip'])],
        verbose_name='Файл'
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Загружено')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Загружено')
    description = models.CharField(max_length=255, blank=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'
        ordering = ['-uploaded_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(ticket__isnull=False) | models.Q(comment__isnull=False),
                name='attachment_has_ticket_or_comment'
            )
        ]
    
    def __str__(self):
        return f"Вложение к тикету #{self.ticket.id if self.ticket else 'комментарию'}"


class TicketHistory(models.Model):
    """История изменений тикета."""
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_ASSIGNED = 'assigned'
    ACTION_STATUS_CHANGED = 'status_changed'
    ACTION_PRIORITY_CHANGED = 'priority_changed'
    
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Создан'),
        (ACTION_UPDATED, 'Обновлен'),
        (ACTION_ASSIGNED, 'Назначен'),
        (ACTION_STATUS_CHANGED, 'Статус изменен'),
        (ACTION_PRIORITY_CHANGED, 'Приоритет изменен'),
    ]
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history', verbose_name='Тикет')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Действующее лицо')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    
    old_value = models.TextField(blank=True, verbose_name='Старое значение')
    new_value = models.TextField(blank=True, verbose_name='Новое значение')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'История'
        verbose_name_plural = 'История'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.ticket} - {self.created_at}"


class UserProfile(models.Model):
    """Профиль пользователя с расширенными параметрами."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    is_approved = models.BooleanField(default=False, verbose_name='Одобрен администратором')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_users', verbose_name='Одобрен пользователем')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата одобрения')
    office_room = models.CharField(max_length=50, blank=True, verbose_name='Кабинет')
    department = models.CharField(max_length=100, blank=True, verbose_name='Отдел')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Рабочее место/Компьютер',
    )
    notify_email = models.BooleanField(default=True, verbose_name='Email уведомления')
    notify_email_address = models.EmailField(blank=True, verbose_name='Email для уведомлений')
    notify_vk = models.BooleanField(default=False, verbose_name='VK уведомления')
    notify_browser = models.BooleanField(default=True, verbose_name='Уведомления в браузере')
    vk_user_id = models.CharField(max_length=100, blank=True, verbose_name='VK ID')
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"Профиль {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """РЎРѕР·РґР°С‚СЊ РїСЂРѕС„РёР»СЊ РїСЂРё СЃРѕР·РґР°РЅРёРё РЅРѕРІРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """РЎРѕС…СЂР°РЅРёС‚СЊ РїСЂРѕС„РёР»СЊ РїСЂРё СЃРѕС…СЂР°РЅРµРЅРёРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    instance.profile.save()

@receiver(post_save, sender=Ticket)
def notify_admins_on_ticket_change(sender, instance, created, **kwargs):
    """РћС‚РїСЂР°РІРёС‚СЊ СѓРІРµРґРѕРјР»РµРЅРёРµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°Рј РїСЂРё СЃРѕР·РґР°РЅРёРё РёР»Рё РёР·РјРµРЅРµРЅРёРё С‚РёРєРµС‚Р°"""
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.core.cache import cache
    
    # Р СџР С•Р В»РЎС“РЎвЂЎР В°Р ВµР С Р Р†РЎРѓР ВµРЎвЂ¦ Р В°Р Т‘Р СР С‘Р Р…Р С‘РЎРѓРЎвЂљРЎР‚Р В°РЎвЂљР С•РЎР‚Р С•Р Р†
    admins = User.objects.filter(is_staff=True)
    
    if created:
        # Р Р€Р Р†Р ВµР Т‘Р С•Р СР В»Р ВµР Р…Р С‘Р Вµ Р С• Р Р…Р С•Р Р†Р С•Р С РЎвЂљР С‘Р С”Р ВµРЎвЂљР Вµ
        message_text = f'Новый тикет #{instance.id}: {instance.title}'
        for admin in admins:
            # Р РЋР С•РЎвЂ¦РЎР‚Р В°Р Р…РЎРЏР ВµР С РЎС“Р Р†Р ВµР Т‘Р С•Р СР В»Р ВµР Р…Р С‘Р Вµ Р Р† Р С”РЎРЊРЎв‚¬ Р Т‘Р В»РЎРЏ Р В°Р Т‘Р СР С‘Р Р…Р С‘РЎРѓРЎвЂљРЎР‚Р В°РЎвЂљР С•РЎР‚Р С•Р Р†
            cache_key = f'notification_admin_{admin.id}'
            notifications = cache.get(cache_key, [])
            notifications.append({
                'message': message_text,
                'type': 'info',
                'ticket_id': instance.id
            })
            cache.set(cache_key, notifications, timeout=None)
    else:
        # Р Р€Р Р†Р ВµР Т‘Р С•Р СР В»Р ВµР Р…Р С‘Р Вµ Р С•Р В± Р С‘Р В·Р СР ВµР Р…Р ВµР Р…Р С‘Р С‘ РЎвЂљР С‘Р С”Р ВµРЎвЂљР В°
        message_text = f'Тикет #{instance.id} был изменён: {instance.title}'
        for admin in admins:
            cache_key = f'notification_admin_{admin.id}'
            notifications = cache.get(cache_key, [])
            notifications.append({
                'message': message_text,
                'type': 'warning',
                'ticket_id': instance.id
            })
            cache.set(cache_key, notifications, timeout=None)

    if not instance.creator.is_staff:
        profile = getattr(instance.creator, 'profile', None)
        notify_browser = getattr(profile, 'notify_browser', True) if profile else True
        previous = getattr(instance, '_previous_state', {}) or {}
        significant_update = created or any(
            previous.get(field) != getattr(instance, field)
            for field in ('status_id', 'priority_id', 'assigned_to_id')
        )
        if notify_browser and significant_update:
            creator_cache_key = f'notification_user_{instance.creator.id}'
            creator_notifications = cache.get(creator_cache_key, [])
            creator_notifications.append({
                'message': (
                    f'Ваш тикет #{instance.id} принят в работу'
                    if created
                    else f'Ваш тикет #{instance.id} был обновлён'
                ),
                'type': 'info' if created else 'warning',
                'ticket_id': instance.id,
                'url': reverse('ticket_detail', kwargs={'ticket_id': instance.id}),
            })
            cache.set(creator_cache_key, creator_notifications, timeout=None)

    # Р вЂ™Р Р…Р ВµРЎв‚¬Р Р…Р С‘Р Вµ РЎС“Р Р†Р ВµР Т‘Р С•Р СР В»Р ВµР Р…Р С‘РЎРЏ (email + VK)
    send_ticket_notifications(instance, created=created)


