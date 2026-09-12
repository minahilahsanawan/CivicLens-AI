# CivicLens AI

<p align="center">
  <a href="https://civiclensai.streamlit.app"><img src="https://img.shields.io/badge/Live%20Demo-Open%20CivicLens%20AI-e97855?style=for-the-badge&logo=streamlit&logoColor=white" alt="Open CivicLens AI live demo"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit app">
</p>

CivicLens AI is a multilingual civic-operations platform that turns a citizen's photo, location, and description into a structured, prioritized, department-ready complaint. It connects public reporting with department routing, duplicate detection, SLA tracking, status timelines, and resolution evidence.

> **Try it now:** press the **Open the Live Streamlit Demo** button above to launch the deployed application.

## What it does

```text
Photo + location + description
              ↓
Issue classification and confidence
              ↓
Department routing and explanation
              ↓
Duplicate detection and priority score
              ↓
SLA-aware work order and timeline
              ↓
Resolution evidence and citizen feedback
```

## Key features

### Citizen reporting

- English and Urdu interface
- English, Urdu, and Roman Urdu descriptions
- Civic-evidence photo upload with preview
- Manual latitude and longitude fields
- Categories for roads, streetlights, waste, water/sewer, parks, and traffic safety
- Unique ticket ID for every complaint
- Human-readable AI summary and routing explanation

### AI-assisted operations

- Local image classification mode for API-free demos
- Optional Groq multimodal AI provider
- Confidence scoring and human-review indicators
- Local knowledge-base routing for predictable demo behavior
- Optional FAISS and HuggingFace retrieval layer
- Recommended department action

### Prioritization and tracking

- Low, medium, high, and critical severity
- Priority score based on severity, confidence, duplicates, and age
- Nearby duplicate detection within a configurable distance
- Category-based SLA deadlines
- Overdue and remaining-time indicators
- Complaint status timeline
- Operations dashboard with metrics, charts, map, and priority queue

### Resolution workflow

- Submitted → Acknowledged → In Progress → Resolved
- Status notes and event history
- Before-and-after resolution evidence
- Optional AI resolution verification
- Citizen feedback: resolved, partially resolved, or not resolved
- Automatic reopening when the citizen reports that the issue remains

## Supported departments

1. Public Works and Roads
2. Street Lighting and Electrical Services
3. Waste Management and Sanitation
4. Water Supply and Sewerage
5. Parks and Public Spaces
6. Traffic and Road Safety

The demo knowledge base is stored in `data/departments.txt`. For a real city, replace it with official departments, service boundaries, contact details, escalation rules, and verified SLAs.

## Technology

| Layer | Tools |
|---|---|
| Interface | Streamlit |
| Image understanding | HuggingFace Transformers, CLIP, Pillow |
| Optional hosted AI | Groq |
| Retrieval | LangChain, FAISS, HuggingFace embeddings |
| Data and analytics | SQLite, Pandas, Altair |
| Deployment | Streamlit Community Cloud |

## API keys: optional or required?

The app can run without an API key in local/demo mode:

- The local CLIP model classifies the uploaded image.
- Local routing maps the category to a department and action.
- Resolution evidence can be saved for manual review.

A Groq API key is optional. When configured, it enables hosted multimodal analysis and automatic resolution verification. Never commit a real key to GitHub or include it in screenshots.

## Project structure

```text
civic-issue-reporter/
├── app.py                         # Streamlit interface and workflow
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
├── data/
│   └── departments.txt            # Routing knowledge base
├── utils/
│   ├── database.py                # SQLite, SLAs, duplicates, events
│   ├── providers.py               # Optional Groq provider
│   ├── rag.py                     # Local and FAISS routing
│   └── vision.py                  # Local image classification and verification
└── uploads/
    └── .gitkeep                   # Runtime evidence directory
```

## Run locally

### Windows PowerShell

```powershell
cd path\to\civic-issue-reporter
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### macOS or Linux

```bash
cd /path/to/civic-issue-reporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The first API-free image analysis may take longer because the CLIP model is downloaded and loaded. Later runs reuse the cached model.

## Optional Groq configuration

Create a local `.env` file, or add the same values in Streamlit Cloud **App settings → Secrets**:

```toml
GROQ_API_KEY = "your_key_here"
GROQ_VISION_MODEL = "your_available_vision_model"
GROQ_RAG_MODEL = "your_available_text_model"
```

If a Groq model is deprecated or unavailable, remove the optional key to use local mode, or replace the model names with currently supported models from the Groq console.

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select **Create app**.
4. Choose the repository and the `main` branch.
5. Set the main file to `app.py`.
6. Select **Deploy**.
7. If using Groq, add the optional secrets under **App settings → Secrets**.
8. After code changes, use **Manage app → Reboot app** if the new version does not appear immediately.

The live deployment for this repository is available here:

**[https://civiclensai.streamlit.app](https://civiclensai.streamlit.app)**

## Typical workflow

1. Select English or Urdu and choose Light or Dark appearance.
2. Open **Report issue**.
3. Upload a civic issue photo.
4. Enter the location coordinates and observation.
5. Confirm that the image is safe to use for civic reporting.
6. Analyze and submit the complaint.
7. Review the category, confidence, severity, department, priority, and SLA.
8. Track the complaint and update its status.
9. Add resolution evidence for manual or optional AI verification.
10. Review the operations dashboard and priority queue.

## Troubleshooting

### The app still shows an old version

Confirm that the latest `app.py`, `utils/`, `requirements.txt`, and `README.md` files were committed and pushed to the repository connected to Streamlit Cloud. Then select **Manage app → Reboot app** and refresh the browser with `Ctrl + F5`.

### The app is slow on the first image

This is expected in API-free mode: the CLIP model has to download and initialize on the first request. Keep the app open until the model finishes loading. Subsequent analyses are faster while the app process remains active.

### Groq returns a deprecation or JSON error

The configured Groq model may no longer be supported, or the provider may return malformed structured output. Remove `GROQ_API_KEY` to run the stable local mode, or update the model values in Secrets with currently supported Groq models.

### FAISS or embedding installation fails

Use Python 3.10–3.12 and upgrade the packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Privacy and production notes

- Do not commit `.env`, API keys, or private evidence.
- Treat AI output as decision support, not emergency or legal authority.
- Add image redaction for faces, number plates, and private documents before production use.
- Use managed PostgreSQL and object storage instead of local SQLite and local files for a durable deployment.
- Add authentication, role-based access, rate limiting, monitoring, notifications, and formal model evaluation before public launch.

## License

This project is provided as a hackathon prototype. Add an open-source license before public redistribution or commercial deployment.
