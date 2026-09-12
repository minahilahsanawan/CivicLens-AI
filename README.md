# CivicLens AI

## From public reports to verified action

CivicLens AI is a multilingual, explainable civic-operations platform. It turns a citizen's photograph, location, and description into a prioritized, department-ready complaint. The application combines Groq multimodal AI, LangChain, FAISS, HuggingFace embeddings, SQLite, and Streamlit.

This repository is designed for a hackathon demonstration and as a foundation for a public civic-reporting product.

## Product concept

Most civic-reporting tools stop after collecting a complaint. CivicLens AI continues the operational workflow:

```text
Citizen evidence
      ↓
AI classification and confidence
      ↓
RAG-based department routing
      ↓
Duplicate detection and priority score
      ↓
SLA assignment and operational work order
      ↓
Status timeline and department action
      ↓
Before/after resolution verification
      ↓
Citizen confirmation or automatic reopening
```

## Features

### Citizen reporting

- English and Urdu interface options
- English, Urdu, and Roman Urdu descriptions
- Photo upload with preview
- Manual latitude and longitude capture
- Categories for potholes, streetlights, garbage, water/sewer, parks, and traffic safety
- Unique ticket ID generated for every complaint
- Citizen-facing AI summary

### AI and RAG layer

- Groq Vision for image classification and resolution verification
- A valid Groq API key is required for AI analysis
- Confidence scoring for every classification
- Human-review flag for uncertain cases
- FAISS vector retrieval over `data/departments.txt`
- HuggingFace `sentence-transformers/all-MiniLM-L6-v2` embeddings
- Explainable routing reason
- Recommended department action

### Operational intelligence

- Severity: low, medium, high, or critical
- Priority score from severity, confidence, and nearby duplicate reports
- Duplicate detection for same-category reports within 350 metres
- Category-specific SLA assignment
- SLA deadline and remaining-time display
- Overdue complaint indicator
- Department work-order information
- Department workload chart
- Priority queue sorted by risk and age
- Interactive complaint map

### Resolution lifecycle

- Submitted → Acknowledged → In Progress → Resolved workflow
- Status notes
- Full complaint event timeline
- Before-and-after resolution image upload
- AI resolution-confidence estimate
- Citizen feedback: Resolved, Partially resolved, or Not resolved
- Automatic reopening when a citizen reports that the problem remains

## Supported departments

The included knowledge base contains six departments:

1. Public Works and Roads
2. Street Lighting and Electrical Services
3. Waste Management and Sanitation
4. Water Supply and Sewerage
5. Parks and Public Spaces
6. Traffic and Road Safety

`data/departments.txt` is a manually curated demonstration knowledge base. For a real city, replace its content with official department names, service boundaries, contact details, escalation rules, and verified SLAs.

## Repository structure

```text
civic-issue-reporter/
├── app.py                         # Streamlit interface and workflow
├── requirements.txt               # Python dependencies
├── .env                           # Local configuration template
├── .gitignore                     # Secrets and generated files excluded
├── README.md                      # This documentation
├── data/
│   └── departments.txt            # Custom RAG knowledge base
├── utils/
│   ├── __init__.py
│   ├── database.py                # SQLite, SLA, duplicates, events
│   ├── providers.py               # Groq provider calls
│   ├── rag.py                     # FAISS retrieval and routing
│   └── vision.py                  # Classification and verification
└── uploads/
    └── .gitkeep                   # Runtime image directory
```

## Requirements

- Python 3.10 or newer
- A Groq API key for image classification, RAG routing, and resolution verification
- Internet access on the first RAG run to download the embedding model

## API key setup

### Groq

