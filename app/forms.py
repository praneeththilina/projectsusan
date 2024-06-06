from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, DateTimeField, SelectField, HiddenField,\
            RadioField, IntegerField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from .models import BotFuelPackage
import pytz


# Generate list of timezones
timezone_choices = [(tz, tz) for tz in pytz.all_timezones]

class TradeForm(FlaskForm):
    pair = StringField('Pair', validators=[DataRequired()])
    side = StringField('Side', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    submit = SubmitField('Execute Trade')

class APIForm(FlaskForm):
    api_key = StringField('API Key', validators=[DataRequired()])
    api_secret = StringField('API Secret', validators=[DataRequired()])
    submit = SubmitField('Bind with Binance')

class PurchaseFuelForm(FlaskForm):
    package = SelectField('Fuel Package', choices=[], validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[('Binance Pay', 'Binance Pay'), ('Crypto Address', 'Crypto Address')], validators=[DataRequired()])
    pay_id = StringField('Pay ID')
    submit = SubmitField('Purchase Fuel')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.package.choices = [(pkg.id, pkg.name) for pkg in BotFuelPackage.query.all()]

class SettingsForm(FlaskForm):
    take_profit_percentage = FloatField('Take Profit Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)],render_kw={"class": "percentage-input", "type": "number", "step": "any"})
    stop_loss_percentage = FloatField('Stop Loss Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)],render_kw={"class": "percentage-input", "type": "number", "step": "any"})
    order_type = SelectField('Order Type', choices=[('market', 'Market'), ('limit', 'Limit')],validators=[DataRequired()], render_kw={"class": "dropdown"})
    leverage = FloatField('Leverage', validators=[DataRequired(), NumberRange(min=0, max=100)])
    concorrent = IntegerField('Concurrent Trades Limit', validators=[DataRequired(), NumberRange(min=2, max=50)])
    defined_long_margine_per_trade = FloatField('Defined Margine Per Trade', validators=[DataRequired()])
    defined_short_margine_per_trade = FloatField('Defined Margine Per Trade', validators=[DataRequired()])
    tg_chatid = StringField('Telegram Chat ID', validators=[DataRequired()])
    marginMode = SelectField('Margin mode', choices=[('cross', 'CROSS MODE'), ('isolated', 'ISOLATED MODE')], validators=[DataRequired()], default='cross')
    timezone = SelectField('Timezone', choices=timezone_choices, validators=[DataRequired()], default='Asia/Colombo')

    submit = SubmitField('Save')

    # def validate_stop_loss_percentage(self, stop_loss_percentage):
    #     # Extract necessary parameters
    #     leverage = self.leverage.data
    #     if leverage:
    #         maint_margin_percent = 2.5
    #         entry_price = 500
    #         # Calculate liquidation price
    #         liquidation_price = entry_price * (1 - 1 / leverage + maint_margin_percent / 100 / leverage)

    #         # Calculate maximum stop loss ratio
    #         max_stop_loss_ratio = (entry_price - liquidation_price) / entry_price
    #         if stop_loss_percentage.data > ((max_stop_loss_ratio) * 100):  # Convert to percentage
    #             raise ValidationError(f"Stop loss percentage exceeds the allowable limit based on leverage {leverage}x. Max SL Ratio: {'{:.2f}'.format(max_stop_loss_ratio*100)}%")


class MarkAsReadForm(FlaskForm):
    notification_id = HiddenField('Notification ID')
    submit = SubmitField('Mark as Read')


class AvatarSelectionForm(FlaskForm):
    avatar = RadioField('Select Avatar', choices=[
            ('avatar1.svg', 'avatar1.svg'),
            ('avatar2.svg', 'avatar2.svg'),
            ('avatar3.svg', 'avatar3.svg'),
            ('avatar4.svg', 'avatar4.svg'),
            ('avatar5.svg', 'avatar5.svg')
            ], validators=[DataRequired()])
    submit = SubmitField('Save Avatar')