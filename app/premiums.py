from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user
from app.models import db, User, PremiumPackage, PendingPremium
import datetime
from flask_security.decorators import permissions_accepted, auth_required, roles_accepted

premium_bp = Blueprint('premium_bp', __name__)

@premium_bp.route('/buy_premium', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def buy_premium():
    if any(not p.approved for p in current_user.pending_premiums):
        return jsonify({"error": "You already have a pending premium request"}), 400

    data = request.json
    if data:
        package_id = data.get('package_id')

    package = PremiumPackage.query.get(package_id)
    if not package:
        return jsonify({"error": "Invalid package"}), 400

    now = datetime.datetime.now()
    if current_user.expire_date:
        start_date = current_user.expire_date + datetime.timedelta(seconds=1)
    else:
        start_date = now

    end_date = start_date + datetime.timedelta(days=package.duration_days)

    pending_premium = PendingPremium(user_id=current_user.id, package_id=package.id, start_date=start_date, end_date=end_date) # type: ignore
    db.session.add(pending_premium)
    db.session.commit()

    return jsonify({"message": f"Requested {package.name} package. Awaiting admin approval."}), 200

@premium_bp.route('/packages', methods=['GET'])
@auth_required('token', 'session')
@roles_accepted('admin', 'user')
def get_packages():
    packages = PremiumPackage.query.all()
    return render_template('premiums/buy_premium.html', packages=packages)

@premium_bp.route('/admin/premium_requests', methods=['GET'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def premium_requests():
    pending_premiums = PendingPremium.query.filter_by(approved=False).all()
    return render_template('admin/premium_requests.html', pending_premiums=pending_premiums)

@premium_bp.route('/admin/approve_premium/<int:pending_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def approve_premium(pending_id):
    pending_premium = PendingPremium.query.get(pending_id)
    if not pending_premium:
        return jsonify({"error": "Pending premium not found"}), 404

    pending_premium.approved = True
    user = pending_premium.user
    if not user.premium:
        user.premium = True
        user.expire_date = pending_premium.end_date

    if user.premium:
        user.expire_date = pending_premium.end_date

    db.session.commit()

    return jsonify({"message": "Premium request approved"}), 200

@premium_bp.route('/admin/reject_premium/<int:pending_id>', methods=['POST'])
@auth_required('token', 'session')
@roles_accepted('admin')
@permissions_accepted("admin-write")
def reject_premium(pending_id):
    pending_premium = PendingPremium.query.get(pending_id)
    if not pending_premium:
        return jsonify({"error": "Pending premium not found"}), 404

    db.session.delete(pending_premium)
    db.session.commit()

    return jsonify({"message": "Premium request rejected"}), 200


def register_blueprint(app):
    app.register_blueprint(premium_bp)
