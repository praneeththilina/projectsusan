from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user
from flask_security.decorators import auth_required
from app.models import db, WebhookURL, User
import uuid

custom_webhook_bp = Blueprint('custom_webhook_bp', __name__)

@custom_webhook_bp.route('/generate_webhook', methods=['GET', 'POST'])
@auth_required('token', 'session') #implementation need for role based
def generate_webhook():
    if request.method == 'GET':
        return render_template('settings.html')

    if not current_user.premium:
        return jsonify({"error": "Only Premium members can generate a webhook URL"}), 403

    webhook = WebhookURL.query.filter_by(user_id=current_user.id).first()

    if not webhook:
        webhook = WebhookURL(user_id=current_user.id, url=str(uuid.uuid4())) # type: ignore
        db.session.add(webhook)
    else:
        webhook.url = str(uuid.uuid4())
        db.session.add(webhook)

    db.session.commit()
    return jsonify({"webhook_url": webhook.url}), 200

def register_blueprint(app):
    app.register_blueprint(custom_webhook_bp)
