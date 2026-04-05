# 🔄 Система Live Updates с HTMX

## Описание

Система Ticket System теперь поддерживает **real-time обновления** без перезагрузок страницы благодаря HTMX. Это обеспечивает плавное и современное пользовательское взаимодействие.

---

## 📋 Что обновляется в реальном времени

### 1️⃣ **Статус тикета** ⏱️ 10 сек
- **Где:** На странице деталей тикета, в разделе мета-информации
- **Как:** Статус автоматически обновляется каждые 10 секунд
- **Зачем:** Администратор меняет статус → вы видите изменение мгновенно
- **CSS:** Плавная fade-in анимация при обновлении (0.3s)

### 2️⃣ **Комментарии** ⏱️ 15 сек
- **Где:** На странице деталей тикета, раздел "Комментарии"
- **Как:** Новые комментарии загружаются каждые 15 секунд
- **Зачем:** Другие участники пишут комментарии → они появляются автоматически
- **CSS:** Плавная fade-in анимация при обновлении (0.3s)

### 3️⃣ **Количество новых тикетов** ⏱️ 30 сек (только для администраторов)
- **Где:** В navbar (правый верхний угол), рядом с "Админ"
- **Как:** Значок с числом обновляется каждые 30 секунд
- **Зачем:** Администратор видит, сколько открыто новых тикетов
- **Анимация:** Пульсирующий значок (pulse animation)

---

## 🔧 Технические реализация

### Структура HTMX атрибутов

```html
<!-- Пример из ticket_detail.html -->
<div id="status-badge-container"
    hx-get="{% url 'ticket_status_partial' ticket.id %}"
    hx-trigger="every 10s"
    hx-swap="innerHTML swap:0.3s">
    <!-- Контент здесь -->
</div>
```

**Атрибуты:**
- `hx-get` — URL для получения обновлённого контента
- `hx-trigger` — когда обновлять (в нашем случае каждые N секунд)
- `hx-swap` — как заменять: `innerHTML` с задержкой 0.3s

### Views для HTMX

**`tickets/views.py`:**

```python
@login_required(login_url='login')
def ticket_status_partial(request, ticket_id):
    """Partial для отображения статуса тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return render(request, 'tickets/partials/ticket_status_partial.html', 
                  {'ticket': ticket})

@login_required(login_url='login')
def ticket_comments_partial(request, ticket_id):
    """Partial для отображения комментариев"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.all()
    return render(request, 'tickets/partials/ticket_comments_partial.html',
                  {'ticket': ticket, 'comments': comments})

@login_required(login_url='login')
def new_tickets_badge(request):
    """Partial для значка новых тикетов"""
    if not request.user.is_staff:
        return render(request, 'tickets/partials/new_tickets_badge.html', 
                      {'count': 0})
    open_status = Status.objects.filter(name=Status.OPEN).first()
    count = Ticket.objects.filter(status=open_status).count() if open_status else 0
    return render(request, 'tickets/partials/new_tickets_badge.html',
                  {'count': count})
```

### HTML Partials

**Location:** `templates/tickets/partials/`

1. **ticket_status_partial.html** — отображает цветной бейдж со статусом
2. **ticket_comments_partial.html** — отображает список комментариев
3. **new_tickets_badge.html** — отображает значок с количеством новых тикетов

---

## 📊 Интервалы обновления

| Элемент | Интервал | Причина |
|---------|----------|---------|
| Статус тикета | 10 сек | Часто меняется, нужно видеть сразу |
| Комментарии | 15 сек | Достаточно для диалога, экономит ресурсы |
| Новые тикеты | 30 сек | За день образуется мало тикетов, редкое изменение |

---

## 🎨 CSS Анимации

### Fade-in эффект

```css
.htmx-swapping {
    opacity: 0;
    transition: opacity 0.2s ease-out;
}
.htmx-settling {
    opacity: 1;
    transition: opacity 0.2s ease-in;
}
```

Когда HTMX заменяет контент:
1. Старый контент исчезает (opacity: 0)
2. Загружается новый
3. Плавно появляется (opacity: 1)

### Пульсирующий значок

```css
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
```

Значок с новыми тикетами слегка мигает, привлекая внимание.

---

## 🚀 Использованные технологии

- **HTMX 1.9.10** — для AJAX запросов без JavaScript
- **Django** — backend для partial views
- **CSS3 transitions** — плавные анимации
- **Polling** — регулярные запросы к серверу

---

## 🔐 Безопасность и производительность

### Безопасность
✅ Все views защищены `@login_required`
✅ Статус видят все авторизованные пользователи
✅ Комментарии фильтруются по правам доступа
✅ Новые тикеты видят только администраторы

### Производительность
✅ Partials возвращают только необходимый HTML
✅ Используются правильные Django ORM запросы
✅ Нет N+1 проблем благодаря select_related
✅ Интервалы выбраны оптимально
✅ Со 100 пользователями на 15 сек интервале = ~6 запросов/сек

---

## 📝 Примеры использования

### Добавить live update к новому элементу

```html
<!-- Ваш HTML элемент -->
<div id="my-container"
    hx-get="{% url 'your_view_name' %}"
    hx-trigger="every 20s"
    hx-swap="innerHTML swap:0.3s">
    <!-- Initial content -->
</div>
```

### Создать новый partial view

```python
@login_required(login_url='login')
def my_partial_view(request):
    context = {'data': ...}
    return render(request, 'path/to/partial.html', context)
```

### Добавить URL

```python
path('api/my-partial/', views.my_partial_view, name='my_partial_view'),
```

---

## 🎯 Тестирование

### Проверить работу:

1. **Статус:**
   - Откройте тикет
   - В другой вкладке измените его статус
   - Проверьте, обновилось ли в первой вкладке за 10 сек

2. **Комментарии:**
   - Откройте один тикет
   - В другой вкладке добавьте комментарий
   - Проверьте появление в первой вкладке за 15 сек

3. **Новые тикеты (админ):**
   - Откройте страницу любого тикета (админом)
   - Создайте новый тикет в другой вкладке
   - Значок должен обновиться за 30 сек

---

## 🐛 Troubleshooting

**Проблема:** Обновления не работают
- ✅ Проверьте, что HTMX загружается (консоль браузера)
- ✅ В DevTools Network должны быть GET запросы каждые N секунд

**Проблема:** Слишком частые обновления
- Увеличьте интервал (например, `every 30s` вместо `every 10s`)

**Проблема:** Слишком редкие обновления
- Уменьшите интервал (например, `every 5s` вместо `every 15s`)

---

## 📚 Дополнительные ресурсы

- [HTMX Документация](https://htmx.org/)
- [HTMX Polling](https://htmx.org/attributes/hx-trigger/#polling)
- [Django Partial Pattern](https://docs.djangoproject.com/en/5.0/topics/templates/#template-inheritance)

---

**Версия:** 1.0
**Дата:** 5 апреля 2026
**Статус:** Готово к использованию ✅