1. Open [Groq Console](https://console.groq.com/keys).
2. Create an account or sign in.
3. Open **API Keys**.
4. Select **Create API Key**.
5. Copy the key and store it securely.

Never publish the key in GitHub, screenshots, chat messages, or frontend code.

## Local configuration

Open `.env` and replace the example values:

```env
GROQ_API_KEY=your_real_groq_key_here
GROQ_VISION_MODEL=qwen/qwen3.6-27b
GROQ_RAG_MODEL=llama-3.1-8b-instant
```

The Groq model names are configurable because provider model catalogs can change. If a model becomes unavailable, update the corresponding value in `.env` without changing the rest of the application.

## Install and run locally

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

The browser will open the local Streamlit URL. On the Report issue page, enter the latitude and longitude for the reported location.

## How a complaint is processed

1. The citizen uploads a photo.
2. The citizen enters the location coordinates.
3. Groq Vision attempts to classify the issue.
4. Groq generates the classification with a confidence score.
6. FAISS retrieves the most relevant department knowledge-base chunks.
7. Groq generates a department, routing reason, and recommended action.
8. If Groq text routing fails, the application shows a clear error instead of silently assigning an unreliable department.
9. The system calculates severity-based SLA and priority score.
10. Nearby open reports of the same category are shown as possible duplicates.
11. SQLite stores the ticket and event timeline.
12. A department can update status and upload resolution evidence.
13. The citizen can confirm resolution or reopen the complaint.

## GitHub deployment

### Create the repository

1. Sign in to GitHub.
2. Select **New repository**.
3. Name it `civic-issue-reporter`.
4. Keep it empty. Do not add a README, `.gitignore`, or license because these already exist locally.
5. Create the repository.

### Push the local project

Open PowerShell or Terminal inside the extracted project folder:

```bash
git init
git add .
git status
git commit -m "Build CivicLens AI civic operations platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/civic-issue-reporter.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

Before pushing, confirm that `.env` does not appear in `git status`. It is intentionally ignored by `.gitignore`.

If GitHub asks for authentication, use GitHub Desktop, Git Credential Manager, or a GitHub personal access token rather than your account password.

## Streamlit Community Cloud deployment

1. Push the project to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Sign in with GitHub.
4. Select **Create app** or **New app**.
5. Select the repository `civic-issue-reporter`.
6. Select branch `main`.
7. Set the main file to `app.py`.
8. Open **Advanced settings**.
9. Add the following in the **Secrets** field:

```toml
GROQ_API_KEY = "your_real_groq_key_here"
GROQ_VISION_MODEL = "qwen/qwen3.6-27b"
GROQ_RAG_MODEL = "llama-3.1-8b-instant"
```

10. Select **Deploy**.
11. Wait for dependencies and the embedding model to install.
12. Open the public URL and test image upload, AI analysis, ticket tracking, and the dashboard.

## Streamlit deployment testing checklist

Run this checklist after deployment:

- App opens without an import error.
- Sidebar language selector works.
- The location form accepts manually entered coordinates.
- Manual coordinates still work.
- A valid streetlight image creates a ticket.
- A pothole image routes to Public Works and Roads.
- A second nearby report triggers duplicate detection.
- A low-confidence AI classification is clearly marked for human review.
- Track complaints displays the original image and timeline.
- Status changes create timeline events.
- Resolution image verification works with both providers.
- “Not resolved” changes the complaint back to “In Progress.”
- Dashboard metrics, charts, map, and priority queue load correctly.

## Troubleshooting

### `GROQ_API_KEY is not configured`

For local use, check `.env` and restart Streamlit. For Streamlit Cloud, add the key under **Advanced settings → Secrets**, save, and reboot the app.

### Groq model not found or decommissioned

Set a currently available Groq model in `.env` or Streamlit secrets and confirm that the Groq account can access it.

Run:

```bash
pip install --upgrade google-genai
```

Then verify that `GROQ_API_KEY` is present and valid.

### Location coordinates

The final interface uses manually entered latitude and longitude values. This keeps the public workflow predictable and avoids browser permission failures.

### FAISS or embedding installation error

Use Python 3.10–3.12, upgrade pip, and reinstall:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### App is slow on first request

The first RAG request downloads and loads the MiniLM embedding model. Later requests reuse the cached FAISS index during that app process.

## Security and privacy

- Do not commit `.env` or real API keys.
- Do not upload sensitive personal documents as civic evidence.
- Use anonymous reporting for public demonstrations.
- Treat AI classification as decision support, not final legal or emergency authority.
- Critical hazards still require human verification and appropriate emergency channels.
- For production, add image redaction for faces, number plates, and private documents.
- For production, use authentication and role-based access for citizens, departments, and administrators.

## Current prototype limitations

The hackathon version uses local SQLite and local image storage. Streamlit Cloud storage is not a durable production database, and files may not survive redeployments or restarts. A production version should use managed PostgreSQL and object storage, such as Supabase.

Other recommended production upgrades include official reverse geocoding, real department APIs, notification delivery, field-team routing, image privacy redaction, rate limiting, structured status history, monitoring, and formal AI evaluation against a labelled civic-image test set.

## Recommended hackathon demonstration

1. Select Urdu.
2. Enter the latitude and longitude for the reported location.
3. Upload a broken streetlight image.
4. Enter a Roman Urdu description.
5. Show the AI category, confidence, priority score, department, routing explanation, and SLA.
6. Submit a second nearby streetlight report and demonstrate duplicate detection.
7. Open the ticket timeline and change its status.
8. Upload an after-repair photo and show AI verification.
9. Select “Not resolved” and show automatic reopening.
10. Finish on the operations dashboard with the priority queue, department workload, and map.

## License

This project is provided as a hackathon prototype. Add an appropriate open-source license before public redistribution or commercial deployment.
