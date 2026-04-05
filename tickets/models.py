from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from .notifications import send_ticket_notifications


class Priority(models.Model):
    """РџСЂРёРѕСЂРёС‚РµС‚ С‚РёРєРµС‚Р°"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    
    PRIORITY_CHOICES = [
        (LOW, 'РќРёР·РєРёР№'),
        (MEDIUM, 'РЎСЂРµРґРЅРёР№'),
        (HIGH, 'Р’С‹СЃРѕРєРёР№'),
        (CRITICAL, 'РљСЂРёС‚РёС‡РµСЃРєРёР№'),
    ]
    
    name = models.CharField(max_length=20, choices=PRIORITY_CHOICES, unique=True)
    color = models.CharField(max_length=7, default='#000000', help_text='HEX С†РІРµС‚')
    
    class Meta:
        verbose_name = 'РџСЂРёРѕСЂРёС‚РµС‚'
        verbose_name_plural = 'РџСЂРёРѕСЂРёС‚РµС‚С‹'
        ordering = ['-name']
    
    def __str__(self):
        return self.get_name_display()


class Status(models.Model):
    """РЎС‚Р°С‚СѓСЃ С‚РёРєРµС‚Р°"""
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    WAITING = 'waiting'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    REOPENED = 'reopened'
    
    STATUS_CHOICES = [
        (OPEN, 'РћС‚РєСЂС‹С‚'),
        (IN_PROGRESS, 'Р’ СЂР°Р±РѕС‚Рµ'),
        (WAITING, 'РћР¶РёРґР°РЅРёРµ'),
        (RESOLVED, 'Р РµС€РµРЅ'),
        (CLOSED, 'Р—Р°РєСЂС‹С‚'),
        (REOPENED, 'РџРµСЂРµРѕС‚РєСЂС‹С‚'),
    ]
    
    name = models.CharField(max_length=20, choices=STATUS_CHOICES, unique=True)
    color = models.CharField(max_length=7, default='#808080', help_text='HEX С†РІРµС‚')
    is_final = models.BooleanField(default=False, help_text='Р¤РёРЅР°Р»СЊРЅС‹Р№ СЃС‚Р°С‚СѓСЃ')
    
    class Meta:
        verbose_name = 'РЎС‚Р°С‚СѓСЃ'
        verbose_name_plural = 'РЎС‚Р°С‚СѓСЃС‹'
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


class Tag(models.Model):
    """РўРµРі РґР»СЏ РєР°С‚РµРіРѕСЂРёР·Р°С†РёРё С‚РёРєРµС‚РѕРІ"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#0066cc')
    
    class Meta:
        verbose_name = 'РўРµРі'
        verbose_name_plural = 'РўРµРіРё'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Workstation(models.Model):
    """Р Р°Р±РѕС‡РµРµ РјРµСЃС‚Рѕ (РєРѕРјРїСЊСЋС‚РµСЂ) РІ РєР°Р±РёРЅРµС‚Рµ"""
    room = models.CharField(max_length=100, verbose_name='РљР°Р±РёРЅРµС‚/РћС„РёСЃ')
    number = models.CharField(max_length=50, verbose_name='РќРѕРјРµСЂ/РћРїРёСЃР°РЅРёРµ', 
                             help_text='РќР°РїСЂРёРјРµСЂ: "РџРљ-1", "Р›РµРІС‹Р№ СЃС‚РѕР»", "РњРѕРЅРёС‚РѕСЂ 3" Рё С‚.Рґ.')
    location = models.CharField(max_length=255, blank=True, verbose_name='РџРѕРґСЂРѕР±РЅРѕРµ РјРµСЃС‚РѕРїРѕР»РѕР¶РµРЅРёРµ',
                               help_text='РћРїС†РёРѕРЅР°Р»СЊРЅРѕ: СѓС‚РѕС‡РЅС‘РЅРЅРѕРµ РјРµСЃС‚Рѕ СЂР°СЃРїРѕР»РѕР¶РµРЅРёСЏ')
    
    class Meta:
        verbose_name = 'Р Р°Р±РѕС‡РµРµ РјРµСЃС‚Рѕ'
        verbose_name_plural = 'Р Р°Р±РѕС‡РёРµ РјРµСЃС‚Р°'
        ordering = ['room', 'number']
        unique_together = [('room', 'number')]
    
    def __str__(self):
        return f"{self.room} - {self.number}"


