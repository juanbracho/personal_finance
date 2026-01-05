#!/usr/bin/env python3
"""
Financial Review Dashboard Generator
Generates an interactive HTML dashboard from personal_finance.db
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from jinja2 import Template

# Configuration
DB_PATH = Path(__file__).parent / "personal_finance.db"
TEMPLATE_PATH = Path(__file__).parent / "dashboard_template.html"
OUTPUT_PATH = Path(__file__).parent / "financial_review_2025.html"

# Owner colors
OWNER_COLORS = {
    "Cacas": "#3B82F6",
    "Cata": "#EC4899",
    "Suricata": "#10B981"
}


def connect_db():
    """Connect to SQLite database"""
    return sqlite3.connect(DB_PATH)


def load_transactions(conn):
    """Load all active transactions from database"""
    query = """
        SELECT
            id,
            date,
            description,
            amount,
            category,
            sub_category,
            owner,
            account_name,
            type,
            is_business
        FROM transactions
        WHERE is_active = 1
        ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn)
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')  # Convert non-numeric to NaN
    df = df.dropna(subset=['amount'])  # Drop rows with NaN amounts
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['year_month'] = df['date'].dt.to_period('M').astype(str)
    df['day_of_week'] = df['date'].dt.day_name()
    df['week_of_month'] = (df['date'].dt.day - 1) // 7 + 1

    return df


def calculate_statistics(df):
    """Calculate overall statistics"""
    stats = {
        "total_transactions": len(df),
        "total_spent": float(df['amount'].sum()),
        "avg_transaction": float(df['amount'].mean()),
        "median_transaction": float(df['amount'].median()),
        "std_deviation": float(df['amount'].std()),
        "date_range": {
            "start": df['date'].min().strftime('%Y-%m-%d'),
            "end": df['date'].max().strftime('%Y-%m-%d')
        },
        "unique_categories": df['category'].nunique(),
        "unique_owners": df['owner'].nunique()
    }
    return stats


def calculate_monthly_summary(df):
    """Calculate monthly aggregations"""
    monthly = df.groupby(['year_month', 'owner']).agg({
        'amount': 'sum',
        'id': 'count'
    }).reset_index()
    monthly.columns = ['year_month', 'owner', 'total_amount', 'transaction_count']

    # Convert to nested structure for frontend
    result = {}
    for _, row in monthly.iterrows():
        ym = row['year_month']
        if ym not in result:
            result[ym] = {}
        result[ym][row['owner']] = {
            'total_amount': float(row['total_amount']),
            'transaction_count': int(row['transaction_count'])
        }

    return result


def calculate_category_summary(df):
    """Calculate category aggregations"""
    category = df.groupby('category').agg({
        'amount': 'sum',
        'id': 'count'
    }).reset_index()
    category.columns = ['category', 'total_amount', 'transaction_count']
    category = category.sort_values('total_amount', ascending=False)

    return category.to_dict('records')


def calculate_owner_summary(df):
    """Calculate owner aggregations"""
    owner = df.groupby('owner').agg({
        'amount': 'sum',
        'id': 'count'
    }).reset_index()
    owner.columns = ['owner', 'total_amount', 'transaction_count']
    owner = owner.sort_values('total_amount', ascending=False)

    return owner.to_dict('records')


def calculate_subcategory_summary(df):
    """Calculate subcategory breakdown by category"""
    result = {}
    for category in df['category'].unique():
        cat_df = df[df['category'] == category]
        subcats = cat_df.groupby('sub_category').agg({
            'amount': 'sum',
            'id': 'count'
        }).reset_index()
        subcats.columns = ['sub_category', 'total_amount', 'transaction_count']
        subcats = subcats.sort_values('total_amount', ascending=False)
        result[category] = subcats.to_dict('records')

    return result


def identify_outliers(df):
    """Identify outlier transactions (>2 std deviations)"""
    mean = df['amount'].mean()
    std = df['amount'].std()
    threshold = mean + (2 * std)

    outliers = df[df['amount'] > threshold].copy()
    outliers['deviation'] = (outliers['amount'] - mean) / std
    outliers['date'] = outliers['date'].dt.strftime('%Y-%m-%d')  # Convert to string

    return outliers[['id', 'date', 'description', 'amount', 'category', 'owner', 'deviation']].to_dict('records')


