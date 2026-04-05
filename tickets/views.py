from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.db import models
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.utils import OperationalError, ProgrammingError
from itertools import groupby
from .models import Ticket, Comment, Status, Priority, Tag, UserProfile, Workstation, TicketHistory, Attachment
from .forms import (
    TicketForm,
    TicketFormUser,
    CommentForm,
    RegistrationForm,
    NotificationSettingsForm,
    ApprovalProfileEditForm,
    WorkstationForm,
)
from django.urls import reverse, reverse_lazy

COMPLETED_STATUS_NAMES = ['resolved', 'closed']
USER_URGENCY_TO_PRIORITY = {
    Ticket.URGENCY_LOW: Priority.LOW,
    Ticket.URGENCY_NORMAL: Priority.MEDIUM,
    Ticket.URGENCY_URGENT: Priority.HIGH,
    Ticket.URGENCY_CRITICAL: Priority.CRITICAL,
}


class TicketLoginView(LoginView):
    """РџСЂРµРґСЃС‚Р°РІР»РµРЅРёРµ РґР»СЏ РІС…РѕРґР°"""
    template_name = 'tickets/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('ticket_list')


class TicketLogoutView(LogoutView):
    """РџСЂРµРґСЃС‚Р°РІР»РµРЅРёРµ РґР»СЏ РІС‹С…РѕРґР°"""
    next_page = 'ticket_list'
    http_method_names = ['get', 'post', 'options']


def register_view(request):
    """Р РµРіРёСЃС‚СЂР°С†РёСЏ РЅРѕРІРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    if request.user.is_authenticated:
        return redirect('ticket_list')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Регистрация успешна! Пожалуйста, войдите в систему.')
            return redirect('login')
    else:
        form = RegistrationForm()
    
    return render(request, 'tickets/register.html', {'form': form})


def is_admin(user):
    """РџСЂРѕРІРµСЂРєР° РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
    return user.is_staff or user.is_superuser


def is_approved(user):
    """РџСЂРѕРІРµСЂРєР°, РѕРґРѕР±СЂРµРЅ Р»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ"""
    if user.is_staff or user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.is_approved


