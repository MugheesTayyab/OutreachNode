# Outreach Node — Custom Cold Emailer

This project is a sub-project developed as part of our **UAV Lab Internship** by **Mughees Tayyab**. 
It is a premium, 100% free multi-agent cold email campaign manager featuring real-time orchestration, a self-correcting critique loop, and Google Text-to-Speech (gTTS) voicemail generation.

---


* **Mughees Tayyab** 


---

## 📌 Features

1. **Social Media Scraper (Prospecting Agent)**: Keyless lookup using DuckDuckGo to find and summarize professional details.
2. **Company Analyst (Context Agent)**: Scrapes Wikipedia and search queries to build strategist briefs with pain points.
3. **Draft Generator (Copywriter Agent)**: Generates highly personalized outreach subject lines and copy.
4. **Fact Checker (Proofreader Agent)**: Evaluates drafts against ground truths, rating and revising drafts (up to 3 retries).
5. **Excel Integration**: Automatically saves campaign status, draft texts, and audio paths to styled sheets.
6. **Voicemail Generator**: Renders audio snippets of personalized pitches using gTTS (100% free, no key needed).
7. **Email Dispatcher**: Connects to SMTP (Gmail App Passwords) for quick, one-click sends.

---

## 🎨 Premium UI/UX Design System
* **Dark Glassmorphism UI**: High-contrast, glowing neon accents (Teal to Purple gradients) with card backdrop blurs.
* **Stepper Visualization**: Real-time tracker reflecting current executing agent stages (Prospecting &rarr; Context &rarr; Copywriter &rarr; Proofreader).
* **Interactive Results Page**: Inline email edit templates, audio players, color-coded badges, and Excel export.

---

## 🚀 Getting Started

### 1. Set Up the Environment
Ensure you have Python 3.10+ installed. Then run:
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and fill in your details:
```env
API_KEY=your_unlimited_surf_or_openai_api_key_here
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password_here
```
*Note: An API key is required (e.g. from Unlimited Surf, OpenRouter, or OpenAI). If SMTP settings are left blank, the app runs in Mock/Development mode and logs sent emails to console.*

### 3. Launch the Application
Start the Flask server:
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## ⚙️ Running Tests
Verify system agents and tools are running correctly:
```bash
pytest tests/ -v
```
