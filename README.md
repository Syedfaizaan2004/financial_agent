# 🏦 AI Financial Research Agent

An intelligent, production-grade **Financial & Market Research Agent** that acts as a junior equity research analyst. It provides stock trend forecasting, fundamental analysis, risk detection, peer comparison, scenario stress testing, investment memo generation, and memory-based personalization — all accessible through a sleek Next.js dashboard.

---

## ✨ Features

- 📈 **Stock Forecasting** — Ensemble of TFT (Temporal Fusion Transformer) & XGBoost models for multi-day price trend prediction
- 🧠 **AI-Powered Analysis** — LLM-driven quick explanations, building context, and investment memos (Groq / Gemini / Local via Ollama)
- 🔍 **Fundamental Analysis** — Company financials, revenue trends, and earnings breakdowns via yFinance & Alpha Vantage
- ⚖️ **Risk Engine** — Automated risk scoring, contradiction detection, and confidence scoring
- 🤝 **Peer Comparison** — Side-by-side sector benchmarking
- 🧪 **Scenario Stress Testing** — What-if analysis for market conditions
- 🗃️ **Memory & Personalization** — Per-user risk profile and time-horizon preferences (SQLite-backed)
- 🎭 **Demo Mode** — Preloaded data for AAPL, MSFT, TSLA, GOOGL for instant showcasing
- ⚡ **Caching Layer** — Configurable TTL cache to minimize redundant API calls

---

## 🗂️ Project Structure

```
Ai_Financial_Agent/
├── backend/
│   ├── agent/            # Core agent logic, intent parsing, workflows, memo generation
│   ├── api/              # FastAPI route definitions and router
│   ├── app/              # App factory, config, CORS, dependencies
│   ├── core/             # Shared utilities and core services
│   ├── data/             # Data fetching and processing modules
│   ├── db/               # SQLite session and ORM models
│   ├── demo/             # Demo mode preloaded data and configuration
│   ├── forecasting/      # TFT & XGBoost forecasting models
│   │   ├── tft/          # PyTorch Temporal Fusion Transformer
│   │   └── xgboost/      # XGBoost regression model
│   ├── memory/           # User memory and personalization engine
│   ├── risk_engine/      # Risk scoring, contradiction, and confidence logic
│   └── utils/            # Shared helper utilities
├── frontend/
│   ├── app/              # Next.js 14 App Router pages
│   ├── components/       # UI components (dashboard, charts, panels)
│   └── lib/              # API client and utility functions
├── data/                 # Raw / cached market data
├── .env                  # Environment configuration (see setup)
├── financial_agent.db    # SQLite database (auto-created)
├── app.log               # Application log file
└── test_agent.py         # Agent smoke tests
```

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| LLM Integration | Groq API / Google Gemini / Ollama (local) |
| Forecasting | PyTorch (TFT), XGBoost, scikit-learn |
| Market Data | yFinance, Alpha Vantage |
| Database | SQLite (via SQLAlchemy) |
| Server | Uvicorn (ASGI) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| UI Components | Lucide React, Recharts |
| Styling | Tailwind CSS |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) [Ollama](https://ollama.ai/) for local LLM inference

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Ai_Financial_Agent.git
cd Ai_Financial_Agent
```

### 2. Set Up the Backend

```bash
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Description | Required |
|---|---|---|
| `LLM_PROVIDER` | `groq`, `gemini`, or `local` | ✅ |
| `GROQ_API_KEY` | Your Groq API key | If using Groq |
| `GEMINI_API_KEY` | Your Google Gemini API key | If using Gemini |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage market data key | Optional |
| `DATABASE_URL` | SQLite URL (default `sqlite:///./financial_agent.db`) | ✅ |
| `DEMO_MODE` | `True` to enable preloaded demo data | Optional |

### 4. Run the Backend

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 5. Set Up & Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

---

## 🔑 LLM Provider Setup

Choose your preferred provider in `.env`:

```env
LLM_PROVIDER=groq       # Options: groq | gemini | local
```

**Groq** (recommended — fast and free tier available):
1. Get a free key at [console.groq.com](https://console.groq.com)
2. Set `GROQ_API_KEY=your_key`

**Google Gemini** (free tier available):
1. Get a key at [aistudio.google.com](https://aistudio.google.com)
2. Set `GEMINI_API_KEY=your_key`

**Local (Ollama)**:
1. Install [Ollama](https://ollama.ai/) and pull a model: `ollama pull llama3`
2. Set `LLM_PROVIDER=local` and `LOCAL_LLM_MODEL=llama3`

---

## 📊 Forecasting Models

The agent uses a **TFT + XGBoost ensemble** for price forecasting.

| Asset | Path |
|---|---|
| TFT model weights | `backend/forecasting/tft/tft_model.pth` |
| TFT dataset params | `backend/forecasting/tft/tft_dataset_params.pkl` |
| XGBoost model | `backend/forecasting/xgboost/xgb_model.pkl` |
| Feature list | `backend/forecasting/features.pkl` |
| Supported tickers | `backend/forecasting/stocks_used.pkl` |

> **Note:** Model files are not included in the repository due to size. Place pre-trained files in the paths listed above, or the app will start in stub (demo) mode.

---

## 🎭 Demo Mode

Enable demo mode for instant out-of-the-box showcase:

```env
DEMO_MODE=True
DEMO_TICKERS=AAPL,MSFT,TSLA,GOOGL
DEMO_CACHE_TTL=3600
```

In demo mode the agent serves preloaded responses for the configured tickers without requiring live API keys or model files.

---

## 🔐 Security

- API key authentication is supported (set `API_KEY_REQUIRED=True` and `API_KEY=your_secret`)
- Never commit your `.env` file — it is listed in `.gitignore`
- Rotate API keys from the respective provider dashboards if accidentally exposed

---

## 📝 API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/docs` | GET | Interactive Swagger UI |
| `/redoc` | GET | ReDoc API documentation |
| `/api/v1/agent/query` | POST | Submit a natural-language research query |
| `/api/v1/forecast/{ticker}` | GET | Get price forecast for a ticker |
| `/api/v1/risk/{ticker}` | GET | Get risk assessment |
| `/api/v1/memo/{ticker}` | GET | Generate investment memo |
| `/api/v1/memory/profile` | GET/POST | Fetch / update user personalization profile |

---

## 🧪 Testing

```bash
# Run agent smoke tests
python test_agent.py
```

---

## 📄 License

This project is for research and educational purposes. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) — modern Python API framework  
- [Next.js](https://nextjs.org/) — React production framework  
- [PyTorch Forecasting](https://pytorch-forecasting.readthedocs.io/) — TFT implementation  
- [yFinance](https://pypi.org/project/yfinance/) — free market data  
- [Groq](https://groq.com/) / [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM providers  