class Tag(models.Model):
    """РўРµРі РґР»СЏ РєР°С‚РµРіРѕСЂРёР·Р°С†РёРё С‚РёРєРµС‚РѕРІ"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#0066cc')
    
    class Meta:
        verbose_name = 'РўРµРі'
        verbose_name_plural = 'РўРµРіРё'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Р“Р»Р°РІРЅР°СЏ РјРѕРґРµР»СЊ С‚РёРєРµС‚Р°"""
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
    title = models.CharField(max_length=255, verbose_name='Р—Р°РіРѕР»РѕРІРѕРє')
    description = models.TextField(verbose_name='РћРїРёСЃР°РЅРёРµ')
    
    # Р С›РЎвЂљР Р…Р С•РЎв‚¬Р ВµР Р…Р С‘РЎРЏ
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tickets', verbose_name='РЎРѕР·РґР°С‚РµР»СЊ')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='assigned_tickets', verbose_name='РќР°Р·РЅР°С‡РµРЅРѕ')
    
    # Р С™Р В»Р В°РЎРѓРЎРѓР С‘РЎвЂћР С‘Р С”Р В°РЎвЂ Р С‘РЎРЏ
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, default=Priority.MEDIUM, 
                                  verbose_name='РџСЂРёРѕСЂРёС‚РµС‚')
    user_urgency = models.CharField(max_length=20, choices=USER_URGENCY_CHOICES, default=URGENCY_NORMAL, verbose_name='Р—Р°РїСЂРѕС€РµРЅРЅР°СЏ СЃСЂРѕС‡РЅРѕСЃС‚СЊ')
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, default=Status.OPEN, 
                               verbose_name='РЎС‚Р°С‚СѓСЃ')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='РўРµРіРё')
    
    # Р вЂ™РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р Вµ Р СР ВµРЎвЂљР С”Р С‘
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='РЎРѕР·РґР°РЅРѕ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='РћР±РЅРѕРІР»РµРЅРѕ')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Р РµС€РµРЅРѕ')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Р—Р°РєСЂС‹С‚Рѕ')
    
    # Р вЂќР С•Р С—Р С•Р В»Р Р…Р С‘РЎвЂљР ВµР В»РЎРЉР Р…РЎвЂ№Р Вµ Р С—Р С•Р В»РЎРЏ
    room = models.CharField(max_length=50, null=True, blank=True, verbose_name='РљР°Р±РёРЅРµС‚/РћС„РёСЃ')
    workstation = models.ForeignKey(Workstation, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='tickets', verbose_name='Р Р°Р±РѕС‡РµРµ РјРµСЃС‚Рѕ/РљРѕРјРїСЊСЋС‚РµСЂ')
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='РЎСЂРѕРє РІС‹РїРѕР»РЅРµРЅРёСЏ')
    estimated_hours = models.FloatField(null=True, blank=True, verbose_name='Р Р°СЃС‡РµС‚РЅС‹Рµ С‡Р°СЃС‹')
    
    class Meta:
        verbose_name = 'РўРёРєРµС‚'
        verbose_name_plural = 'РўРёРєРµС‚С‹'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Р Р€РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р С‘РЎвЂљРЎРЉ resolved_at Р С”Р С•Р С–Р Т‘Р В° РЎРѓРЎвЂљР В°РЎвЂљРЎС“РЎРѓ Р С‘Р В·Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ Р Р…Р В° RESOLVED
        if self.status and self.status.name == Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        # Р Р€РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р С‘РЎвЂљРЎРЉ closed_at Р С”Р С•Р С–Р Т‘Р В° РЎРѓРЎвЂљР В°РЎвЂљРЎС“РЎРѓ Р С‘Р В·Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ Р Р…Р В° CLOSED
        if self.status and self.status.name == Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    """РљРѕРјРјРµРЅС‚Р°СЂРёР№ Рє С‚РёРєРµС‚Сѓ"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name='РўРёРєРµС‚')
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='РђРІС‚РѕСЂ')
    content = models.TextField(verbose_name='РЎРѕРґРµСЂР¶Р°РЅРёРµ')
    
    # Р вЂ™РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р Вµ Р СР ВµРЎвЂљР С”Р С‘
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='РЎРѕР·РґР°РЅРѕ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='РћР±РЅРѕРІР»РµРЅРѕ')
    
    # Р В¤Р В»Р В°Р С–Р С‘
    is_internal = models.BooleanField(default=False, verbose_name='Р’РЅСѓС‚СЂРµРЅРЅРёР№ РєРѕРјРјРµРЅС‚Р°СЂРёР№')
    
    class Meta:
        verbose_name = 'РљРѕРјРјРµРЅС‚Р°СЂРёР№'
        verbose_name_plural = 'РљРѕРјРјРµРЅС‚Р°СЂРёРё'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
        ]
    
    def __str__(self):
        return f"РљРѕРјРјРµРЅС‚Р°СЂРёР№ РѕС‚ {self.author} Рє С‚РёРєРµС‚Сѓ #{self.ticket.id}"


class Attachment(models.Model):
    """Р’Р»РѕР¶РµРЅРёРµ Рє С‚РёРєРµС‚Сѓ РёР»Рё РєРѕРјРјРµРЅС‚Р°СЂРёСЋ"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', 
                               null=True, blank=True, verbose_name='РўРёРєРµС‚')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='attachments', 
                                null=True, blank=True, verbose_name='РљРѕРјРјРµРЅС‚Р°СЂРёР№')
    
    file = models.FileField(
        upload_to='tickets/attachments/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip'])],
        verbose_name='Р¤Р°Р№Р»'
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Р—Р°РіСЂСѓР¶РµРЅРѕ')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Р—Р°РіСЂСѓР¶РµРЅРѕ')
    description = models.CharField(max_length=255, blank=True, verbose_name='РћРїРёСЃР°РЅРёРµ')
    
    class Meta:
        verbose_name = 'Р’Р»РѕР¶РµРЅРёРµ'
        verbose_name_plural = 'Р’Р»РѕР¶РµРЅРёСЏ'
        ordering = ['-uploaded_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(ticket__isnull=False) | models.Q(comment__isnull=False),
                name='attachment_has_ticket_or_comment'
            )
        ]
    
    def __str__(self):
        return f"Р’Р»РѕР¶РµРЅРёРµ Рє С‚РёРєРµС‚Сѓ #{self.ticket.id if self.ticket else 'РєРѕРјРјРµРЅС‚Р°СЂРёСЋ'}"


