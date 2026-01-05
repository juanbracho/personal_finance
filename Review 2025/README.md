# Financial Review Dashboard 2025

## What You Have

Your interactive financial review dashboard is ready! This is a beautiful, self-contained HTML file with all your 2025 financial data embedded.

## Files Created

1. **financial_review_2025.html** (2.0 MB)
   - Your main dashboard - open this in any browser
   - Self-contained, shareable file
   - No internet required to view (all libraries loaded from CDN on first open)

2. **generate_dashboard.py**
   - Python script to regenerate the dashboard
   - Pulls data from personal_finance.db
   - Can be run anytime to get fresh data

3. **dashboard_template.html**
   - HTML template used by the generator
   - Modify this if you want to customize the design

4. **IMPLEMENTATION_PLAN.md**
   - Detailed technical documentation
   - Reference for future modifications

## How to Use

### View the Dashboard

Simply open the dashboard:
```bash
open financial_review_2025.html
```

Or double-click the file in Finder.

### Interactive Features

The dashboard includes:

**Filters & Controls:**
- Date range presets (2022, 2023, 2024, 2025, All Time)
- Multi-select owners (Cacas, Cata, Suricata)
- Multi-select categories
- Include/exclude business transactions
- Highlight outlier transactions

**Overview Cards:**
- Total spent
- Average monthly spending
- Top category
- Transaction count

**Interactive Charts:**
1. **Monthly Spending Trend** - Line chart showing spending over time by owner
2. **Category Breakdown** - Pie chart of spending by category
3. **Owner Comparison** - Stacked bar chart comparing owners month-by-month
4. **Top 20 Expenses** - Horizontal bar chart of largest transactions
5. **Spending Heatmap** - When you spend most (day of week vs week of month)

**Comparison Tools:**
- **Month Comparison** - Compare any two months side-by-side
- **Category Deep Dive** - Explore spending within a specific category

**Transaction Explorer:**
- Full searchable table of all transactions
- Check/uncheck transactions to exclude outliers
- All charts update in real-time when you toggle transactions
- Pagination for easy browsing
- Export filtered data to CSV

### Tips for Your Review with Your Wife

1. **Start with the Overview** - Look at total spent and top categories
2. **Use Month Comparison** - Compare recent months to see trends
3. **Click Categories** - Click any category in the pie chart to filter
4. **Find Outliers** - Enable "Highlight Outliers" to spot unusual expenses
5. **Toggle Transactions** - Uncheck one-time expenses to see normal patterns
6. **Export Data** - Use "Export to CSV" to save filtered views

### Regenerate with Fresh Data

If you add more transactions before your review:

```bash
cd "/Users/elcacas/Desktop/Finance Dashboard/Review 2025"
python3 generate_dashboard.py
```

This will create a new `financial_review_2025.html` with updated data.

## Data Summary

- **Total Transactions**: 6,912 (1 transaction excluded due to data error)
- **Date Range**: 2022-01-03 to 2026-01-01
- **Owners**: Cacas, Cata, Suricata
- **Outliers Identified**: 83 transactions (>2 standard deviations)

## Next Steps

1. **Review Together** - Open the dashboard and explore your financial habits
2. **If You Like It** - We can integrate the best features into your main FinanceDashboard.app
3. **Customize** - Let me know if you want any changes to colors, charts, or features

## Technical Stack

- **Data Processing**: Python (pandas, sqlite3)
- **Visualization**: Plotly.js
- **Interactivity**: Alpine.js
- **Styling**: Tailwind CSS
- **Output**: Self-contained HTML (works offline)

## Questions?

The dashboard is fully functional and ready for your year-end review. Enjoy exploring your financial data together!