def require_approval(view_func):
    """Р”РµРєРѕСЂР°С‚РѕСЂ РґР»СЏ РїСЂРѕРІРµСЂРєРё РѕРґРѕР±СЂРµРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if not is_approved(request.user):
            return render(request, 'tickets/pending_approval.html')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def _apply_ticket_filters_and_sorting(queryset, request, *, is_archive):
    """Apply search, filters, sorting and build query-string helpers for templates."""
    search_query = (request.GET.get('q') or '').strip()
    status_id = (request.GET.get('status') or '').strip()
    priority_id = (request.GET.get('priority') or '').strip()
    current_sort = (request.GET.get('sort') or 'id').strip()

    if status_id:
        queryset = queryset.filter(status_id=status_id)

    if priority_id:
        queryset = queryset.filter(priority_id=priority_id)

    if search_query:
        combined_filter = (
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(creator__username__icontains=search_query) |
            Q(creator__first_name__icontains=search_query) |
            Q(creator__last_name__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query) |
            Q(assigned_to__first_name__icontains=search_query) |
            Q(assigned_to__last_name__icontains=search_query) |
            Q(tags__name__icontains=search_query) |
            Q(priority__name__icontains=search_query) |
            Q(status__name__icontains=search_query) |
            Q(room__icontains=search_query) |
            Q(workstation__room__icontains=search_query) |
            Q(workstation__number__icontains=search_query) |
            Q(workstation__location__icontains=search_query)
        )

        normalized_query = search_query.lstrip('#')
        if normalized_query.isdigit():
            combined_filter |= Q(id=int(normalized_query))

        queryset = queryset.filter(combined_filter).distinct()

    if request.GET.get('my_tickets'):
        queryset = queryset.filter(assigned_to=request.user)

    allowed_sort_fields = {
        'id': 'id',
        'title': 'title',
        'priority': 'priority__name',
        'status': 'status__name',
        'created_at': 'created_at',
        'due_date': 'due_date',
    }

    sort_field = current_sort.lstrip('-')
    if sort_field not in allowed_sort_fields:
        current_sort = 'id'
        sort_field = 'id'

    order_by = allowed_sort_fields[sort_field]

    # If the sort param already starts with "-", the same column was clicked again
    # and the ordering must be toggled to descending.
    if current_sort.startswith('-'):
        order_by = f'-{order_by}'

    queryset = queryset.order_by(order_by, '-id')

    query_params = request.GET.copy()
    query_params.pop('page', None)
    page_query_string = query_params.urlencode()

    sort_query_params = request.GET.copy()
    sort_query_params.pop('page', None)
    sort_query_params.pop('sort', None)
    sort_query_string = sort_query_params.urlencode()

    def next_sort(field_name):
        if current_sort == field_name:
            return f'-{field_name}'
        if current_sort == f'-{field_name}':
            return field_name
        return field_name

    context = {
        'search_query': search_query,
        'selected_status': status_id,
        'selected_priority': priority_id,
        'current_filters': request.GET,
        'current_sort': current_sort,
        'query_string': page_query_string,
        'sort_query_string': sort_query_string,
        'next_sort_id': next_sort('id'),
        'next_sort_title': next_sort('title'),
        'next_sort_priority': next_sort('priority'),
        'next_sort_status': next_sort('status'),
        'next_sort_created_at': next_sort('created_at'),
        'next_sort_due_date': next_sort('due_date'),
        'status_choices': Status.objects.filter(name__in=COMPLETED_STATUS_NAMES).order_by('name') if is_archive else Status.objects.exclude(name__in=COMPLETED_STATUS_NAMES).order_by('name'),
        'priority_choices': Priority.objects.all().order_by('name'),
    }
    return queryset, context


@require_approval
def ticket_list(request):
    """РЎРїРёСЃРѕРє РІСЃРµС… С‚РёРєРµС‚РѕРІ СЃ С„РёР»СЊС‚СЂР°С†РёРµР№"""
    from django.core.cache import cache
    
    # РџРѕР»СѓС‡Р°РµРј СѓРІРµРґРѕРјР»РµРЅРёСЏ РґР»СЏ Р°РґРјРёРЅРѕРІ
    if request.user.is_staff:
        cache_key = f'notification_admin_{request.user.id}'
        notifications = cache.get(cache_key, [])
        if notifications:
            # РџРѕРєР°Р·С‹РІР°РµРј СѓРІРµРґРѕРјР»РµРЅРёСЏ
            for notif in notifications:
                if notif['type'] == 'warning':
                    messages.warning(request, notif['message'])
                else:
                    messages.info(request, notif['message'])
            # РћС‡РёС‰Р°РµРј СѓРІРµРґРѕРјР»РµРЅРёСЏ
            cache.delete(cache_key)
    
    tickets = Ticket.objects.exclude(status__name__in=COMPLETED_STATUS_NAMES)
    tickets, list_context = _apply_ticket_filters_and_sorting(tickets, request, is_archive=False)

    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'tickets': page_obj.object_list,
        'statuses': list_context['status_choices'],
        'priorities': list_context['priority_choices'],
        'is_archive': False,
    }
    context.update(list_context)
    return render(request, 'tickets/ticket_list.html', context)


@require_approval
def ticket_archive(request):
    """РђСЂС…РёРІ Р·Р°РІРµСЂС€РµРЅРЅС‹С… С‚РёРєРµС‚РѕРІ."""
    tickets = Ticket.objects.filter(status__name__in=COMPLETED_STATUS_NAMES)
    if not request.user.is_staff:
        tickets = tickets.filter(creator=request.user)

    tickets, list_context = _apply_ticket_filters_and_sorting(tickets, request, is_archive=True)

    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'tickets': page_obj.object_list,
        'statuses': list_context['status_choices'],
        'priorities': list_context['priority_choices'],
        'is_archive': True,
    }
    context.update(list_context)
    return render(request, 'tickets/ticket_list.html', context)


@login_required(login_url='login')
def ticket_detail(request, ticket_id):
    """Р”РµС‚Р°Р»СЊРЅС‹Р№ РїСЂРѕСЃРјРѕС‚СЂ С‚РёРєРµС‚Р°"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.all()
    attachments = ticket.attachments.all()
    
    # РџСЂРѕРІРµСЂРєР° РїСЂР°РІ РґРѕСЃС‚СѓРїР°
    can_edit = request.user == ticket.creator or request.user == ticket.assigned_to or request.user.is_staff
    
    can_cancel_ticket = (
        request.user == ticket.creator
        and not request.user.is_staff
        and ticket.status is not None
        and ticket.status.name == Status.OPEN
    )

    context = {
        'ticket': ticket,
        'comments': comments,
        'attachments': attachments,
        'can_edit': can_edit,
        'can_cancel_ticket': can_cancel_ticket,
        'now': timezone.now(),
    }
    return render(request, 'tickets/ticket_detail.html', context)


@login_required(login_url='login')
def ticket_create(request):
    """РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ С‚РёРєРµС‚Р°"""
    # Р’С‹Р±РёСЂР°РµРј С„РѕСЂРјСѓ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ СЂРѕР»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    form_class = TicketForm if request.user.is_staff else TicketFormUser
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            
            # Р”Р»СЏ РѕР±С‹С‡РЅС‹С… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ СѓСЃС‚Р°РЅР°РІР»РёРІР°РµРј СЃС‚Р°С‚СѓСЃ "РћС‚РєСЂС‹С‚"
            if not request.user.is_staff:
                ticket.status = Status.objects.filter(name='open').first() or Status.objects.first()
                priority_name = USER_URGENCY_TO_PRIORITY.get(ticket.user_urgency, Priority.MEDIUM)
                ticket.priority = (
                    Priority.objects.filter(name=priority_name).first()
                    or Priority.objects.filter(name=Priority.MEDIUM).first()
                    or Priority.objects.first()
                )
            
            ticket.save()
            if hasattr(form, 'save_m2m'):
                form.save_m2m()  # РЎРѕС…СЂР°РЅРёС‚СЊ M2M РѕС‚РЅРѕС€РµРЅРёСЏ (С‚РµРіРё) РµСЃР»Рё РѕРЅРё РµСЃС‚СЊ
            for uploaded_file in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    ticket=ticket,
                    file=uploaded_file,
                    uploaded_by=request.user,
                )
            
            # РћС‚РїСЂР°РІР»СЏРµРј СЃРѕРѕР±С‰РµРЅРёРµ РѕР± СѓСЃРїРµС€РЅРѕРј СЃРѕР·РґР°РЅРёРё
            messages.success(request, f'✅ Тикет #{ticket.id} успешно создан!')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = form_class()
    
    return render(request, 'tickets/ticket_form.html', {'form': form, 'title': 'Создать тикет'})


