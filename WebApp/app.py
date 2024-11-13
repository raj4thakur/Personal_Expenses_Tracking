from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)

# Configuration
DATABASE_CONFIG = {
    'host': "localhost",
    'user': "root",
    'password': "rjtkpr",
    'database': "PersonalExpense"
}

# Database connection function with error handling
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

# Fetch expenses from the database
def fetch_expenses():
    conn = get_db_connection()
    if not conn:
        return []

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC;")
    expenses = cursor.fetchall()
    cursor.close()
    conn.close()
    return expenses

# Route to display the homepage with the expense form and list
@app.route('/')
def index():
    expenses = fetch_expenses()
    return render_template('index.html', expenses=expenses)

# Route to add a new expense
@app.route('/add', methods=['POST'])
def add_expense():
    date = request.form.get('date')
    category = request.form.get('category')
    description = request.form.get('description')
    amount = request.form.get('amount')
    
    # Get custom category if "Others" is selected
    if category == "Others":
        category = request.form.get('custom-category')
    
    if not all([date, category, description, amount]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (%s, %s, %s, %s)",
            (date, category, description, amount)
        )
        conn.commit()
    except Error as e:
        print(f"Error inserting expense: {e}")
        return jsonify({'error': 'Failed to add expense'}), 500
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))

# Route to delete an expense by ID
@app.route('/delete/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
    except Error as e:
        print(f"Error deleting expense: {e}")
        return jsonify({'error': 'Failed to delete expense'}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({'success': True}), 200

# Route to fetch all expenses as JSON for AJAX requests
@app.route('/expenses', methods=['GET'])
def get_expenses():
    expenses = fetch_expenses()
    expenses_list = [{
        'id': expense[0],
        'date': expense[1],
        'category': expense[2],
        'description': expense[3],
        'amount': expense[4]
    } for expense in expenses]

    return jsonify(expenses_list)

# Route to display monthly report
@app.route('/monthly_report')
def monthly_report():
    # Get the current year and month
    current_year = 2024
    current_month = 11
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total expenses for the month
    cursor.execute("""
        SELECT SUM(amount) 
        FROM expenses 
        WHERE YEAR(date) = %s AND MONTH(date) = %s
    """, (current_year, current_month))
    total_expense = cursor.fetchone()[0] or 0

    # Category breakdown for the month
    cursor.execute("""
        SELECT category, SUM(amount) 
        FROM expenses 
        WHERE YEAR(date) = %s AND MONTH(date) = %s
        GROUP BY category
    """, (current_year, current_month))
    category_breakdown = cursor.fetchall()

    # Calculate percentage per category
    category_percentages = []
    for category in category_breakdown:
        category_percentages.append({
            'category': category[0],
            'amount': category[1],
            'percentage': (category[1] / total_expense) * 100 if total_expense > 0 else 0
        })

    # Top spending category
    top_spending_category = max(category_percentages, key=lambda x: x['amount'], default=None)

    # Number of expenses for the month
    cursor.execute("""
        SELECT COUNT(*) 
        FROM expenses 
        WHERE YEAR(date) = %s AND MONTH(date) = %s
    """, (current_year, current_month))
    expense_count = cursor.fetchone()[0]

    conn.close()

    # Prepare the detailed report
    report = {
        'total_expense': total_expense,
        'category_breakdown': category_percentages,
        'top_spending_category': top_spending_category,
        'expense_count': expense_count,
        'month': current_month,
        'year': current_year
    }
    return jsonify(report)


@app.route('/set_income', methods=['POST'])
def set_income():
    user_id = 1  # Assuming user ID is 1 for simplicity
    income_amount = request.form['income_amount']
    current_month = datetime.now().month
    current_year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Save income to the database
    query = "INSERT INTO income_sources (user_id, amount, month, year) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (user_id, income_amount, current_month, current_year))  # Use current month/year
    conn.commit()

    return redirect(url_for('financial_summary'))

@app.route('/set_budget', methods=['POST'])
def set_budget():
    user_id = 1
    budget_amount = request.form['budget_amount']
    current_month = datetime.now().month
    current_year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Save the budget
    query = "INSERT INTO budgets (user_id, budget_amount, month, year) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (user_id, budget_amount, current_month, current_year))
    conn.commit()

    return redirect(url_for('financial_summary'))




@app.route('/add_bill', methods=['POST'])
def add_bill():
    user_id = 1
    bill_category = request.form['bill_category']
    bill_amount = request.form['bill_amount']
    conn = get_db_connection()
    cursor = conn.cursor()
    # Save the bill to the database
    query = "INSERT INTO expenses (user_id, category, amount, month, year) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(query, (user_id, bill_category, bill_amount, 11, 2024))  # November 2024
    conn.commit()

    return redirect(url_for('financial_summary'))

@app.route('/financial_summary', methods=['GET'])
def financial_summary():
    user_id = 1  # Example user; replace with session or authenticated user ID as needed
    
    # Get current month and year or use specified parameters
    month = request.args.get('month', default=datetime.now().month, type=int)
    year = request.args.get('year', default=datetime.now().year, type=int)

    try:
        # Establishing database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch total income for the month and year
        cursor.execute("""
            SELECT SUM(amount) 
            FROM income_sources 
            WHERE user_id = %s AND month = %s AND year = %s
        """, (user_id, month, year))
        total_income = cursor.fetchone()[0] or 0

        # Fetch total expenses for the month and year (Correcting this query)
        cursor.execute("""
            SELECT SUM(amount) 
            FROM expenses 
            WHERE user_id = %s 
            AND EXTRACT(MONTH FROM date) = %s 
            AND EXTRACT(YEAR FROM date) = %s
        """, (user_id, month, year))
        total_expenses = cursor.fetchone()[0] or 0

        # Fetch budget for the month and year
        cursor.execute("""
            SELECT budget_amount 
            FROM budgets 
            WHERE user_id = %s AND month = %s AND year = %s
        """, (user_id, month, year))
        budget = cursor.fetchone()[0] or 0
        
        # Fetch all bills (expense items) for the month and year (Correcting the query)
        cursor.execute("""
            SELECT category, amount 
            FROM expenses 
            WHERE user_id = %s
            AND EXTRACT(MONTH FROM date) = %s
            AND EXTRACT(YEAR FROM date) = %s
        """, (user_id, month, year))
        bills = cursor.fetchall()

        # Calculate remaining savings
        remaining_savings = total_income - total_expenses

        # Prepare data for the frontend
        financial_data = {
            'total_income': total_income,
            'budget': budget,
            'total_expenses': total_expenses,
            'remaining_savings': remaining_savings,
            'bills': [{'category': bill[0], 'amount': bill[1]} for bill in bills]
        }

        # Close the connection after fetching data
        cursor.close()
        conn.close()

        # Return the data as a JSON response
        return jsonify(financial_data)

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "There was an issue processing your request"}), 500



# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
