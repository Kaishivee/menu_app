from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    phone = StringField('Номер телефона', validators=[DataRequired()])
    submit = SubmitField('Войти')


class AddressForm(FlaskForm):
    address = StringField('Адрес доставки', validators=[DataRequired()])
    submit = SubmitField('Подтвердить заказ')
