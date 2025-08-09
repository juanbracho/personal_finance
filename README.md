# 💰 Personal Finance Dashboard

A comprehensive, personal finance management system built with Flask, featuring advanced analytics, budget tracking, and intelligent insights.

![Dashboard Preview](https://img.shields.io/badge/Status-MVP%20Complete-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3%2B-lightgrey)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue)
![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap%205.3-purple)

## 🚀 Features

### 📊 Enhanced Dashboard
- **Real-time Financial Overview**: Current month spending, YTD comparisons, and trend analysis
- **Budget Performance**: Visual indicators for over/under/on-track categories
- **Owner Comparison**: Multi-owner expense tracking with delta calculations
- **Recent Activity**: Quick access to latest transactions
- **Debt Summary**: Total debt overview with status indicators

### 📈 Advanced Analytics
- **Interactive Filtering**: Date ranges, categories, owners, accounts, and transaction types
- **Dynamic Charts**: Real-time updates with Plotly.js visualizations
- **Spending Trends**: Time series analysis with type breakdown
- **Category Analysis**: Pie charts and bar graphs with percentage breakdowns
- **Owner Comparison**: Grouped spending analysis across different expense types

### 💳 Transaction Management
- **Multi-account Support**: Track expenses across different financial accounts
- **Smart Categorization**: Organized by categories, subcategories, and expense types
- **Owner Attribution**: Individual and shared expense tracking
- **Business Separation**: Separate personal and business expenses

### 💰 Intelligent Budget System
- **Template-based Budgets**: Reusable budget templates for consistent planning
- **Unexpected Expense Tracking**: Handle budget variances with detailed tracking
- **Variance Analysis**: Automatic calculation of budget vs actual spending
- **Historical Data**: Month-over-month budget performance tracking

### 📉 Debt Management
- **Multiple Debt Types**: Credit cards, loans, mortgages, and custom accounts
- **Payment Tracking**: Automatic transaction creation for debt payments
- **Progress Visualization**: Visual debt reduction progress with completion percentages
- **Interest Rate Management**: Track rates and minimum payments

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask with Blueprint architecture
- **Database**: SQLite with pandas for data manipulation
- **Data Processing**: Pandas for complex financial calculations
- **API Design**: RESTful endpoints with comprehensive error handling

### Frontend
- **UI Framework**: Bootstrap 5.3.0 for responsive design
- **Charts**: Plotly.js for interactive visualizations
- **JavaScript**: Vanilla JS for custom functionality
- **Styling**: Custom CSS with modular component approach

### Development Methodology
- **AI-Assisted Development**: Comprehensive documentation for AI collaboration
- **Modular Architecture**: Blueprint-based structure for maintainability
- **Surgical Coding**: Precise, minimal changes for maximum functionality
- **Context-Driven**: Complete project context in every development session

## 📁 Project Structure

```
personal-finance-dashboard/
├── blueprints/                 # Flask blueprints
│   ├── analytics/             # Advanced analytics system
│   ├── api/                   # RESTful API endpoints
│   ├── budgets/               # Budget management
│   ├── dashboards/            # Main dashboard views
│   ├── debts/                 # Debt tracking system
│   └── transactions/          # Transaction CRUD operations
├── data/                      # Database and data files
│   └── personal_finance.db    # SQLite database
├── static/                    # Static assets
│   ├── css/                   # Modular stylesheets
│   └── js/                    # Component-specific JavaScript
├── templates/                 # Jinja2 templates
│   ├── analytics.html         # Analytics dashboard
│   ├── base.html             # Base template
│   └── ...                   # Feature-specific templates
├── app.py                     # Flask application factory
├── config.py                  # Configuration settings
├── models.py                  # SQLAlchemy models
├── utils.py                   # Database utilities
└── requirements.txt           # Python dependencies
```

## 🚦 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/personal-finance-dashboard.git
   cd personal-finance-dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python -c "from app import initialize_personal_finance_database; initialize_personal_finance_database()"
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the dashboard**
   Open your browser and navigate to `http://localhost:5000`

## 🎯 Usage

### Dashboard Navigation
- **Overview**: Main dashboard with key financial metrics
- **Analytics**: Advanced filtering and data analysis
- **Transactions**: Add, edit, and manage transactions
- **Budget**: Set up and monitor budgets
- **Debts**: Track and manage debt accounts

### Key Workflows

#### Adding Transactions
1. Navigate to **Transactions** → **Add New**
2. Fill in transaction details (amount, category, owner, etc.)
3. Select appropriate transaction type (Needs, Wants, Savings, Business)
4. Save to automatically update all dashboards

#### Budget Management
1. Go to **Budget** section
2. Set initial budget amounts for each category
3. Track unexpected expenses throughout the month
4. Monitor variance in the dashboard overview

#### Analytics Deep Dive
1. Visit the **Analytics** page
2. Use filters to narrow down data (date range, categories, owners)
3. Explore interactive charts for spending patterns
4. Export insights for further analysis

## 📊 Database Schema

### Core Tables
- **transactions**: All financial transactions with categorization
- **budget_templates**: Reusable budget templates
- **unexpected_expenses**: Budget variance tracking
- **debt_accounts**: Debt account information
- **debt_payments**: Payment history and tracking

### Key Relationships
- Transactions linked to budget categories for variance analysis
- Debt payments automatically create transaction records
- Owner-based filtering for multi-user scenarios

## 🎨 Development Principles

### AI-Assisted Development
This project was built using advanced AI collaboration techniques:
- **Context Window Optimization**: Complete project context in every development session
- **Artifact-Based Development**: Reusable, modular code artifacts
- **Surgical Code Changes**: Minimal, precise modifications for maximum functionality
- **Documentation-Driven**: Every feature thoroughly documented for future AI assistance

### Code Quality Standards
- **Modular Blueprints**: Each feature area independently developed and maintained
- **Consistent Error Handling**: Comprehensive try/catch blocks with graceful fallbacks
- **API-First Design**: All data interactions through well-defined endpoints
- **Responsive Design**: Mobile-first approach with desktop optimization

## 🔮 Future Roadmap

### Phase 4: Advanced Features
- **Subcategory Filtering**: Enhanced analytics with subcategory breakdowns
- **Interactive Drill-down**: Click-to-filter capabilities in charts
- **Export Functionality**: PDF reports and CSV data exports
- **Performance Optimization**: Caching for large datasets

### AI Data Analyzer Integration
- **Intelligent Insights**: AI-powered spending pattern analysis
- **Predictive Budgeting**: Machine learning-based budget recommendations
- **Anomaly Detection**: Automatic identification of unusual spending patterns
- **Natural Language Queries**: Ask questions about your finances in plain English

### Additional Enhancements
- **Mobile App**: React Native companion app
- **Bank Integration**: Automatic transaction import via APIs
- **Investment Tracking**: Portfolio management features
- **Multi-currency Support**: International transaction handling

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Follow the AI-assisted development principles** documented in the project
4. **Commit your changes** (`git commit -m 'Add amazing feature'`)
5. **Push to the branch** (`git push origin feature/amazing-feature`)
6. **Open a Pull Request**

### Development Guidelines
- Use the established modular blueprint structure
- Follow the surgical coding principles (minimal, precise changes)
- Include comprehensive error handling
- Update documentation for any new features
- Test all database interactions thoroughly

## 🙏 Acknowledgments

- **AI-Assisted Development**: Built using advanced AI collaboration techniques
- **Open Source Libraries**: Flask, Bootstrap, Plotly.js, and pandas communities
- **Financial Management Inspiration**: Personal finance best practices and methodologies

**Built with ❤️ using AI-assisted development methodologies**

*This project demonstrates the power of human-AI collaboration in software development, featuring comprehensive documentation designed for seamless AI integration and context sharing.*