@login_required(login_url='login')
def ticket_edit(request, ticket_id):
    """Р РµРґР°РєС‚РёСЂРѕРІР°РЅРёРµ С‚РёРєРµС‚Р°"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # РџСЂРѕРІРµСЂРєР° РїСЂР°РІ РґРѕСЃС‚СѓРїР°
    if request.user != ticket.creator and request.user != ticket.assigned_to and not request.user.is_staff:
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    # Р’С‹Р±РёСЂР°РµРј С„РѕСЂРјСѓ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ СЂРѕР»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    form_class = TicketForm if request.user.is_staff else TicketFormUser
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            if not request.user.is_staff:
                priority_name = USER_URGENCY_TO_PRIORITY.get(ticket.user_urgency, Priority.MEDIUM)
                ticket.priority = (
                    Priority.objects.filter(name=priority_name).first()
                    or Priority.objects.filter(name=Priority.MEDIUM).first()
                    or Priority.objects.first()
                )
            ticket.save()
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
            attachment_ids_to_delete = request.POST.getlist('delete_attachments')
            if attachment_ids_to_delete:
                attachments_to_delete = ticket.attachments.filter(id__in=attachment_ids_to_delete)
                for attachment in attachments_to_delete:
                    attachment.file.delete(save=False)
                    attachment.delete()
            for uploaded_file in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    ticket=ticket,
                    file=uploaded_file,
                    uploaded_by=request.user,
                )
            
            # РћС‚РїСЂР°РІР»СЏРµРј СЃРѕРѕР±С‰РµРЅРёРµ РѕР± СѓСЃРїРµС€РЅРѕРј РѕР±РЅРѕРІР»РµРЅРёРё
            messages.success(request, f'✅ Тикет #{ticket.id} успешно обновлен!')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = form_class(instance=ticket)
    
    return render(
        request,
        'tickets/ticket_edit.html',
        {
            'form': form,
            'ticket': ticket,
            'existing_attachments': ticket.attachments.all(),
            'title': 'Редактировать тикет',
        },
    )


@login_required(login_url='login')
@require_POST
def confirm_ticket_resolution(request, ticket_id):
    """Подтверждение решения тикета его создателем."""
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.user != ticket.creator and not request.user.is_staff:
        messages.error(request, '❌ Только создатель тикета может подтвердить решение.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    if not ticket.status or ticket.status.name != Status.RESOLVED:
        messages.error(request, '❌ Подтверждение доступно только для тикетов со статусом "Решен".')
        return redirect('ticket_detail', ticket_id=ticket.id)

    closed_status = Status.objects.filter(name=Status.CLOSED).first()
    if not closed_status:
        messages.error(request, '❌ Статус "Закрыт" не найден.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_STATUS_CHANGED,
        old_value=ticket.status.get_name_display(),
        new_value=closed_status.get_name_display(),
    )

    ticket.status = closed_status
    ticket.save(update_fields=['status', 'updated_at', 'closed_at'])
    messages.success(request, f'Тикет #{ticket.id} закрыт после подтверждения решения.')
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
@require_POST
def reopen_ticket_by_creator(request, ticket_id):
    """Переоткрытие решенного тикета его создателем."""
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.user != ticket.creator and not request.user.is_staff:
        messages.error(request, '❌ Только создатель тикета может сообщить, что проблема осталась.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    if not ticket.status or ticket.status.name != Status.RESOLVED:
        messages.error(request, '❌ Переоткрытие доступно только для тикетов со статусом "Решен".')
        return redirect('ticket_detail', ticket_id=ticket.id)

    reopened_status = Status.objects.filter(name=Status.REOPENED).first()
    if not reopened_status:
        reopened_status = Status.objects.filter(name=Status.OPEN).first()

    if not reopened_status:
        messages.error(request, '❌ Не найден статус для повторного открытия тикета.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_STATUS_CHANGED,
        old_value=ticket.status.get_name_display(),
        new_value=reopened_status.get_name_display(),
    )

    ticket.status = reopened_status
    ticket.save(update_fields=['status', 'updated_at'])
    messages.success(request, f'Тикет #{ticket.id} переоткрыт. Исполнитель увидит, что проблема осталась.')
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
@require_POST
def cancel_ticket_by_creator(request, ticket_id):
    """Отзыв заявки создателем, пока тикет еще не взят в работу."""
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.user != ticket.creator and not request.user.is_staff:
        messages.error(request, '❌ Только создатель тикета может отозвать заявку.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    if not ticket.status or ticket.status.name != Status.OPEN:
        messages.error(request, '❌ Отозвать можно только тикет со статусом "Открыт".')
        return redirect('ticket_detail', ticket_id=ticket.id)

    closed_status = Status.objects.filter(name=Status.CLOSED).first()
    if not closed_status:
        messages.error(request, '❌ Статус "Закрыт" не найден.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_STATUS_CHANGED,
        old_value=ticket.status.get_name_display(),
        new_value=closed_status.get_name_display(),
    )

    ticket.status = closed_status
    ticket.save(update_fields=['status', 'updated_at', 'closed_at'])
    messages.success(request, f'Заявка по тикету #{ticket.id} отозвана.')
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_POST
def assign_ticket_to_me(request, ticket_id):
    """РќР°Р·РЅР°С‡РёС‚СЊ С‚РёРєРµС‚ С‚РµРєСѓС‰РµРјСѓ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.assigned_to = request.user
    ticket.save(update_fields=['assigned_to', 'updated_at'])
    messages.success(request, f'Тикет #{ticket.id} назначен на вас.')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_POST
