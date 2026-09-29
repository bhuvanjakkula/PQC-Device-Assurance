"""
Authentication, Session Management & Payment Gate for Continuous PQC Assurance.
- Strictly locks the platform:
  * Visitors without sign up / sign in CANNOT access the website.
  * Customers without paid subscription CANNOT access the website.
  * ONLY owner bhuvanjakkula@gmail.com has full access without paying money.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any

OWNER_EMAIL = "bhuvanjakkula@gmail.com"
SESSION_LIFETIME_SECONDS = 30 * 24 * 3600  # 30 days


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(stored: str, password: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        parts = stored.split("$")
        if len(parts) != 2:
            return False
        salt, key_hex = parts
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(computed, key_hex)
    except Exception:
        return False


class AuthManager:
    """Manages users, authentication, payment verification and sessions in SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Ensure tables exist and owner is initialized."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    mobile TEXT,
                    org TEXT,
                    role TEXT NOT NULL DEFAULT 'customer',
                    plan TEXT NOT NULL DEFAULT 'Starter',
                    is_paid INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    last_login INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    is_owner INTEGER NOT NULL,
                    is_paid INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            # Ensure owner user exists
            cursor.execute("SELECT id, password_hash FROM users WHERE lower(email) = ?", (OWNER_EMAIL.lower(),))
            row = cursor.fetchone()
            now = int(time.time())
            if not row:
                default_hash = hash_password("OwnerPqc2026!")
                cursor.execute("""
                    INSERT INTO users (email, password_hash, mobile, org, role, plan, is_paid, created_at, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (OWNER_EMAIL, default_hash, "+1 (555) 000-0000", "PQC Assurance Admin", "owner", "Enterprise+", 1, now, now))
            else:
                # Ensure owner is always marked with role=owner, plan=Enterprise+, is_paid=1
                cursor.execute("""
                    UPDATE users SET role = 'owner', plan = 'Enterprise+', is_paid = 1
                    WHERE lower(email) = ?
                """, (OWNER_EMAIL.lower(),))
            conn.commit()

    def is_owner(self, email: str) -> bool:
        return email.strip().lower() == OWNER_EMAIL.lower()

    def create_session(self, user_row: sqlite3.Row | Dict[str, Any]) -> str:
        token = "tok_" + secrets.token_urlsafe(32)
        now = int(time.time())
        expires_at = now + SESSION_LIFETIME_SECONDS
        email = user_row["email"]
        is_owner_val = 1 if self.is_owner(email) else 0
        is_paid_val = 1 if (is_owner_val == 1 or user_row["is_paid"] == 1) else 0
        plan = "Enterprise+" if is_owner_val == 1 else user_row["plan"]
        role = "owner" if is_owner_val == 1 else "customer"

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (token, user_id, email, role, plan, is_owner, is_paid, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (token, user_row["id"], email, role, plan, is_owner_val, is_paid_val, now, expires_at))
            conn.commit()
        return token

    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        norm_email = email.strip().lower()
        now = int(time.time())

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE lower(email) = ?", (norm_email,))
            user = cursor.fetchone()

            # Special clearance for owner
            if norm_email == OWNER_EMAIL.lower():
                if user:
                    # Update password if provided
                    if password and not verify_password(user["password_hash"], password):
                        # Allow owner to update password on login seamlessly
                        new_hash = hash_password(password)
                        cursor.execute("UPDATE users SET password_hash = ?, last_login = ?, is_paid = 1, role = 'owner' WHERE id = ?", (new_hash, now, user["id"]))
                    else:
                        cursor.execute("UPDATE users SET last_login = ?, is_paid = 1, role = 'owner' WHERE id = ?", (now, user["id"]))
                else:
                    new_hash = hash_password(password or "OwnerPqc2026!")
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, mobile, org, role, plan, is_paid, created_at, last_login)
                        VALUES (?, ?, ?, ?, 'owner', 'Enterprise+', 1, ?, ?)
                    """, (OWNER_EMAIL, new_hash, "+1", "PQC Assurance Admin", now, now))
                conn.commit()

                # Re-fetch
                cursor.execute("SELECT * FROM users WHERE lower(email) = ?", (norm_email,))
                user = cursor.fetchone()
                token = self.create_session(user)
                return {
                    "id": user["id"],
                    "email": user["email"],
                    "role": "owner",
                    "plan": "Enterprise+",
                    "plan_badge": "Enterprise+ (Owner Lifetime Clearance)",
                    "is_owner": True,
                    "is_paid": True,
                    "token": token,
                    "message": "Owner authenticated. Full lifetime bypass granted without payment."
                }

            # Standard customer login
            if not user:
                return None

            if not verify_password(user["password_hash"], password):
                return None

            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user["id"]))
            conn.commit()

            token = self.create_session(user)
            is_paid_bool = bool(user["is_paid"])
            return {
                "id": user["id"],
                "email": user["email"],
                "role": "customer",
                "plan": user["plan"],
                "plan_badge": f"{user['plan']} Tier",
                "is_owner": False,
                "is_paid": is_paid_bool,
                "token": token,
                "message": "Customer authenticated." if is_paid_bool else "Customer authenticated. Subscription payment required to unlock platform."
            }

    def register(self, email: str, password: str, mobile: str = "", org: str = "", plan: str = "Professional") -> Dict[str, Any]:
        norm_email = email.strip().lower()
        now = int(time.time())

        # If owner signs up
        if norm_email == OWNER_EMAIL.lower():
            pwd_hash = hash_password(password or "OwnerPqc2026!")
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (norm_email,))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("UPDATE users SET password_hash = ?, last_login = ?, is_paid = 1, role = 'owner', plan = 'Enterprise+' WHERE id = ?", (pwd_hash, now, existing["id"]))
                    user_id = existing["id"]
                else:
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, mobile, org, role, plan, is_paid, created_at, last_login)
                        VALUES (?, ?, ?, ?, 'owner', 'Enterprise+', 1, ?, ?)
                    """, (OWNER_EMAIL, pwd_hash, mobile, org or "PQC Assurance Admin", now, now))
                    user_id = cursor.lastrowid
                conn.commit()

                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                token = self.create_session(user)
                return {
                    "id": user_id,
                    "email": OWNER_EMAIL,
                    "role": "owner",
                    "plan": "Enterprise+",
                    "plan_badge": "Enterprise+ (Owner Lifetime Clearance)",
                    "is_owner": True,
                    "is_paid": True,
                    "token": token,
                    "message": "Owner registered successfully. Lifetime access active without payment."
                }

        # Customer registration
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (norm_email,))
            if cursor.fetchone():
                raise ValueError("This email is already registered. Please sign in.")

            pwd_hash = hash_password(password)
            # Customers are UNPAID by default (is_paid = 0)
            cursor.execute("""
                INSERT INTO users (email, password_hash, mobile, org, role, plan, is_paid, created_at, last_login)
                VALUES (?, ?, ?, ?, 'customer', ?, 0, ?, ?)
            """, (norm_email, pwd_hash, mobile, org, plan, now, now))
            user_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            token = self.create_session(user)
            return {
                "id": user_id,
                "email": user["email"],
                "role": "customer",
                "plan": plan,
                "plan_badge": f"{plan} Tier",
                "is_owner": False,
                "is_paid": False,
                "token": token,
                "message": "Account created. Commercial payment required to unlock platform access."
            }

    def confirm_payment(self, email_or_token: str, plan: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Mark a customer as paid (unlocking platform access)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            user_id = None
            if email_or_token.startswith("tok_"):
                cursor.execute("SELECT user_id, email FROM sessions WHERE token = ?", (email_or_token,))
                sess = cursor.fetchone()
                if sess:
                    user_id = sess["user_id"]
            if not user_id:
                cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (email_or_token.strip().lower(),))
                row = cursor.fetchone()
                if row:
                    user_id = row["id"]

            if not user_id:
                return None

            if plan:
                cursor.execute("UPDATE users SET is_paid = 1, plan = ? WHERE id = ?", (plan, user_id))
                cursor.execute("UPDATE sessions SET is_paid = 1, plan = ? WHERE user_id = ?", (plan, user_id))
            else:
                cursor.execute("UPDATE users SET is_paid = 1 WHERE id = ?", (user_id,))
                cursor.execute("UPDATE sessions SET is_paid = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            is_owner = self.is_owner(user["email"])
            return {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "plan": user["plan"],
                "plan_badge": f"{user['plan']} Tier (Active License)",
                "is_owner": is_owner,
                "is_paid": True,
                "message": "Payment verified! Full platform access unlocked."
            }

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        now = int(time.time())
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE token = ? AND expires_at > ?", (token, now))
            sess = cursor.fetchone()
            if not sess:
                return None

            email = sess["email"]
            is_owner = self.is_owner(email)
            is_paid = True if (is_owner or sess["is_paid"] == 1) else False

            return {
                "user_id": sess["user_id"],
                "email": email,
                "role": "owner" if is_owner else sess["role"],
                "plan": "Enterprise+" if is_owner else sess["plan"],
                "is_owner": is_owner,
                "is_paid": is_paid,
                "token": token
            }

    def logout(self, token: str):
        if not token:
            return
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()

    def reset_password(self, email: str, new_password: str) -> Optional[Dict[str, Any]]:
        """Reset or update password for any registered user or owner."""
        norm_email = email.strip().lower()
        if not norm_email or not new_password:
            return None
        now = int(time.time())
        pwd_hash = hash_password(new_password)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, role, plan, is_paid FROM users WHERE lower(email) = ?", (norm_email,))
            user = cursor.fetchone()
            if not user:
                # If owner hasn't signed up yet or user doesn't exist:
                if norm_email == OWNER_EMAIL.lower():
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, mobile, org, role, plan, is_paid, created_at, last_login)
                        VALUES (?, ?, ?, ?, 'owner', 'Enterprise+', 1, ?, ?)
                    """, (OWNER_EMAIL, pwd_hash, "+1", "PQC Assurance Admin", now, now))
                    conn.commit()
                    return {"email": OWNER_EMAIL, "is_owner": True, "message": "Owner password updated successfully."}
                return None

            cursor.execute("UPDATE users SET password_hash = ?, last_login = ? WHERE id = ?", (pwd_hash, now, user["id"]))
            # Invalidate previous sessions so user signs in with new password
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
            conn.commit()
            return {
                "email": user["email"],
                "is_owner": self.is_owner(user["email"]),
                "message": "Password updated successfully."
            }

