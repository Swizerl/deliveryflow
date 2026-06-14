from django.core.management.base import BaseCommand

from products.models import Product


MENU = [
    # ── Роллы и суши ──
    {'category': 'rolls', 'name': 'Филадельфия классик', 'description': 'Лосось, сливочный сыр, огурец, нори, рис', 'price': 520, 'weight': '280 г', 'stock': 30},
    {'category': 'rolls', 'name': 'Калифорния с крабом', 'description': 'Снежный краб, авокадо, огурец, тобико, рис', 'price': 480, 'weight': '260 г', 'stock': 25},
    {'category': 'rolls', 'name': 'Дракон ролл', 'description': 'Угорь, авокадо, огурец, унаги соус, кунжут', 'price': 590, 'weight': '300 г', 'stock': 20},
    {'category': 'rolls', 'name': 'Спайси лосось', 'description': 'Лосось, спайси соус, зелёный лук, кунжут', 'price': 450, 'weight': '250 г', 'stock': 35},
    {'category': 'rolls', 'name': 'Темпура с креветкой', 'description': 'Тигровая креветка в темпуре, авокадо, сливочный сыр', 'price': 540, 'weight': '290 г', 'stock': 20},
    {'category': 'rolls', 'name': 'Запечённый ролл с лососем', 'description': 'Лосось, сливочный сыр, соус спайси, запечённый', 'price': 510, 'weight': '280 г', 'stock': 25},
    {'category': 'rolls', 'name': 'Сет «Для двоих»', 'description': '32 шт: Филадельфия, Калифорния, Дракон, Спайси лосось', 'price': 1490, 'weight': '950 г', 'stock': 10},

    # ── Горячие блюда ──
    {'category': 'hot', 'name': 'Том ям с креветками', 'description': 'Тайский суп с кокосовым молоком, креветки, грибы шиитаке, лемонграсс', 'price': 490, 'weight': '350 мл', 'stock': 20},
    {'category': 'hot', 'name': 'Вок с курицей и овощами', 'description': 'Рисовая лапша, куриное филе, болгарский перец, соус терияки', 'price': 420, 'weight': '350 г', 'stock': 30},
    {'category': 'hot', 'name': 'Вок с морепродуктами', 'description': 'Удон, креветки, кальмар, мидии, овощи, соус устричный', 'price': 520, 'weight': '380 г', 'stock': 20},
    {'category': 'hot', 'name': 'Рис с курицей терияки', 'description': 'Жареный рис, куриное филе, овощи, соус терияки, кунжут', 'price': 380, 'weight': '320 г', 'stock': 35},
    {'category': 'hot', 'name': 'Лосось на гриле', 'description': 'Стейк лосося, овощи гриль, лимонный соус', 'price': 650, 'weight': '250 г', 'stock': 15},
    {'category': 'hot', 'name': 'Утка по-пекински', 'description': 'Утиная грудка, блинчики, хойсин соус, огурец, лук', 'price': 720, 'weight': '400 г', 'stock': 10},

    # ── Супы ──
    {'category': 'soups', 'name': 'Мисо суп', 'description': 'Бульон даси, тофу, водоросли вакамэ, зелёный лук', 'price': 220, 'weight': '250 мл', 'stock': 40},
    {'category': 'soups', 'name': 'Рамен со свининой', 'description': 'Наваристый бульон тонкоцу, чашу, яйцо аджитама, нори, лук', 'price': 460, 'weight': '450 мл', 'stock': 20},
    {'category': 'soups', 'name': 'Фо бо', 'description': 'Вьетнамский суп, говяжий бульон, рисовая лапша, ростки сои, базилик', 'price': 430, 'weight': '400 мл', 'stock': 20},

    # ── Салаты ──
    {'category': 'salads', 'name': 'Салат с лососем и авокадо', 'description': 'Микс салатов, лосось, авокадо, черри, соус понзу', 'price': 490, 'weight': '220 г', 'stock': 25},
    {'category': 'salads', 'name': 'Цезарь с креветками', 'description': 'Романо, тигровые креветки, пармезан, гренки, соус цезарь', 'price': 450, 'weight': '240 г', 'stock': 25},
    {'category': 'salads', 'name': 'Тёплый салат с курицей', 'description': 'Куриное филе, микс листьев, помидоры, огурцы, кунжутная заправка', 'price': 380, 'weight': '230 г', 'stock': 30},

    # ── Закуски ──
    {'category': 'appetizers', 'name': 'Гёдза с курицей (6 шт)', 'description': 'Японские пельмени с куриным фаршем, соус понзу', 'price': 340, 'weight': '180 г', 'stock': 30},
    {'category': 'appetizers', 'name': 'Эдамаме', 'description': 'Бобы эдамаме с морской солью', 'price': 250, 'weight': '150 г', 'stock': 40},
    {'category': 'appetizers', 'name': 'Спринг-роллы с овощами (4 шт)', 'description': 'Рисовая бумага, авокадо, морковь, огурец, соус sweet chili', 'price': 320, 'weight': '160 г', 'stock': 30},
    {'category': 'appetizers', 'name': 'Креветки темпура (5 шт)', 'description': 'Тигровые креветки в хрустящем кляре, соус спайси', 'price': 490, 'weight': '200 г', 'stock': 20},
    {'category': 'appetizers', 'name': 'Татаки из тунца', 'description': 'Обжаренный тунец, соус понзу, кунжут, микрозелень', 'price': 560, 'weight': '150 г', 'stock': 15},

    # ── Десерты ──
    {'category': 'desserts', 'name': 'Моти (3 шт)', 'description': 'Рисовые пирожные: манго, клубника, зелёный чай', 'price': 350, 'weight': '120 г', 'stock': 25},
    {'category': 'desserts', 'name': 'Чизкейк матча', 'description': 'Нежный чизкейк с японским зелёным чаем', 'price': 320, 'weight': '130 г', 'stock': 20},
    {'category': 'desserts', 'name': 'Тирамису юдзу', 'description': 'Классический тирамису с цитрусом юдзу', 'price': 340, 'weight': '140 г', 'stock': 20},
    {'category': 'desserts', 'name': 'Мороженое темпура', 'description': 'Ванильное мороженое в хрустящем кляре, шоколадный соус', 'price': 290, 'weight': '100 г', 'stock': 25},

    # ── Напитки ──
    {'category': 'drinks', 'name': 'Зелёный чай сенча', 'description': 'Классический японский зелёный чай', 'price': 190, 'weight': '400 мл', 'stock': 50},
    {'category': 'drinks', 'name': 'Матча латте', 'description': 'Японский зелёный чай с молоком', 'price': 280, 'weight': '350 мл', 'stock': 40},
    {'category': 'drinks', 'name': 'Лимонад юдзу', 'description': 'Домашний лимонад с японским цитрусом юдзу и мятой', 'price': 250, 'weight': '400 мл', 'stock': 40},
    {'category': 'drinks', 'name': 'Кока-Кола', 'description': '', 'price': 150, 'weight': '330 мл', 'stock': 100},
    {'category': 'drinks', 'name': 'Вода негазированная', 'description': '', 'price': 100, 'weight': '500 мл', 'stock': 100},
    {'category': 'drinks', 'name': 'Сок апельсиновый', 'description': 'Свежевыжатый', 'price': 280, 'weight': '300 мл', 'stock': 40},
    {'category': 'drinks', 'name': 'Саке (графин)', 'description': 'Тёплое или холодное саке, подача в традиционном графине', 'price': 490, 'weight': '300 мл', 'stock': 15},
]


class Command(BaseCommand):
    help = 'Заполнить каталог товаров меню ресторана (удаляет старые товары)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Не удалять существующие товары, только добавить новые',
        )

    def handle(self, *args, **options):
        if not options['keep']:
            deleted, _ = Product.objects.all().delete()
            if deleted:
                self.stdout.write(f'Удалено старых товаров: {deleted}')

        created = 0
        for item in MENU:
            _, is_new = Product.objects.get_or_create(
                name=item['name'],
                defaults={
                    'category': item['category'],
                    'description': item['description'],
                    'price': item['price'],
                    'weight': item['weight'],
                    'stock': item['stock'],
                },
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Добавлено товаров: {created}, всего в каталоге: {Product.objects.count()}'
        ))

        # Показываем сводку по категориям.
        for code, label in Product.CATEGORY_CHOICES:
            count = Product.objects.filter(category=code).count()
            if count:
                self.stdout.write(f'  {label}: {count}')
