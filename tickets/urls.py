from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('login/', views.TicketLoginView.as_view(), name='login'),
    path('logout/', views.TicketLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Тикеты
    path('', views.ticket_list, name='ticket_list'),
    path('archive/', views.ticket_archive, name='ticket_archive'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('<int:ticket_id>/edit/', views.ticket_edit, name='ticket_edit'),
    path('<int:ticket_id>/confirm-resolution/', views.confirm_ticket_resolution, name='confirm_ticket_resolution'),
    path('<int:ticket_id>/reopen-by-creator/', views.reopen_ticket_by_creator, name='reopen_ticket_by_creator'),
    path('<int:ticket_id>/cancel-by-creator/', views.cancel_ticket_by_creator, name='cancel_ticket_by_creator'),
    path('<int:ticket_id>/assign-to-me/', views.assign_ticket_to_me, name='assign_ticket_to_me'),
    path('<int:ticket_id>/unassign/', views.unassign_ticket, name='unassign_ticket'),
    path('api/new-tickets/', views.get_new_tickets, name='get_new_tickets'),
    path('api/new-comments/', views.get_new_comment_notifications, name='get_new_comment_notifications'),
    path('api/browser-notifications/', views.get_new_browser_notifications, name='get_new_browser_notifications'),
    path('api/workstations-by-room/', views.workstations_by_room, name='workstations_by_room'),
    
    # Комментарии
    path('<int:ticket_id>/comment/', views.add_comment, name='add_comment'),
    
    # Личный кабинет
    path('dashboard/', views.my_dashboard, name='dashboard'),
    path('statistics/', views.ticket_statistics, name='ticket_statistics'),
    path('settings/notifications/', views.notification_settings, name='notification_settings'),
    
    # Управление одобрением пользователей (только для администраторов)
    path('users/approval/', views.user_approval_list, name='user_approval_list'),
    path('users/<int:user_id>/approve/', views.approve_user, name='approve_user'),
    path('users/<int:user_id>/reject/', views.reject_user, name='reject_user'),
    path('users/<int:user_id>/revoke/', views.revoke_approval, name='revoke_approval'),
    path('workstations/', views.workstation_list, name='workstation_list'),
    path('workstations/create/', views.workstation_create, name='workstation_create'),
    path('workstations/<int:workstation_id>/edit/', views.workstation_edit, name='workstation_edit'),
    path('workstations/<int:workstation_id>/delete/', views.workstation_delete, name='workstation_delete'),
]