def unassign_ticket(request, ticket_id):
    """Снять назначение тикета с текущего пользователя."""
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.assigned_to != request.user:
        messages.error(request, '❌ Вы не являетесь исполнителем этого тикета.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_ASSIGNED,
        old_value=request.user.get_full_name() or request.user.username,
        new_value='Не назначено',
    )

    ticket.assigned_to = None
    ticket.save(update_fields=['assigned_to', 'updated_at'])
    messages.success(request, f'Тикет #{ticket.id} снят с вас.')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
def add_comment(request, ticket_id):
    """Р”РѕР±Р°РІР»РµРЅРёРµ РєРѕРјРјРµРЅС‚Р°СЂРёСЏ Рє С‚РёРєРµС‚Сѓ"""
    from .notifications import send_comment_notification
    from django.core.cache import cache

    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()

            creator_user = ticket.creator
            if (
                creator_user
                and creator_user != request.user
                and not creator_user.is_staff
                and not comment.is_internal
            ):
                creator_profile = getattr(creator_user, 'profile', None)
                creator_notify_browser = getattr(creator_profile, 'notify_browser', True) if creator_profile else True
                if creator_notify_browser:
                    creator_cache_key = f'notification_user_{creator_user.id}'
                    creator_notifications = cache.get(creator_cache_key, [])
                    creator_notifications.append({
                        'message': f'Новый комментарий в вашем тикете #{ticket.id}: {ticket.title}',
                        'type': 'warning',
                        'ticket_id': ticket.id,
                        'comment_id': comment.id,
                        'url': reverse('ticket_detail', kwargs={'ticket_id': ticket.id}),
                    })
                    cache.set(creator_cache_key, creator_notifications, timeout=None)

            assigned_user = ticket.assigned_to
            if assigned_user and assigned_user != request.user:
                should_notify = not comment.is_internal or assigned_user.is_staff
                if should_notify:
                    cache_key = f'notification_comments_{assigned_user.id}'
                    notifications = cache.get(cache_key, [])
                    notifications.append({
                        'message': f'Новый комментарий в тикете #{ticket.id}: {ticket.title}',
                        'type': 'warning',
                        'ticket_id': ticket.id,
                        'comment_id': comment.id,
                        'url': reverse('ticket_detail', kwargs={'ticket_id': ticket.id}),
                    })
                    cache.set(cache_key, notifications, timeout=None)
            send_comment_notification(comment)
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = CommentForm()
    
    return render(request, 'tickets/comment_form.html', {'form': form, 'ticket': ticket})


