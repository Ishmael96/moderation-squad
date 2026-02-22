# Moderation Squad Portal

Professional moderation career platform. Deployed on Render.com.

## Setup
1. Fork/upload this repo to GitHub
2. Connect to Render.com as a Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Deploy!

## Features
- OTP email login (whitelist-based)
- Persistent SQLite database (jobs, profiles, notifications all saved permanently)
- Job applications that persist across sessions
- Training courses with certificates
- Live support chat
- Earnings tracker
- Schedule management
