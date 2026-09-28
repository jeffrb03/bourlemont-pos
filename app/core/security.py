import hashlib
import hmac
import os
import json
import base64
import time
from typing import Optional, Dict, Any
from app.core.config import settings

def _hash_with_salt(value: str, salt: Optional[str] = None) -> str:
    """Genera hash seguro usando PBKDF2-HMAC-SHA256 con sal."""
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        value.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def _verify_with_salt(value: str, stored_hash: str) -> bool:
    """Verifica valor en texto plano contra el hash con sal."""
    try:
        salt, hashed = stored_hash.split('$', 1)
        expected = hashlib.pbkdf2_hmac(
            'sha256',
            value.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return hmac.compare_digest(hashed, expected)
    except Exception:
        return False

def hash_pin(pin: str) -> str:
    return _hash_with_salt(str(pin))

def verify_pin(plain_pin: str, stored_hash: str) -> bool:
    return _verify_with_salt(str(plain_pin), stored_hash)

def hash_password(password: str) -> str:
    return _hash_with_salt(str(password))

def verify_password(plain_password: str, stored_hash: str) -> bool:
    return _verify_with_salt(str(plain_password), stored_hash)

def create_access_token(data: Dict[str, Any], expires_in_seconds: int = 86400) -> str:
    """Crea token de sesión firmado para la SPA Local-First."""
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')
    
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        b64_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{b64_payload}.{signature}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida y decodifica un token de sesión."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        b64_payload, signature = parts
        
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            b64_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Padding
        padded = b64_payload + '=' * (-len(b64_payload) % 4)
        raw_json = base64.urlsafe_b64decode(padded.encode('utf-8')).decode('utf-8')
        payload = json.loads(raw_json)
        
        if payload.get("exp", 0) < int(time.time()):
            return None
            
        return payload
    except Exception:
        return None
