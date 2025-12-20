from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Ticket, Comment, Status, Priority, Tag
from .forms import TicketForm, CommentForm
from django.urls import reverse_lazy


class TicketLoginView(LoginView):
    """Представление для входа"""
    template_name = 'tickets/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('ticket_list')


class TicketLogoutView(LogoutView):
    """Представление для выхода"""
    next_page = 'ticket_list'


@login_required(login_url='login')
def ticket_list(request):
    """Список всех тикетов с фильтрацией"""
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
    search_query = request.GET.get('q')
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Фильтрация по назначению (мои тикеты)
    if request.GET.get('my_tickets'):
        tickets = tickets.filter(assigned_to=request.user)
    
    # Пагинация
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'tickets': page_obj.object_list,
        'statuses': Status.objects.all(),
        'priorities': Priority.objects.all(),
        'search_query': search_query,
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
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            ticket.save()
            form.save_m2m()  # Сохранить M2M отношения (теги)
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketForm()
    
    return render(request, 'tickets/ticket_form.html', {'form': form, 'title': 'Создать тикет'})


@login_required(login_url='login')
def ticket_edit(request, ticket_id):
    """Редактирование тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверка прав доступа
    if request.user != ticket.creator and request.user != ticket.assigned_to and not request.user.is_staff:
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketForm(instance=ticket)
    
    return render(request, 'tickets/ticket_form.html', {'form': form, 'ticket': ticket, 'title': 'Редактировать тикет'})


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
