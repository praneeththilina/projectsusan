from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, DateTimeField, SelectField, HiddenField,\
            RadioField
from wtforms.validators import DataRequired, NumberRange


# class TradeForm(FlaskForm):
#     pair = StringField('Pair', validators=[DataRequired()])
#     side = SelectField('Side', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
#     price = FloatField('Price')
#     amount = FloatField('Amount', validators=[DataRequired()])
#     submit = SubmitField('Execute Trade')

class TradeForm(FlaskForm):
    pair = StringField('Pair', validators=[DataRequired()])
    side = StringField('Side', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    submit = SubmitField('Execute Trade')

class APIForm(FlaskForm):
    api_key = StringField('API Key', validators=[DataRequired()])
    api_secret = StringField('API Secret', validators=[DataRequired()])
    submit = SubmitField('Save API Keys')

class RequestPremiumPlanForm(FlaskForm):
    plan = SelectField('Premium Plan', choices=[])
    submit = SubmitField('Request Plan')

    def __init__(self, plans, *args, **kwargs):
        super(RequestPremiumPlanForm, self).__init__(*args, **kwargs)
        self.plan.choices = [(plan.id, plan.name) for plan in plans]

# class SettingsForm(FlaskForm):
#     take_profit_percentage = FloatField('Take Profit Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
#     stop_loss_percentage = FloatField('Stop Loss Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
#     future_wallet_margin_usage_ratio = FloatField('Future Wallet Margin Usage Ratio', validators=[DataRequired(), NumberRange(min=0, max=100)])
#     submit = SubmitField('Save Settings')


class SettingsForm(FlaskForm):
    take_profit_percentage = FloatField(
        'Take Profit Percentage',
        validators=[DataRequired(), NumberRange(min=0, max=100)],
        render_kw={"class": "percentage-input"}
    )
    stop_loss_percentage = FloatField(
        'Stop Loss Percentage',
        validators=[DataRequired(), NumberRange(min=0, max=100)],
        render_kw={"class": "percentage-input"}
    )
    future_wallet_margin_usage_ratio = FloatField(
        'Future Wallet Margin Usage Ratio',
        validators=[DataRequired(), NumberRange(min=0, max=100)],
        render_kw={"class": "percentage-input"}
    )
    tg_chatid = StringField('Telegram Chat ID', validators=[DataRequired()])
    submit = SubmitField('Save Settings')

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