@login_required(login_url='login')
def my_dashboard(request):
    """Р›РёС‡РЅС‹Р№ РєР°Р±РёРЅРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    created_tickets = Ticket.objects.filter(creator=request.user)
    assigned_tickets = Ticket.objects.filter(assigned_to=request.user)
    
    # РЎС‚Р°С‚РёСЃС‚РёРєР°
    open_tickets = Ticket.objects.filter(
        assigned_to=request.user,
        status__name__in=['open', 'in_progress']
    ).count()
    
    resolved_tickets = Ticket.objects.filter(
        assigned_to=request.user,
        status__name='resolved'
    ).count()
    
    context = {
        'created_tickets': created_tickets[:5],
        'assigned_tickets': assigned_tickets[:5],
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'total_tickets': created_tickets.count() + assigned_tickets.count(),
    }
    return render(request, 'tickets/dashboard.html', context)


@require_approval
def ticket_statistics(request):
    """РЎС‚Р°С‚РёСЃС‚РёРєР° РїРѕ С‚РёРєРµС‚Р°Рј."""
    if request.user.is_staff:
        tickets = Ticket.objects.all()
        scope_label = 'Р’СЃРµ С‚РёРєРµС‚С‹'
    else:
        tickets = Ticket.objects.filter(
            Q(creator=request.user) | Q(assigned_to=request.user)
        ).distinct()
        scope_label = 'РњРѕРё С‚РёРєРµС‚С‹'

    total_tickets = tickets.count()
    status_stats = (
        tickets.values('status__name', 'status__color')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    priority_stats = (
        tickets.values('priority__name', 'priority__color')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    top_creators = (
        tickets.values('creator__username')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    top_assignees = (
        tickets.exclude(assigned_to__isnull=True)
        .values('assigned_to__username')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    trend_raw = (
        tickets.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    trend_labels = [item['day'].strftime('%d.%m') for item in trend_raw if item['day']]
    trend_counts = [item['count'] for item in trend_raw if item['day']]

    def with_percent(rows, name_key, color_key, fallback_name):
        result = []
        for row in rows:
            count = row['count']
            percent = round((count / total_tickets) * 100, 1) if total_tickets else 0
            result.append({
                'name': row.get(name_key) or fallback_name,
                'color': row.get(color_key) or '#6c757d',
                'count': count,
                'percent': percent,
            })
        return result

    status_rows = with_percent(status_stats, 'status__name', 'status__color', 'Р‘РµР· СЃС‚Р°С‚СѓСЃР°')
    priority_rows = with_percent(priority_stats, 'priority__name', 'priority__color', 'Р‘РµР· РїСЂРёРѕСЂРёС‚РµС‚Р°')

    context = {
        'scope_label': scope_label,
        'total_tickets': total_tickets,
        'open_tickets': tickets.filter(status__name__in=['open', 'in_progress', 'reopened']).count(),
        'resolved_tickets': tickets.filter(status__name='resolved').count(),
        'closed_tickets': tickets.filter(status__name='closed').count(),
        'status_stats': status_rows,
        'priority_stats': priority_rows,
        'top_creators': top_creators,
        'top_assignees': top_assignees,
        'trend_labels': trend_labels,
        'trend_counts': trend_counts,
    }
    return render(request, 'tickets/ticket_statistics.html', context)


@require_approval
def notification_settings(request):
    """РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ РЅР°СЃС‚СЂРѕР№РєРё СѓРІРµРґРѕРјР»РµРЅРёР№."""
    profile = request.user.profile
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки уведомлений сохранены.')
            return redirect('notification_settings')
    else:
        form = NotificationSettingsForm(instance=profile)

    return render(request, 'tickets/notification_settings.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_dashboard(request):
    """РђРґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅС‹Р№ РєР°Р±РёРЅРµС‚ СЃ РѕР±С‰РµР№ СЃС‚Р°С‚РёСЃС‚РёРєРѕР№"""
    # РћР±С‰Р°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°
    total_users = User.objects.count()
    approved_users = UserProfile.objects.filter(is_approved=True).count()
    pending_users = UserProfile.objects.filter(is_approved=False).exclude(user__is_staff=True).count()
    
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status__name__in=['open', 'in_progress', 'reopened']).count()
    resolved_tickets = Ticket.objects.filter(status__name='resolved').count()
    closed_tickets = Ticket.objects.filter(status__name='closed').count()
    
    # РўРёРєРµС‚С‹ РїРѕ РїСЂРёРѕСЂРёС‚РµС‚Сѓ
    critical_tickets = Ticket.objects.filter(priority__name='critical').count()
    high_tickets = Ticket.objects.filter(priority__name='high').count()
    
    # РџРѕСЃР»РµРґРЅРёРµ С‚РёРєРµС‚С‹
    recent_tickets = Ticket.objects.all()[:10]
    
    # РЎС‚Р°С‚РёСЃС‚РёРєР° РїРѕ СЃС‚Р°С‚СѓСЃР°Рј
    status_stats = Status.objects.all().annotate(
        count=models.Count('ticket')
    ).order_by('-count')
    
    # РЎР°РјС‹Рµ Р°РєС‚РёРІРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»Рё
    top_assignees = User.objects.annotate(
        assigned_count=models.Count('assigned_tickets')
    ).filter(assigned_count__gt=0).order_by('-assigned_count')[:5]
    
    context = {
        'total_users': total_users,
        'approved_users': approved_users,
        'pending_users': pending_users,
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'closed_tickets': closed_tickets,
        'critical_tickets': critical_tickets,
        'high_tickets': high_tickets,
        'recent_tickets': recent_tickets,
        'status_stats': status_stats,
        'top_assignees': top_assignees,
    }
    return render(request, 'tickets/admin_dashboard.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def user_approval_list(request):
    """РЎРїРёСЃРѕРє РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№, РѕР¶РёРґР°СЋС‰РёС… РѕРґРѕР±СЂРµРЅРёСЏ (РґР»СЏ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРІ)"""
    # РџРѕР»СѓС‡Р°РµРј РІСЃРµС… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ Рё РѕР±РµСЃРїРµС‡РёРІР°РµРј РЅР°Р»РёС‡РёРµ РїСЂРѕС„РёР»СЏ
    all_users = User.objects.all()
    
    # РЈР±РµРґРёРјСЃСЏ, С‡С‚Рѕ Сѓ РєР°Р¶РґРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РµСЃС‚СЊ РїСЂРѕС„РёР»СЊ
    for user in all_users:
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
    
    # РўРµРїРµСЂСЊ С„РёР»СЊС‚СЂСѓРµРј РїРѕ СЃС‚Р°С‚СѓСЃСѓ РѕРґРѕР±СЂРµРЅРёСЏ (РёСЃРєР»СЋС‡Р°СЏ С€С‚Р°С‚)
    pending_users = User.objects.filter(profile__is_approved=False).exclude(is_staff=True)
    approved_users = User.objects.filter(profile__is_approved=True).exclude(is_staff=True)
    
    context = {
        'pending_users': pending_users,
        'approved_users': approved_users,
    }
    return render(request, 'tickets/user_approval_list.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def approve_user(request, user_id):
    """РћРґРѕР±СЂРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    rooms = Workstation.objects.values_list('room', flat=True).distinct().order_by('room')

    if request.method == 'POST':
        form = ApprovalProfileEditForm(request.POST, instance=profile)
        action = request.POST.get('action')
        if form.is_valid():
            updated_profile = form.save(commit=False)
            workstation_id = request.POST.get('workstation_id')
            if workstation_id:
                ws = Workstation.objects.filter(id=workstation_id).first()
                updated_profile.workstation = ws
            else:
                updated_profile.workstation = None
            if action == 'approve':
                updated_profile.is_approved = True
                updated_profile.approved_by = request.user
                updated_profile.approved_at = timezone.now()
                updated_profile.save()
                messages.success(request, f'Пользователь {user.username} успешно одобрен.')
                return redirect('user_approval_list')

            updated_profile.save()
            messages.success(request, f'Данные заявки пользователя {user.username} обновлены.')
            return redirect('approve_user', user_id=user.id)
    else:
        form = ApprovalProfileEditForm(instance=profile)

    context = {'user': user, 'form': form, 'rooms': rooms}
    return render(request, 'tickets/approve_user.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def workstations_by_room(request):
    from django.http import JsonResponse

    room = request.GET.get('room', '').strip()
    if not room:
        return JsonResponse({'workstations': []})

    workstations = Workstation.objects.filter(room=room).order_by('number')
    data = [{'id': w.id, 'label': str(w)} for w in workstations]
    return JsonResponse({'workstations': data})


@login_required(login_url='login')
@user_passes_test(is_admin)
def reject_user(request, user_id):
    """РћС‚РєР»РѕРЅРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.is_active = False
        user.save()
        messages.success(request, f'Пользователь {user.username} деактивирован.')
        return redirect('user_approval_list')
    
    context = {'user': user}
    return render(request, 'tickets/reject_user.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def revoke_approval(request, user_id):
    """РћС‚РѕР·РІР°С‚СЊ РѕРґРѕР±СЂРµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.profile.is_approved = False
        user.profile.approved_by = None
        user.profile.approved_at = None
        user.profile.save()
        messages.success(request, f'Одобрение пользователя {user.username} отозвано.')
        return redirect('user_approval_list')
    
    context = {'user': user}
    return render(request, 'tickets/revoke_approval.html', context)



@login_required(login_url='login')
@user_passes_test(is_admin)
def workstation_list(request):
    queryset = Workstation.objects.all().order_by('room', 'number')
    grouped = {k: list(v) for k, v in groupby(queryset, key=lambda w: w.room)}
    context = {'grouped': grouped, 'total': queryset.count()}
    return render(request, 'tickets/workstation_list.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def workstation_create(request):
    if request.method == 'POST':
        form = WorkstationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Рабочее место добавлено.')
            return redirect('workstation_list')
    else:
        form = WorkstationForm()

    return render(
        request,
        'tickets/workstation_form.html',
        {'form': form, 'title': 'Добавить рабочее место'},
    )


@login_required(login_url='login')
@user_passes_test(is_admin)
def workstation_edit(request, workstation_id):
    workstation = get_object_or_404(Workstation, id=workstation_id)
    if request.method == 'POST':
        form = WorkstationForm(request.POST, instance=workstation)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Рабочее место обновлено.')
            return redirect('workstation_list')
    else:
        form = WorkstationForm(instance=workstation)

    return render(
        request,
        'tickets/workstation_form.html',
        {'form': form, 'title': 'Редактировать рабочее место', 'workstation': workstation},
    )


@login_required(login_url='login')
@user_passes_test(is_admin)
def user_detail_admin(request, user_id):
    """Страница профиля пользователя для администраторов"""
    target_user = get_object_or_404(User, id=user_id)
    
    # Получить профиль пользователя
    try:
        profile = target_user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=target_user)
    
    # Получить все тикеты (созданные и назначенные)
    created_tickets = Ticket.objects.filter(creator=target_user).select_related('status', 'priority')
    assigned_tickets = Ticket.objects.filter(assigned_to=target_user).select_related('status', 'priority')
    
    # Объединить и отсортировать
    all_tickets = list(created_tickets) + list(assigned_tickets)
    all_tickets = sorted(all_tickets, key=lambda t: t.created_at, reverse=True)
    
    # Подсчитать статистику
    open_statuses = ['OPEN', 'IN_PROGRESS', 'WAITING']
    closed_statuses = ['CLOSED', 'RESOLVED']
    
    total_tickets = len(all_tickets)
    open_tickets = sum(1 for t in all_tickets if t.status and t.status.name in open_statuses)
    closed_tickets = sum(1 for t in all_tickets if t.status and t.status.name in closed_statuses)
    
    # Пагинация
    paginator = Paginator(all_tickets, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'target_user': target_user,
        'profile': profile,
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'closed_tickets': closed_tickets,
        'page_obj': page_obj,
        'all_tickets': page_obj.object_list,
    }
    
    return render(request, 'tickets/user_detail_admin.html', context)


@login_required(login_url='login')
@require_POST
def change_ticket_status(request, ticket_id):
    """Изменить статус тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверка прав доступа (только создатель, назначенный или администратор)
    if not (request.user == ticket.creator or request.user == ticket.assigned_to or request.user.is_staff):
        messages.error(request, '❌ У вас нет прав для изменения статуса этого тикета.')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Получить новый статус
    new_status_name = request.POST.get('status')
    if not new_status_name:
        messages.error(request, '❌ Статус не указан.')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Получить объект Status
    try:
        new_status = Status.objects.get(name=new_status_name)
    except Status.DoesNotExist:
        messages.error(request, f'❌ Статус "{new_status_name}" не существует.')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Сохранить старый статус для истории
    old_status = ticket.status
    
    # Изменить статус
    ticket.status = new_status
    ticket.save()
    
    # Добавить запись в историю
    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_STATUS_CHANGED,
        old_value=str(old_status) if old_status else '',
        new_value=str(new_status)
    )
    
    messages.success(request, f'✅ Статус изменён на "{new_status}".')
    return redirect('ticket_detail', ticket_id=ticket_id)


@login_required(login_url='login')
@require_POST
def mark_ticket_unresolved(request, ticket_id):
    """Отметить, что проблема не решена - вернуть в статус 'В работе'"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверка: только создатель тикета может сказать, что проблема не решена
    if request.user != ticket.creator:
        messages.error(request, '❌ Только создатель тикета может отметить, что проблема не решена.')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Проверка: статус должен быть "Решен"
    if ticket.status is None or ticket.status.name != Status.RESOLVED:
        messages.error(request, '❌ Тикет должен быть в статусе "Решен".')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Получить комментарий пользователя
    comment_text = request.POST.get('comment', '').strip()
    if not comment_text:
        messages.error(request, '❌ Пожалуйста, опишите проблему.')
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    # Сохранить старый статус
    old_status = ticket.status
    
    # Изменить статус на "В работе"
    in_progress_status = Status.objects.get(name=Status.IN_PROGRESS)
    ticket.status = in_progress_status
    ticket.save()
    
    # Добавить комментарий
    comment = Comment.objects.create(
        ticket=ticket,
        author=request.user,
        content=comment_text,
        is_internal=False
    )
    
    # Добавить запись в историю
    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.ACTION_STATUS_CHANGED,
        old_value=str(old_status),
        new_value=str(in_progress_status)
    )
    
    messages.success(request, '✅ Тикет возвращён в работу. Пожалуйста, дождитесь ответа.')
    return redirect('ticket_detail', ticket_id=ticket_id)


