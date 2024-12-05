import pandas as pd
from app import app, db, User, Transaction  

# Ensure the code runs within the application context
with app.app_context():
    # Query all transactions and users from the database
    transactions = Transaction.query.all()
    users = User.query.all()  
    # Convert the user data to a list of dictionaries
    user_data = [
        {
            'User ID': user.id,
            'Name': user.name,
            'Email': user.email,
            # Add other user fields as needed
        }
        for user in users
    ]
    # Convert the transactions to a list of dictionaries
    transaction_data = [
        {
            'ID': transaction.id,
            'User ID': transaction.user_id,
            'Description': transaction.description,
            'Amount': transaction.amount,
            'Type': transaction.transaction_type,
            'Date': transaction.date.strftime('%Y-%m-%d'),
        }
        for transaction in transactions
    ]
    # Create DataFrames for both user and transaction data
    df_transactions = pd.DataFrame(transaction_data)
    df_users = pd.DataFrame(user_data)
    # separate sheets in the same Excel file
    file_path = 'all_transactions.xlsx'
    with pd.ExcelWriter(file_path) as writer:
        df_transactions.to_excel(writer, sheet_name='Transactions', index=False)
        df_users.to_excel(writer, sheet_name='Users', index=False)

    print(f"Data exported to {file_path}")