def calculate_top_expenses(df, n=10):
    """Get top N expenses"""
    top = df.nlargest(n, 'amount')[['id', 'date', 'description', 'amount', 'category', 'owner']]
    top['date'] = top['date'].dt.strftime('%Y-%m-%d')
    return top.to_dict('records')


def calculate_heatmap_data(df):
    """Calculate spending heatmap (day of week vs week of month)"""
    heatmap = df.groupby(['day_of_week', 'week_of_month']).agg({
        'amount': 'sum'
    }).reset_index()

    # Create matrix structure
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weeks = [1, 2, 3, 4, 5]

    matrix = []
    for day in days:
        row = []
        for week in weeks:
            value = heatmap[(heatmap['day_of_week'] == day) &
                          (heatmap['week_of_month'] == week)]['amount'].sum()
            row.append(float(value) if value > 0 else 0)
        matrix.append(row)

    return {
        'days': days,
        'weeks': weeks,
        'values': matrix
    }


def prepare_transactions_list(df):
    """Prepare transactions for frontend table"""
    transactions = df.copy()
    transactions['date'] = transactions['date'].dt.strftime('%Y-%m-%d')
    transactions['amount'] = transactions['amount'].round(2)

    # Select and order columns
    columns = ['id', 'date', 'description', 'amount', 'category', 'sub_category',
               'owner', 'account_name', 'type', 'is_business']

    return transactions[columns].to_dict('records')


def generate_dashboard():
    """Main function to generate dashboard"""
    print("🚀 Starting dashboard generation...")

    # Connect to database
    print("📊 Connecting to database...")
    conn = connect_db()

    # Load data
    print("📥 Loading transactions...")
    df = load_transactions(conn)
    print(f"   Loaded {len(df)} transactions")

    # Calculate all data structures
    print("🔢 Calculating statistics...")
    statistics = calculate_statistics(df)

    print("📅 Processing monthly summary...")
    monthly_summary = calculate_monthly_summary(df)

    print("📂 Processing category summary...")
    category_summary = calculate_category_summary(df)

    print("👥 Processing owner summary...")
    owner_summary = calculate_owner_summary(df)

    print("🏷️  Processing subcategory breakdown...")
    subcategory_summary = calculate_subcategory_summary(df)

    print("⚠️  Identifying outliers...")
    outliers = identify_outliers(df)
    print(f"   Found {len(outliers)} outlier transactions")

    print("🔝 Calculating top expenses...")
    top_expenses = calculate_top_expenses(df, n=20)

    print("🔥 Generating heatmap data...")
    heatmap_data = calculate_heatmap_data(df)

    print("📋 Preparing transactions list...")
    transactions_list = prepare_transactions_list(df)

    # Prepare complete data object
    data = {
        "statistics": statistics,
        "monthly_summary": monthly_summary,
        "category_summary": category_summary,
        "owner_summary": owner_summary,
        "subcategory_summary": subcategory_summary,
        "outliers": outliers,
        "top_expenses": top_expenses,
        "heatmap_data": heatmap_data,
        "transactions": transactions_list,
        "owner_colors": OWNER_COLORS,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Load template
    print("📄 Loading HTML template...")
    with open(TEMPLATE_PATH, 'r') as f:
        template = Template(f.read())

    # Render template
    print("🎨 Rendering HTML...")
    html_output = template.render(data_json=json.dumps(data, indent=2))

    # Write output
    print(f"💾 Writing output to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w') as f:
        f.write(html_output)

    conn.close()

    print("✅ Dashboard generated successfully!")
    print(f"📍 Open: {OUTPUT_PATH}")

    return OUTPUT_PATH


if __name__ == "__main__":
    try:
        output_file = generate_dashboard()
        print(f"\n🎉 Done! Open the dashboard:\nopen '{output_file}'")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