# =========================
# HTMX Live Update Views
# =========================

@login_required(login_url='login')
def ticket_status_partial(request, ticket_id):
    """Partial для отображения статуса тикета (live updates)"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    context = {'ticket': ticket}
    return render(request, 'tickets/partials/ticket_status_partial.html', context)


@login_required(login_url='login')
def ticket_comments_partial(request, ticket_id):
    """Partial для отображения комментариев (live updates)"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.all()
    context = {
        'ticket': ticket,
        'comments': comments,
    }
    return render(request, 'tickets/partials/ticket_comments_partial.html', context)


@login_required(login_url='login')
def new_tickets_count(request):
    """API endpoint для получения количества новых тикетов (для администраторов)"""
    from django.http import JsonResponse
    
    if not request.user.is_staff:
        return JsonResponse({'count': 0})
    
    # Подсчитать открытые тикеты
    open_status = Status.objects.filter(name=Status.OPEN).first()
    if open_status:
        count = Ticket.objects.filter(status=open_status).count()
    else:
        count = 0
    
    return JsonResponse({'count': count})


@login_required(login_url='login')
def new_tickets_badge(request):
    """Partial для значка "Новые тикеты" (live updates)"""
    if not request.user.is_staff:
        return render(request, 'tickets/partials/new_tickets_badge.html', {'count': 0})
    
    open_status = Status.objects.filter(name=Status.OPEN).first()
    if open_status:
        count = Ticket.objects.filter(status=open_status).count()
    else:
        count = 0
    
    context = {'count': count}
    return render(request, 'tickets/partials/new_tickets_badge.html', context)


