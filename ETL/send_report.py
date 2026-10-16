import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
DB_FILE = "jobs.db"


def send_email_report():
    print("Generating daily market intelligence report...")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM job_postings")
    total_jobs = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT company, title FROM job_postings LIMIT 5")
    sample_jobs = cursor.fetchall()
    conn.close()

    if total_jobs == 0:
        print("No jobs found in database. Skipping email.")
        return

    html_content = f"""
    <h2>Toronto Tech Job Market Report</h2>
    <p><b>Total Active Postings Tracked:</b> {total_jobs}</p>
    <h3>Featured Openings Today:</h3>
    <ul>
    """
    for company, title in sample_jobs:
        html_content += f"<li><b>{company}</b> — {title}</li>"
    html_content += "</ul>"

    # Send securely via Resend HTTP API (Bypasses SMTP port blocks completely)
    headers = {
        "Authorization": f"Bearer {EMAIL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "onboarding@resend.dev",
        "to": RECEIVER_EMAIL,
        "subject": f"📊 Daily Toronto Tech Job Report ({total_jobs} Roles)",
        "html": html_content
    }

    response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)

    if response.status_code == 200 or response.status_code == 201:
        print("Successfully sent market report email via Resend API!")
    else:
        print(f"Failed to send email: {response.text}")


if __name__ == "__main__":
    send_email_report()
