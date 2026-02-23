from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.db import models
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Ticket, Comment, Status, Priority, Tag, UserProfile
from .forms import TicketForm, TicketFormUser, CommentForm, RegistrationForm
from django.urls import reverse_lazy


class TicketLoginView(LoginView):
    """Представление для входа"""
    template_name = 'tickets/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('ticket_list')


class TicketLogoutView(LogoutView):
    """Представление для выхода"""
    next_page = 'ticket_list'


def register_view(request):
    """Регистрация нового пользователя"""
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
    """Проверка прав администратора"""
    return user.is_staff or user.is_superuser


def is_approved(user):
    """Проверка, одобрен ли пользователь"""
    if user.is_staff or user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.is_approved


def require_approval(view_func):
    """Декоратор для проверки одобрения пользователя"""
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        if not is_approved(request.user):
            return render(request, 'tickets/pending_approval.html')
        return view_func(request, *args, **kwargs)
    return wrapped_view


@require_approval
def ticket_list(request):
    """Список всех тикетов с фильтрацией"""
    from django.core.cache import cache
    
    # Получаем уведомления для админов
    if request.user.is_staff:
        cache_key = f'notification_admin_{request.user.id}'
        notifications = cache.get(cache_key, [])
        if notifications:
            # Показываем уведомления
            for notif in notifications:
                if notif['type'] == 'warning':
                    messages.warning(request, notif['message'])
                else:
                    messages.info(request, notif['message'])
            # Очищаем уведомления
            cache.delete(cache_key)
    
    tickets = Ticket.objects.all()
    
    # Фильтрация по статусу
    status_id = request.GET.get('status')
    if status_id:
        tickets = tickets.filter(status_id=status_id)
    
    # Фильтрация по приоритету
    priority_id = request.GET.get('priority')
    if priority_id:
        tickets = tickets.filter(priority_id=priority_id)
    
    # Поиск по названию или описанию
    search_query = (request.GET.get('q') or '').strip()
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

        terms = [term for term in search_query.split() if term]
        for term in terms:
            term_filter = (
                Q(title__icontains=term) |
                Q(description__icontains=term) |
                Q(creator__username__icontains=term) |
                Q(creator__first_name__icontains=term) |
                Q(creator__last_name__icontains=term) |
                Q(assigned_to__username__icontains=term) |
                Q(assigned_to__first_name__icontains=term) |
                Q(assigned_to__last_name__icontains=term) |
                Q(tags__name__icontains=term) |
                Q(workstation__room__icontains=term) |
                Q(workstation__number__icontains=term) |
                Q(workstation__location__icontains=term)
            )
            combined_filter &= term_filter

        tickets = tickets.filter(combined_filter).distinct()
    
    # Фильтрация по назначению (мои тикеты)
    if request.GET.get('my_tickets'):
        tickets = tickets.filter(assigned_to=request.user)
    
    # Пагинация
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'page_obj': page_obj,
        'tickets': page_obj.object_list,
        'statuses': Status.objects.all(),
        'priorities': Priority.objects.all(),
        'search_query': search_query,
        'query_string': query_params.urlencode(),
    }
    return render(request, 'tickets/ticket_list.html', context)