@login_required(login_url='login')
def ticket_list_rows_partial(request):
    """Partial для строк таблицы списка тикетов (live updates)"""
    # Получить параметры фильтрации из GET параметров
    filter_status = request.GET.get('status', '')
    filter_priority = request.GET.get('priority', '')
    filter_creator = request.GET.get('creator', '')
    filter_assigned = request.GET.get('assigned', '')
    search_query = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', '-created_at')
    is_archive = request.GET.get('archive') == '1'
    
    # Начальный queryset
    if is_archive:
        tickets = Ticket.objects.filter(status__name__in=COMPLETED_STATUS_NAMES)
    else:
        tickets = Ticket.objects.exclude(status__name__in=COMPLETED_STATUS_NAMES)
    
    # Фильтрация
    if filter_status:
        tickets = tickets.filter(status_id=filter_status)
    if filter_priority:
        tickets = tickets.filter(priority_id=filter_priority)
    if filter_creator:
        tickets = tickets.filter(creator_id=filter_creator)
    if filter_assigned:
        tickets = tickets.filter(assigned_to_id=filter_assigned)
    
    # Поиск
    if search_query:
        tickets = tickets.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    
    # Оптимизация запросов
    tickets = tickets.select_related(
        'status', 'priority', 'creator', 'assigned_to', 'workstation'
    ).order_by(sort)
    
    # Пагинация если требуется
    page_number = request.GET.get('page', 1)
    paginator = Paginator(tickets, 20)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tickets': page_obj.object_list,
        'is_archive': is_archive,
    }
    return render(request, 'tickets/partials/ticket_list_rows_partial.html', context)


