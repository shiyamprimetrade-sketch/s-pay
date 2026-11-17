"""Offline S-Pay demonstration ledger. No money is moved."""
import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from datetime import datetime, timezone

CENT = Decimal('0.01')

def cents(value):
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError('Enter a valid USD amount')
    if not amount.is_finite() or amount <= 0 or amount > Decimal('1000000'):
        raise ValueError('Amount must be between $0.01 and $1,000,000')
    if amount.quantize(CENT, rounding=ROUND_HALF_UP) != amount:
        raise ValueError('Use at most two decimal places')
    return int(amount * 100)

def breakdown(value):
    base = cents(value)
    fee = (base * 2 + 50) // 100
    return base, fee, base + fee

def dollars(value):
    return f'${value / 100:,.2f}'

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        return con

    def init(self):
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                  role TEXT NOT NULL CHECK(role IN ('poster','billionaire')),
                  payout_reference TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS bills (
                  id INTEGER PRIMARY KEY, poster_id INTEGER NOT NULL REFERENCES users(id),
                  title TEXT NOT NULL, description TEXT NOT NULL,
                  base_cents INTEGER NOT NULL CHECK(base_cents>0),
                  fee_cents INTEGER NOT NULL CHECK(fee_cents>=0),
                  total_cents INTEGER NOT NULL,
                  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','demo_funded')),
                  created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS transactions (
                  id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL UNIQUE REFERENCES bills(id),
                  billionaire_id INTEGER NOT NULL REFERENCES users(id),
                  base_cents INTEGER NOT NULL, fee_cents INTEGER NOT NULL,
                  settlement_status TEXT NOT NULL DEFAULT 'demo_only',
                  timestamp TEXT NOT NULL);
            ''')

    def register(self, username, role):
        username = username.strip()
        if not (3 <= len(username) <= 40) or not all(c.isalnum() or c in '_-' for c in username):
            raise ValueError('Username: 3–40 letters, numbers, _ or -')
        if role not in ('poster', 'billionaire'):
            raise ValueError('Invalid role')
        with self.connect() as db:
            try:
                cur = db.execute('INSERT INTO users(username,role,created_at) VALUES(?,?,?)', (username, role, now()))
            except sqlite3.IntegrityError:
                raise ValueError('Username already exists')
            return cur.lastrowid

    def login(self, username):
        # Demo profile switching only; no real authentication.
        with self.connect() as db:
            return db.execute('SELECT * FROM users WHERE username=?', (username.strip(),)).fetchone()

    def create_bill(self, poster_id, title, description, amount):
        base, fee, total = breakdown(amount)
        title, description = title.strip(), description.strip()
        if not (3 <= len(title) <= 100) or len(description) > 1000:
            raise ValueError('Title must be 3–100 characters; description at most 1000')
        with self.connect() as db:
            user = db.execute('SELECT role FROM users WHERE id=?', (poster_id,)).fetchone()
            if not user or user['role'] != 'poster':
                raise ValueError('Poster account required')
            cur = db.execute('INSERT INTO bills(poster_id,title,description,base_cents,fee_cents,total_cents,created_at) VALUES(?,?,?,?,?,?,?)', (poster_id,title,description,base,fee,total,now()))
            return cur.lastrowid

    def bills(self, poster_id=None, pending_only=False):
        sql = 'SELECT bills.*, users.username AS poster FROM bills JOIN users ON users.id=bills.poster_id WHERE 1=1'
        args = []
        if poster_id is not None:
            sql += ' AND poster_id=?'; args.append(poster_id)
        if pending_only:
            sql += " AND status='pending'"
        sql += ' ORDER BY bills.id DESC'
        with self.connect() as db:
            return db.execute(sql,args).fetchall()

    def demo_fund(self, billionaire_id, bill_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT role FROM users WHERE id=?', (billionaire_id,)).fetchone()
            if not user or user['role'] != 'billionaire':
                raise ValueError('Supporter account required')
            bill = db.execute('SELECT * FROM bills WHERE id=?', (bill_id,)).fetchone()
            if not bill or bill['status'] != 'pending':
                raise ValueError('Bill already selected or missing')
            db.execute("UPDATE bills SET status='demo_funded' WHERE id=?", (bill_id,))
            db.execute('INSERT INTO transactions(bill_id,billionaire_id,base_cents,fee_cents,settlement_status,timestamp) VALUES(?,?,?,?,?,?)', (bill_id,billionaire_id,bill['base_cents'],bill['fee_cents'],'demo_only',now()))
            return bill['base_cents'], bill['fee_cents']

    def summary(self):
        with self.connect() as db:
            row = db.execute('SELECT COUNT(*) AS n, COALESCE(SUM(base_cents),0) AS base, COALESCE(SUM(fee_cents),0) AS fees FROM transactions').fetchone()
            return dict(row)
