# Business Finder AI System

**Status**: Production-ready ✅  
**Version**: 1.0.0  
**Last Updated**: January 28, 2026

A comprehensive AI system for finding small businesses (restaurants, cafés, takeaways, bakeries) without websites or social media presence. The system uses multiple data sources, machine learning, and human review to achieve high accuracy in identifying businesses that lack digital presence.

## � Documentation

| Document | Purpose |
|----------|---------|
| [PRODUCTION.md](PRODUCTION.md) | **Complete production deployment guide** (Docker & traditional) |
| [DOCKER_COMPOSE.md](DOCKER_COMPOSE.md) | Docker Compose quick-start and operations |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Pre/post-deployment verification checklist |
| [COMPLETION.md](COMPLETION.md) | Project status and completed tasks |

## 🚀 Quick Start

### Development (Local)

```bash
# Backend
.venv311/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Frontend (new terminal)
npm start  # Opens http://localhost:3000

# Test retraining: Click "Seed demo labels" on Dashboard
```

### Production Deployment

```bash
# Docker Compose (recommended - 5 minute setup)
git clone https://github.com/yourusername/business-finder.git
cd business-finder
cp env.example .env
# Edit .env with your values
docker-compose up -d

# See DOCKER_COMPOSE.md for detailed steps
```

## ✨ Features

- **Multi-source Data Ingestion**: CSV files, Google Places API, OpenStreetMap
- **Data Normalization**: Name/address standardization and deduplication
- **Website Detection**: Google search with aggregator filtering
- **Social Media Detection**: Facebook, Instagram, Twitter/X, LinkedIn
- **ML Classification**: Confidence scoring with logistic regression, random forest, LightGBM
- **Human Review Dashboard**: React-based interface with pagination and accessibility
- **Retraining Pipeline**: Retrain models with human labels and auto-reclassify all businesses
- **Export Capabilities**: CSV/JSON export with filtering options
- **Admin Seeding**: Demo endpoint to seed labeled data for testing

## 🏗️ Architecture

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Data Sources   │    │   Processing     │    │   Output         │
│                  │    │                  │    │                  │
│ • CSV Files      │───▶│ • Normalization  │───▶│ • Dashboard      │
│ • Google Places  │    │ • Website Check  │    │ • API Endpoints  │
│ • OpenStreetMap  │    │ • Social Check   │    │ • CSV/JSON       │
│                  │    │ • ML Train/Class │    │ • Metrics        │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │  ML Models (*)   │
                      │ • Logistic Reg   │
                      │ • Random Forest  │
                      │ • LightGBM       │
                      └──────────────────┘

(*) Models are trained with human-labeled examples via /api/retrain
```

## 📋 System Requirements

### Backend
- **Python**: 3.11+ (uses .venv311 virtual environment)
- **Database**: PostgreSQL (production) or SQLite (development)
- **Optional APIs**: Google Places API, social media tokens

### Frontend
- **Node.js**: 16+
- **React**: 18+
- **Build**: TailwindCSS, code-splitting with React.lazy

### Deployment
- **Docker** (recommended) or traditional server (Nginx + Supervisor)
- **Reverse proxy**: Nginx for SSL/TLS and load balancing
- **Process manager**: Supervisor or systemd


## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AISystemFDM
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Configure Environment Variables
```bash
cp env.example .env
# Edit .env with your configuration
```

#### Database Setup
```bash
# For PostgreSQL
createdb business_finder
# Update DATABASE_URL in .env

# For SQLite (development)
# DATABASE_URL=sqlite:///./business_finder.db
```

#### Initialize Database
```bash
python database.py
```

### 3. Frontend Setup

#### Install Node Dependencies
```bash
npm install
```

#### Build Frontend
```bash
npm run build
```

## 🚀 Usage

### 1. Run the Complete Pipeline
```bash
python run_pipeline.py
```

This will:
- Ingest data from all sources
- Normalize and deduplicate businesses
- Check for websites and social media
- Classify businesses using ML
- Export results

### 2. Run Individual Components

#### Data Ingestion
```bash
python ingest.py
```

#### Data Normalization
```bash
python normalize.py
```

#### Website Detection
```bash
python website_checker.py
```

#### Social Media Detection
```bash
python social_checker.py
```

#### ML Classification
```bash
python classifier.py
```

#### Export Data
```bash
python export.py
```

### 3. Start the Web Dashboard

#### Backend API
```bash
python main.py
```

#### Frontend (Development)
```bash
npm start
```

#### Frontend (Production)
```bash
npm run build
# Serve the build folder with your web server
```

## 📊 Data Sources

### 1. CSV Files
- Local government business registries
- Food hygiene databases
- Custom business listings

### 2. Google Places API
- Business information and websites
- Contact details and addresses
- User reviews and ratings

### 3. OpenStreetMap
- POI data for restaurants and cafés
- Address information
- Business categories

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/business_finder

# Google APIs
GOOGLE_PLACES_API_KEY=your_api_key_here
GOOGLE_SEARCH_API_KEY=your_search_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here

# Social Media APIs (Optional)
FACEBOOK_ACCESS_TOKEN=your_facebook_token_here
INSTAGRAM_ACCESS_TOKEN=your_instagram_token_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
CONFIDENCE_THRESHOLD=0.7
MAX_SEARCH_RESULTS=10

# Web Scraping
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
REQUEST_DELAY=1.0
MAX_RETRIES=3
```

### Pipeline Configuration

```bash
# Skip certain steps (useful for development)
SKIP_INGESTION=false
SKIP_WEBSITE_CHECK=false
SKIP_SOCIAL_CHECK=false
SKIP_CLASSIFICATION=false
```

## 📈 Usage Examples

