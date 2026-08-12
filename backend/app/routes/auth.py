import hmac
import hashlib
import time
from flask import Blueprint, request, jsonify, current_app
from app.models.user import User
from app.extensions import db
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

def generate_token(username: str) -> str:
    secret = current_app.config.get('SECRET_KEY', 'trademerc-secret-key-2026')
    timestamp = str(int(time.time()))
    msg = f"{username}:{timestamp}".encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
    return f"{username}:{timestamp}:{sig}"

def verify_token(token: str) -> bool:
    if not token:
        return False
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return False
        username, timestamp, sig = parts
        secret = current_app.config.get('SECRET_KEY', 'trademerc-secret-key-2026')
        msg = f"{username}:{timestamp}".encode('utf-8')
        expected_sig = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
        
        # Token valid for 30 days
        if int(time.time()) - int(timestamp) > 30 * 86400:
            return False

        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    pin = str(data.get('pin', '')).strip()

    if not username or not pin:
        return jsonify({"success": False, "error": "Nombre de usuario y PIN son obligatorios."}), 400

    # Guarantee user elkinpabon exists with PIN 2002123 if not in DB
    user = User.query.filter_by(username=username).first()
    if not user and username.lower() == 'elkinpabon':
        user = User(
            username='elkinpabon',
            pin_hash=generate_password_hash('2002123')
        )
        db.session.add(user)
        db.session.commit()

    if not user or not user.check_pin(pin):
        return jsonify({"success": False, "error": "Usuario o PIN incorrectos."}), 401

    token = generate_token(user.username)
    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_dict(),
        "message": "Autenticación exitosa."
    }), 200

@auth_bp.route('/auth/verify', methods=['GET', 'POST'])
def verify():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip() if auth_header else request.args.get('token', '')

    if verify_token(token):
        return jsonify({"valid": True}), 200
    return jsonify({"valid": False, "error": "Token inválido o expirado"}), 401