class TicketHistory(models.Model):
    """РСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ С‚РёРєРµС‚Р°"""
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_ASSIGNED = 'assigned'
    ACTION_STATUS_CHANGED = 'status_changed'
    ACTION_PRIORITY_CHANGED = 'priority_changed'
    
    ACTION_CHOICES = [
        (ACTION_CREATED, 'РЎРѕР·РґР°РЅ'),
        (ACTION_UPDATED, 'РћР±РЅРѕРІР»РµРЅ'),
        (ACTION_ASSIGNED, 'РќР°Р·РЅР°С‡РµРЅ'),
        (ACTION_STATUS_CHANGED, 'РЎС‚Р°С‚СѓСЃ РёР·РјРµРЅРµРЅ'),
        (ACTION_PRIORITY_CHANGED, 'РџСЂРёРѕСЂРёС‚РµС‚ РёР·РјРµРЅРµРЅ'),
    ]
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history', verbose_name='РўРёРєРµС‚')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Р”РµР№СЃС‚РІСѓСЋС‰РµРµ Р»РёС†Рѕ')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Р”РµР№СЃС‚РІРёРµ')
    
    old_value = models.TextField(blank=True, verbose_name='РЎС‚Р°СЂРѕРµ Р·РЅР°С‡РµРЅРёРµ')
    new_value = models.TextField(blank=True, verbose_name='РќРѕРІРѕРµ Р·РЅР°С‡РµРЅРёРµ')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='РЎРѕР·РґР°РЅРѕ')
    
    class Meta:
        verbose_name = 'РСЃС‚РѕСЂРёСЏ'
        verbose_name_plural = 'РСЃС‚РѕСЂРёСЏ'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.ticket} - {self.created_at}"