### 1. Basic Pipeline Run
```bash
# Run complete pipeline
python run_pipeline.py

# Check results
ls -la *.csv *.json
```

### 2. Custom Data Ingestion
```python
from ingest import DataIngester

ingester = DataIngester()

# Ingest from CSV
ingester.ingest_csv("my_businesses.csv", "Custom Data")

# Ingest from Google Places
ingester.ingest_google_places("restaurants", "London, UK", 5000)

# Ingest from OSM
ingester.ingest_osm((51.5074, -0.1278, 51.5074, -0.1278))
```

### 3. Custom Classification
```python
from classifier import BusinessClassifier

classifier = BusinessClassifier()

# Train model
X, y = classifier.prepare_training_data()
metrics = classifier.train_model(X, y)

# Classify businesses
classifier.classify_all_businesses()

# Get high confidence predictions
high_confidence = classifier.get_high_confidence_predictions(threshold=0.8)
```

### 4. Custom Export
```python
from export import BusinessExporter

exporter = BusinessExporter()

# Export all businesses
exporter.export_to_csv("all_businesses.csv")

# Export approved businesses only
exporter.export_approved_only("approved_businesses.csv")

# Export high confidence predictions
exporter.export_high_confidence("high_confidence.csv", confidence_threshold=0.8)
```

## 🎯 API Endpoints

### Business Management
- `GET /api/businesses` - List all businesses
- `GET /api/businesses/{id}` - Get specific business
- `PATCH /api/businesses/{id}` - Update business
- `POST /api/businesses/{id}/approve` - Approve business
- `POST /api/businesses/{id}/reject` - Reject business

### Statistics
- `GET /api/stats` - Get system statistics

### Export
- `GET /api/export/csv` - Export to CSV

## 📊 Output Formats

### CSV Export
```csv
id,name,address,phone,city,postcode,website_present,website_url,social_present,social_links,no_website_no_social,confidence_score,sources,last_checked_date,human_review,notes
1,"The Golden Dragon","123 High Street","020 1234 5678","London","SW1A 1AA",false,"",false,"{}",true,0.85,"Sample Data","2024-01-15T10:30:00","approved","Verified no website"
```

### JSON Export
```json
{
  "id": 1,
  "name": "The Golden Dragon",
  "address": "123 High Street",
  "phone": "020 1234 5678",
  "city": "London",
  "postcode": "SW1A 1AA",
  "website_present": false,
  "website_url": null,
  "social_present": false,
  "social_links": {},
  "no_website_no_social": true,
  "confidence_score": 0.85,
  "sources": ["Sample Data"],
  "last_checked_date": "2024-01-15T10:30:00",
  "human_review": "approved",
  "notes": "Verified no website"
}
```

## 🔍 Dashboard Features

### Business Review Interface
- **Business Information**: Name, address, phone, city
- **Digital Presence**: Website and social media status
- **AI Analysis**: Classification and confidence score

## 🔁 Demo seeding & retraining (development)

To speed up demos and enable retraining without manual labeling, you can seed demo labels locally.

- Enable seeding: set the environment variable `DEMO_ALLOW_SEED=true` (defaults to `true` in development).
- Seed labels (10 by default):
  - Backend: `POST /api/admin/seed_labels?count=10`
  - Frontend: open the Dashboard on `localhost` and click **Seed demo labels** (visible only on local hosts).

After seeding, trigger a retrain:

- `POST /api/retrain` — this will return either `status: ok` with training metrics or an error message if ML dependencies are missing. If you see `status: not_enough_data`, ensure you seeded at least 10 labeled examples.

This helps you demo the full end-to-end retraining flow without manual labeling.

- **Review Actions**: Approve, reject, or add notes
- **Search & Filter**: Find businesses by various criteria

### Export Interface
- **Format Selection**: CSV or JSON export
- **Filtering Options**: By status, confidence, source
- **Preview**: See what will be exported
- **Statistics**: Export summary and counts

## 🧪 Testing

### Run Tests
```bash
# Backend tests
python -m pytest tests/

# Frontend tests
npm test
```

### Sample Data
The system includes `sample_data.csv` with example businesses for testing.

## 📝 Logging

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information about pipeline progress
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures

### Log Files
- `business_finder.log`: Complete pipeline logs
- Console output: Real-time progress updates

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection
```bash
# Check database connection
python -c "from database import get_session; print('Database connected')"
```

#### 2. API Keys
```bash
# Verify API keys are set
python -c "import os; print('Google API Key:', bool(os.getenv('GOOGLE_PLACES_API_KEY')))"
```

#### 3. Dependencies
```bash
# Check Python dependencies
pip list | grep -E "(fastapi|sqlalchemy|pandas|scikit-learn)"

# Check Node dependencies
npm list
```

#### 4. Port Conflicts
```bash
# Check if ports are available
lsof -i :8000  # Backend API
lsof -i :3000  # Frontend development server
```

### Performance Optimization

#### 1. Database Indexing
```sql
-- Add indexes for better performance
CREATE INDEX idx_businesses_name ON businesses(name);
CREATE INDEX idx_businesses_city ON businesses(city);
CREATE INDEX idx_businesses_confidence ON businesses(confidence_score);
```

#### 2. Rate Limiting
```bash
# Adjust request delays
REQUEST_DELAY=2.0  # Increase for slower APIs
MAX_RETRIES=5      # Increase for unreliable connections
```

#### 3. Memory Usage
```bash
# Monitor memory usage
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Places API for business data
- OpenStreetMap for POI information
- Scikit-learn for machine learning
- React and Tailwind CSS for the frontend
- FastAPI for the backend API

## 📞 Support

For questions or issues:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Create an issue on GitHub
4. Contact the development team

---

**Note**: This system is designed for research and development purposes. Ensure compliance with API terms of service and data protection regulations when using in production.
