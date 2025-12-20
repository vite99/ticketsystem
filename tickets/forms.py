from django import forms
from .models import Ticket, Comment, Priority, Status, Tag


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