class UserProfile(models.Model):
    """РџСЂРѕС„РёР»СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ СЃ СЂР°СЃС€РёСЂРµРЅРЅС‹РјРё РїР°СЂР°РјРµС‚СЂР°РјРё"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ')
    is_approved = models.BooleanField(default=False, verbose_name='РћРґРѕР±СЂРµРЅ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='approved_users', verbose_name='РћРґРѕР±СЂРµРЅ РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Р”Р°С‚Р° РѕРґРѕР±СЂРµРЅРёСЏ')
    office_room = models.CharField(max_length=50, blank=True, verbose_name='РљР°Р±РёРЅРµС‚')
    department = models.CharField(max_length=100, blank=True, verbose_name='РћС‚РґРµР»')
    phone = models.CharField(max_length=20, blank=True, verbose_name='РўРµР»РµС„РѕРЅ')
    workstation = models.ForeignKey(
        Workstation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Р Р°Р±РѕС‡РµРµ РјРµСЃС‚Рѕ/РљРѕРјРїСЊСЋС‚РµСЂ',
    )
    notify_email = models.BooleanField(default=True, verbose_name='Email СѓРІРµРґРѕРјР»РµРЅРёСЏ')
    notify_email_address = models.EmailField(blank=True, verbose_name='Email РґР»СЏ СѓРІРµРґРѕРјР»РµРЅРёР№')
    notify_vk = models.BooleanField(default=False, verbose_name='VK СѓРІРµРґРѕРјР»РµРЅРёСЏ')
    notify_browser = models.BooleanField(default=True, verbose_name='РЈРІРµРґРѕРјР»РµРЅРёСЏ РІ Р±СЂР°СѓР·РµСЂРµ')
    vk_user_id = models.CharField(max_length=100, blank=True, verbose_name='VK ID')
    
    class Meta:
        verbose_name = 'РџСЂРѕС„РёР»СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ'
        verbose_name_plural = 'РџСЂРѕС„РёР»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№'
    
    def __str__(self):
        return f"РџСЂРѕС„РёР»СЊ {self.user.username}"


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
        message_text = f'рџ†• РќРѕРІС‹Р№ С‚РёРєРµС‚ #{instance.id}: {instance.title}'
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
        message_text = f'вњЏпёЏ РўРёРєРµС‚ #{instance.id} Р±С‹Р» РёР·РјРµРЅС‘РЅ: {instance.title}'
        for admin in admins:
            cache_key = f'notification_admin_{admin.id}'
            notifications = cache.get(cache_key, [])
            notifications.append({
                'message': message_text,
                'type': 'warning',
                'ticket_id': instance.id
            })
            cache.set(cache_key, notifications, timeout=None)

    # Р вЂ™Р Р…Р ВµРЎв‚¬Р Р…Р С‘Р Вµ РЎС“Р Р†Р ВµР Т‘Р С•Р СР В»Р ВµР Р…Р С‘РЎРЏ (email + VK)
    send_ticket_notifications(instance, created=created)


