from django.contrib import admin
from .models import Priority, Status, Tag, Workstation, Ticket, Comment, Attachment, TicketHistory, UserProfile


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'is_final')
    search_fields = ('name',)
    list_filter = ('is_final',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ('room', 'number', 'location')
    list_filter = ('room',)
    search_fields = ('room', 'number', 'location')
    ordering = ('room', 'number')


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('author', 'content', 'is_internal', 'created_at')


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ('uploaded_at', 'uploaded_by')


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ('action', 'actor', 'old_value', 'new_value', 'created_at')
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'creator', 'assigned_to', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'tags')
    search_fields = ('title', 'description', 'creator__username', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at', 'closed_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'creator')
        }),
        ('Назначение и статус', {
            'fields': ('assigned_to', 'priority', 'status')
        }),
        ('Местоположение', {
            'fields': ('workstation',)
        }),
        ('Теги и сроки', {
            'fields': ('tags', 'due_date', 'estimated_hours')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CommentInline, AttachmentInline, TicketHistoryInline]
    filter_horizontal = ('tags',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('creator',)
        return self.readonly_fields


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('ticket__title', 'author__username', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Информация', {
            'fields': ('ticket', 'author', 'is_internal')
        }),
        ('Содержание', {
            'fields': ('content',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'uploaded_by', 'uploaded_at', 'description')
    list_filter = ('uploaded_at',)
    search_fields = ('description', 'ticket__title')
    readonly_fields = ('uploaded_at', 'uploaded_by')


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('ticket__title', 'actor__username')
    readonly_fields = ('ticket', 'action', 'actor', 'old_value', 'new_value', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved', 'approved_by', 'approved_at', 'department')
    list_filter = ('is_approved', 'approved_at')
    search_fields = ('user__username', 'user__email', 'department')
    readonly_fields = ('approved_at',)
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Одобрение', {
            'fields': ('is_approved', 'approved_by', 'approved_at')
        }),
        ('Информация', {
            'fields': ('department', 'phone')
        }),
    )

