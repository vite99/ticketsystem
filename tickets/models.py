from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    """Тег для категоризации тикетов"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#0066cc')
    
    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Главная модель тикета"""
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    
    # Отношения
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tickets', verbose_name='Создатель')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='assigned_tickets', verbose_name='Назначено')
    
    # Классификация
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, default=Priority.MEDIUM, 
                                  verbose_name='Приоритет')
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, default=Status.OPEN, 
                               verbose_name='Статус')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='Теги')
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Решено')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Закрыто')
    
    # Дополнительные поля
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Срок выполнения')
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
        # Установить resolved_at когда статус изменяется на RESOLVED
        if self.status and self.status.name == Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        # Установить closed_at когда статус изменяется на CLOSED
        if self.status and self.status.name == Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Комментарий к тикету"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name='Тикет')
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    # Флаги
    is_internal = models.BooleanField(default=False, verbose_name='Внутренний комментарий')
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
        ]
    
    def __str__(self):
        return f"Комментарий от {self.author} к тикету #{self.ticket.id}"


class Attachment(models.Model):
    """Вложение к тикету или комментарию"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', 
                               null=True, blank=True, verbose_name='Тикет')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='attachments', 
                                null=True, blank=True, verbose_name='Комментарий')
    
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
    """История изменений тикета"""
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
    """Профиль пользователя с расширенными параметрами"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    is_approved = models.BooleanField(default=False, verbose_name='Одобрен администратором')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='approved_users', verbose_name='Одобрен пользователем')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата одобрения')
    department = models.CharField(max_length=100, blank=True, verbose_name='Отдел')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"Профиль {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создать профиль при создании нового пользователя"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохранить профиль при сохранении пользователя"""
    instance.profile.save()