@login_required(login_url='login')
def ticket_count_partial(request):
    """Partial для счётчика количества тикетов (live updates)"""
    is_archive = request.GET.get('archive') == '1'
    
    # Получить параметры фильтрации
    filter_status = request.GET.get('status', '')
    filter_priority = request.GET.get('priority', '')
    filter_creator = request.GET.get('creator', '')
    filter_assigned = request.GET.get('assigned', '')
    search_query = request.GET.get('search', '').strip()
    
    # Начальный queryset
    if is_archive:
        tickets = Ticket.objects.filter(status__name__in=COMPLETED_STATUS_NAMES)
    else:
        tickets = Ticket.objects.exclude(status__name__in=COMPLETED_STATUS_NAMES)
    
    # Фильтрация
    if filter_status:
        tickets = tickets.filter(status_id=filter_status)
    if filter_priority:
        tickets = tickets.filter(priority_id=filter_priority)
    if filter_creator:
        tickets = tickets.filter(creator_id=filter_creator)
    if filter_assigned:
        tickets = tickets.filter(assigned_to_id=filter_assigned)
    
    # Поиск
    if search_query:
        tickets = tickets.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    
    count = tickets.count()
    
    context = {'count': count}
    return render(request, 'tickets/partials/ticket_count_partial.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def workstation_delete(request, workstation_id):
    workstation = get_object_or_404(Workstation, id=workstation_id)

    if request.method == 'POST':
        has_tickets = workstation.tickets.exists()
        users_relation = getattr(workstation, 'users', None)
        has_users = users_relation.exists() if users_relation is not None else False
        if has_tickets or has_users:
            messages.error(request, '❌ Нельзя удалить: есть привязанные тикеты или пользователи.')
            return redirect('workstation_list')

        workstation.delete()
        messages.success(request, '✅ Рабочее место удалено.')
        return redirect('workstation_list')

    return render(request, 'tickets/workstation_confirm_delete.html', {'workstation': workstation})


@require_approval
def get_new_tickets(request):
    """API endpoint РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РЅРѕРІС‹С… С‚РёРєРµС‚РѕРІ (РґР»СЏ AJAX)"""
    from django.http import JsonResponse

    if not request.user.is_staff:
        return JsonResponse({'success': True, 'tickets': [], 'count': 0})
    try:
        if hasattr(request.user, 'profile') and not request.user.profile.notify_browser:
            return JsonResponse({'success': True, 'tickets': [], 'count': 0})
    except (OperationalError, ProgrammingError):
        # РњРёРіСЂР°С†РёРё РїСЂРѕС„РёР»СЏ РµС‰Рµ РЅРµ РїСЂРёРјРµРЅРµРЅС‹: РЅРµ Р±Р»РѕРєРёСЂСѓРµРј endpoint.
        pass
    
    # РџРѕР»СѓС‡РёС‚СЊ ID РїРѕСЃР»РµРґРЅРµРіРѕ РїСЂРѕСЃРјРѕС‚СЂРµРЅРЅРѕРіРѕ С‚РёРєРµС‚Р° РёР· РїР°СЂР°РјРµС‚СЂРѕРІ
    try:
        last_ticket_id = int(request.GET.get('last_id', 0))
    except (TypeError, ValueError):
        last_ticket_id = 0
    
    # РџРѕР»СѓС‡РёС‚СЊ РєРѕР»РёС‡РµСЃС‚РІРѕ РЅРѕРІС‹С… С‚РёРєРµС‚РѕРІ
    tickets = Ticket.objects.filter(id__gt=last_ticket_id).order_by('-created_at')[:10]
    
    # Р¤РѕСЂРјР°С‚РёСЂРѕРІР°С‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ JSON
    tickets_data = []
    for ticket in tickets:
        status_name = ticket.status.name if ticket.status else 'UNKNOWN'
        priority_name = ticket.priority.name if ticket.priority else 'MEDIUM'
        
        # РћРїСЂРµРґРµР»РёС‚СЊ С†РІРµС‚Р° РґР»СЏ badge
        priority_colors = {
            'LOW': 'secondary',
            'MEDIUM': 'info',
            'HIGH': 'warning',
            'CRITICAL': 'danger'
        }
        status_colors = {
            'OPEN': 'primary',
            'IN_PROGRESS': 'info',
            'WAITING': 'warning',
            'RESOLVED': 'success',
            'CLOSED': 'secondary',
            'REOPENED': 'danger'
        }
        
        ticket_info = {
            'id': ticket.id,
            'title': ticket.title,
            'description': ticket.description[:100] + ('...' if len(ticket.description) > 100 else ''),
            'creator': ticket.creator.username,
            'priority': priority_name,
            'priority_color': priority_colors.get(priority_name, 'secondary'),
            'status': status_name,
            'status_color': status_colors.get(status_name, 'secondary'),
            'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            'room': ticket.room or '-',
            'is_staff': request.user.is_staff,
            'url': reverse('ticket_detail', kwargs={'ticket_id': ticket.id}),
        }
        tickets_data.append(ticket_info)
    
    return JsonResponse({
        'success': True,
        'tickets': tickets_data,
        'count': len(tickets_data)
    })


@require_approval
def get_new_comment_notifications(request):
    from django.core.cache import cache
    from django.http import JsonResponse

    try:
        if hasattr(request.user, 'profile') and not request.user.profile.notify_browser:
            return JsonResponse({'success': True, 'notifications': [], 'count': 0})
    except (OperationalError, ProgrammingError):
        pass

    cache_key = f'notification_comments_{request.user.id}'
    notifications = cache.get(cache_key, [])
    if notifications:
        cache.delete(cache_key)

    return JsonResponse({
        'success': True,
        'notifications': notifications,
        'count': len(notifications),
    })


@require_approval
def get_new_browser_notifications(request):
    from django.core.cache import cache
    from django.http import JsonResponse

    try:
        if hasattr(request.user, 'profile') and not request.user.profile.notify_browser:
            return JsonResponse({'success': True, 'notifications': [], 'count': 0})
    except (OperationalError, ProgrammingError):
        pass

    cache_key = f'notification_user_{request.user.id}'
    notifications = cache.get(cache_key, [])
    if notifications:
        cache.delete(cache_key)

    return JsonResponse({
        'success': True,
        'notifications': notifications,
        'count': len(notifications),
    })



