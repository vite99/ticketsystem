from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('login/', views.TicketLoginView.as_view(), name='login'),
    path('logout/', views.TicketLogoutView.as_view(), name='logout'),
    
    # Тикеты
    path('', views.ticket_list, name='ticket_list'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('<int:ticket_id>/edit/', views.ticket_edit, name='ticket_edit'),
    
    # Комментарии
    path('<int:ticket_id>/comment/', views.add_comment, name='add_comment'),
    
    # Личный кабинет
    path('dashboard/', views.my_dashboard, name='dashboard'),
]
