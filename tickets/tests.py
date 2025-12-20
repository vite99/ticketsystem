from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Ticket, Comment, Priority, Status, Tag


class TicketModelTest(TestCase):
    """Тесты для модели Ticket"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.priority = Priority.objects.create(name='medium', color='#ffc107')
        self.status = Status.objects.create(name='open', color='#0066cc')
        
    def test_ticket_creation(self):
        """Тест создания тикета"""
        ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            creator=self.user,
            priority=self.priority,
            status=self.status
        )
        self.assertEqual(ticket.title, 'Test Ticket')
        self.assertEqual(ticket.creator, self.user)
        self.assertTrue(ticket.id)
        
    def test_ticket_string_representation(self):
        """Тест строкового представления"""
        ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test',
            creator=self.user,
            priority=self.priority,
            status=self.status
        )
        self.assertEqual(str(ticket), f"#{ticket.id} - Test Ticket")


class CommentModelTest(TestCase):
    """Тесты для модели Comment"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.priority = Priority.objects.create(name='low', color='#17a2b8')
        self.status = Status.objects.create(name='open', color='#0066cc')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test',
            creator=self.user,
            priority=self.priority,
            status=self.status
        )
        
    def test_comment_creation(self):
        """Тест создания комментария"""
        comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.user,
            content='Test comment'
        )
        self.assertEqual(comment.content, 'Test comment')
        self.assertEqual(comment.ticket, self.ticket)
        self.assertFalse(comment.is_internal)


class TicketViewTest(TestCase):
    """Тесты для представлений"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.priority = Priority.objects.create(name='medium', color='#ffc107')
        self.status = Status.objects.create(name='open', color='#0066cc')
        
    def test_ticket_list_redirect_not_authenticated(self):
        """Тест редиректа на логин для неавторизованных"""
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 302)


class TagModelTest(TestCase):
    """Тесты для модели Tag"""
    
    def test_tag_creation(self):
        """Тест создания тега"""
        tag = Tag.objects.create(
            name='Bug',
            description='Bug report',
            color='#dc3545'
        )
        self.assertEqual(tag.name, 'Bug')
        self.assertEqual(str(tag), 'Bug')
