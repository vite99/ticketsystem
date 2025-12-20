from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('login/', views.TicketLoginView.as_view(), name='login'),
    path('logout/', views.TicketLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Тикеты
    path('', views.ticket_list, name='ticket_list'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('<int:ticket_id>/edit/', views.ticket_edit, name='ticket_edit'),
    
    # Комментарии
    path('<int:ticket_id>/comment/', views.add_comment, name='add_comment'),
    
    # Личный кабинет
    path('dashboard/', views.my_dashboard, name='dashboard'),
    
    # Управление одобрением пользователей (только для администраторов)
    path('users/approval/', views.user_approval_list, name='user_approval_list'),
    path('users/<int:user_id>/approve/', views.approve_user, name='approve_user'),
    path('users/<int:user_id>/reject/', views.reject_user, name='reject_user'),
    path('users/<int:user_id>/revoke/', views.revoke_approval, name='revoke_approval'),
]