@login_required(login_url='login')
def ticket_detail(request, ticket_id):
    """Детальный просмотр тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.all()
    attachments = ticket.attachments.all()
    
    # Проверка прав доступа
    can_edit = request.user == ticket.creator or request.user == ticket.assigned_to or request.user.is_staff
    
    context = {
        'ticket': ticket,
        'comments': comments,
        'attachments': attachments,
        'can_edit': can_edit,
    }
    return render(request, 'tickets/ticket_detail.html', context)


@login_required(login_url='login')
def ticket_create(request):
    """Создание нового тикета"""
    # Выбираем форму в зависимости от роли пользователя
    form_class = TicketForm if request.user.is_staff else TicketFormUser
    
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            
            # Для обычных пользователей устанавливаем статус "Открыт"
            if not request.user.is_staff:
                from django.db.models import Q
                ticket.status = Status.objects.filter(name='open').first() or Status.objects.first()
            
            ticket.save()
            if hasattr(form, 'save_m2m'):
                form.save_m2m()  # Сохранить M2M отношения (теги) если они есть
            
            # Отправляем сообщение об успешном создании
            messages.success(request, f'✅ Тикет #{ticket.id} успешно создан!')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = form_class()
    
    return render(request, 'tickets/ticket_form.html', {'form': form, 'title': 'Создать тикет'})


@login_required(login_url='login')
def ticket_edit(request, ticket_id):
    """Редактирование тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверка прав доступа
    if request.user != ticket.creator and request.user != ticket.assigned_to and not request.user.is_staff:
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    # Выбираем форму в зависимости от роли пользователя
    form_class = TicketForm if request.user.is_staff else TicketFormUser
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()
            
            # Отправляем сообщение об успешном обновлении
            messages.success(request, f'✅ Тикет #{ticket.id} успешно обновлён!')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = form_class(instance=ticket)
    
    return render(request, 'tickets/ticket_form.html', {'form': form, 'ticket': ticket, 'title': 'Редактировать тикет'})


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_POST
def assign_ticket_to_me(request, ticket_id):
    """Назначить тикет текущему администратору."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.assigned_to = request.user
    ticket.save(update_fields=['assigned_to', 'updated_at'])
    messages.success(request, f'Тикет #{ticket.id} назначен на вас.')
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required(login_url='login')
def add_comment(request, ticket_id):
    """Добавление комментария к тикету"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = CommentForm()
    
    return render(request, 'tickets/comment_form.html', {'form': form, 'ticket': ticket})


@login_required(login_url='login')
def my_dashboard(request):
    """Личный кабинет пользователя"""
    created_tickets = Ticket.objects.filter(creator=request.user)
    assigned_tickets = Ticket.objects.filter(assigned_to=request.user)
    
    # Статистика
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


@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Административный кабинет с общей статистикой"""
    # Общая статистика
    total_users = User.objects.count()
    approved_users = UserProfile.objects.filter(is_approved=True).count()
    pending_users = UserProfile.objects.filter(is_approved=False).exclude(user__is_staff=True).count()
    
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status__name__in=['open', 'in_progress', 'reopened']).count()
    resolved_tickets = Ticket.objects.filter(status__name='resolved').count()
    closed_tickets = Ticket.objects.filter(status__name='closed').count()
    
    # Тикеты по приоритету
    critical_tickets = Ticket.objects.filter(priority__name='critical').count()
    high_tickets = Ticket.objects.filter(priority__name='high').count()
    
    # Последние тикеты
    recent_tickets = Ticket.objects.all()[:10]
    
    # Статистика по статусам
    status_stats = Status.objects.all().annotate(
        count=models.Count('ticket')
    ).order_by('-count')
    
    # Самые активные пользователи
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
    """Список пользователей, ожидающих одобрения (для администраторов)"""
    # Получаем всех пользователей и обеспечиваем наличие профиля
    all_users = User.objects.all()
    
    # Убедимся, что у каждого пользователя есть профиль
    for user in all_users:
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
    
    # Теперь фильтруем по статусу одобрения (исключая штат)
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
    """Одобрить пользователя"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.profile.is_approved = True
        user.profile.approved_by = request.user
        user.profile.approved_at = timezone.now()
        user.profile.save()
        
        messages.success(request, f'Пользователь {user.username} успешно одобрен.')
        return redirect('user_approval_list')
    
    context = {'user': user}
    return render(request, 'tickets/approve_user.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
def reject_user(request, user_id):
    """Отклонить пользователя"""
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
    """Отозвать одобрение пользователя"""
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


@require_approval
def get_new_tickets(request):
    """API endpoint для получения новых тикетов (для AJAX)"""
    from django.http import JsonResponse
    
    # Получить ID последнего просмотренного тикета из параметров
    last_ticket_id = request.GET.get('last_id', 0)
    
    # Получить количество новых тикетов
    tickets = Ticket.objects.filter(id__gt=last_ticket_id).order_by('-created_at')[:10]
    
    # Форматировать данные для JSON
    tickets_data = []
    for ticket in tickets:
        status_name = ticket.status.name if ticket.status else 'UNKNOWN'
        priority_name = ticket.priority.name if ticket.priority else 'MEDIUM'
        
        # Определить цвета для badge
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
            'is_staff': request.user.is_staff
        }
        tickets_data.append(ticket_info)
    
    return JsonResponse({
        'success': True,
        'tickets': tickets_data,
        'count': len(tickets_data)
    })
