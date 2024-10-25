from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Dish, Order, OrderItem
from forms import LoginForm, AddressForm
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@app.route('/menu')
def menu():
    categories = Category.query.all()
    return render_template('menu.html', categories=categories)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(phone=form.phone.data).first()
        if not user:
            user = User(phone=form.phone.data)
            db.session.add(user)
            db.session.commit()
        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('menu'))
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('menu'))


@app.route('/add_to_cart/<int:dish_id>')
@login_required
def add_to_cart(dish_id):
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append(dish_id)
    session['cart'] = cart
    flash('Блюдо добавлено в корзину')
    return redirect(url_for('menu'))


@app.route('/remove_from_cart/<int:dish_id>')
@login_required
def remove_from_cart(dish_id):
    if 'cart' in session:
        cart = session['cart']
        if dish_id in cart:
            cart.remove(dish_id)
            session['cart'] = cart
            flash('Блюдо удалено из корзины')
    return redirect(url_for('cart'))


@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    form = AddressForm()
    if 'cart' not in session:
        session['cart'] = []

    cart_items = []
    total = 0
    for dish_id in session['cart']:
        dish = Dish.query.get(dish_id)
        if dish:
            cart_items.append(dish)
            total += dish.price

    if form.validate_on_submit():
        order = Order(user=current_user, total=total)
        for dish in cart_items:
            order_item = OrderItem(order=order, dish_id=dish.id, quantity=1, price=dish.price)
            db.session.add(order_item)
        current_user.address = form.address.data
        db.session.add(order)
        db.session.commit()
        session['cart'] = []
        flash('Заказ успешно оформлен!')
        return redirect(url_for('order_status', order_id=order.id))

    return render_template('cart.html', items=cart_items, total=total, form=form)


@app.route('/order/<int:order_id>')
@login_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Доступ запрещен')
        return redirect(url_for('menu'))

    # Получаем все заказы пользователя
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.asc()).all()
    # Находим порядковый номер текущего заказа
    order_number = next((i for i, o in enumerate(user_orders, 1) if o.id == order_id), None)

    return render_template('order_status.html', order=order, order_number=order_number)


@app.route('/order/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Доступ запрещен')
        return redirect(url_for('menu'))
    order.delivered = True
    order.delivery_time = datetime.utcnow()
    db.session.commit()
    flash('Доставка подтверждена')
    return redirect(url_for('order_status', order_id=order.id))


@app.route('/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    numbered_orders = []
    for i, order in enumerate(orders, 1): # начинаем нумерацию с 1
        numbered_orders.append((i, order))
    return render_template('order_history.html', numbered_orders=numbered_orders)


def init_db():
    # Проверяем, есть ли уже категории в базе
    if Category.query.first() is None:
        # Создаем категории
        categories_data = {
            'Закуски': [
                ('Салат Цезарь', 'caesar.jpg', 'Свежий салат с курицей и соусом Цезарь', 350),
                ('Брускетта', 'bruschetta.jpg', 'Хрустящий багет с томатами и базиликом', 250),
                ('Суп дня', 'soup.jpg', 'Суп из сезонных овощей', 200)
            ],
            'Основные блюда': [
                ('Стейк', 'steak.jpg', 'Сочный стейк из мраморной говядины', 800),
                ('Паста Карбонара', 'carbonara.jpg', 'Классическая итальянская паста', 450),
                ('Пицца Маргарита', 'pizza.jpg', 'Традиционная пицца с томатами и моцареллой', 500)
            ],
            'Десерты': [
                ('Тирамису', 'tiramisu.jpg', 'Итальянский десерт с маскарпоне', 300),
                ('Чизкейк', 'cheesecake.jpg', 'Нежный чизкейк Нью-Йорк', 350),
                ('Мороженое', 'icecream.jpg', 'Ассорти из трех видов мороженого', 200)
            ],
            'Напитки': [
                ('Кофе', 'coffee.jpg', 'Свежесваренный кофе', 150),
                ('Чай', 'tea.jpg', 'Чай с чабрецом', 100),
                ('Лимонад', 'lemonade.jpg', 'Домашний лимонад', 180)
            ]
        }

        # Добавляем категории и блюда в базу данных
        for category_name, dishes in categories_data.items():
            category = Category(name=category_name)
            db.session.add(category)
            db.session.flush()  # Чтобы получить id категории

            for dish_data in dishes:
                name, image, description, price = dish_data
                dish = Dish(
                    name=name,
                    image=image,
                    description=description,
                    price=price,
                    category_id=category.id
                )
                db.session.add(dish)

        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()
    app.run(debug=True)
