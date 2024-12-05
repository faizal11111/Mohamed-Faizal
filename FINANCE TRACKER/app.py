from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from sqlalchemy import func, extract
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Relationship with the Transaction model
    transactions = db.relationship('Transaction', backref='user', lazy=True)

# Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  

    def __repr__(self):
        return f"<Transaction {self.description}>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your email and password.', 'danger')

    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', name=current_user.name, transactions=transactions)

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        transaction_type = request.form['transaction_type']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        new_transaction = Transaction(
            user_id=current_user.id,
            description=description,
            amount=amount,
            date=date,
            transaction_type=transaction_type
        )

        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_transaction.html')

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id == current_user.id:
        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted successfully!', 'success')
    else:
        flash('You cannot delete this transaction.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/export_to_excel')
@login_required
def export_to_excel():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    transaction_data = [
        {
            'ID': transaction.id,
            'Description': transaction.description,
            'Amount': transaction.amount,
            'Type': transaction.transaction_type,
            'Date': transaction.date.strftime('%Y-%m-%d')
        }
        for transaction in transactions
    ]

    df = pd.DataFrame(transaction_data)
    file_path = 'transactions.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        if User.query.filter(User.email == email, User.id != current_user.id).first():
            flash('Email is already in use by another account.', 'danger')
            return redirect(url_for('settings'))

        current_user.name = name
        current_user.email = email
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', name=current_user.name, email=current_user.email)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('change_password'))

        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('change_password.html')

# Function to calculate total income for a given month and year
def calculate_total_income(user_id, month, year):
    return db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id ==user_id, 
   
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year,
        Transaction.transaction_type == 'Income'
    ).scalar() or 0  # Return 0 if no income

# Function to calculate total expenses for a given month and year
def calculate_total_expense(user_id, month, year):
    return db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, 
        
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year,
         Transaction.transaction_type == 'Expense'
    ).scalar() or 0  

# Route for displaying total income and expenses
@app.route('/total_amount', methods=['GET', 'POST'])
@login_required
def total_amount():
    selected_month = request.form.get('month', type=int, default=datetime.now().month)
    selected_year = request.form.get('year', type=int, default=datetime.now().year)

    # Calculate total income and expenses for the selected month and year
    total_income = calculate_total_income(current_user.id, selected_month, selected_year)
    total_expense = calculate_total_expense(current_user.id, selected_month, selected_year)

    # Calculate net total (income - expenses)
    net_total = total_income - total_expense
    current_year = datetime.now().year

    return render_template('total_amount.html', 
                           total_income=total_income,
                           total_expense=total_expense,
                           net_total=net_total,
                           selected_month=selected_month,
                           selected_year=selected_year,
                           current_year=current_year)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
