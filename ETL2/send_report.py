import os
import sqlite3
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
DB_FILE = "jobs_2.db"


def run_deep_analytics():
    print("🔍 Inspecting database and running deep analytics on jobs_2.db...\n")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check column names in active_jobs table dynamically
        cursor.execute("PRAGMA table_info(active_jobs);")
        columns = [col[1] for col in cursor.fetchall()]

        # Fetch total jobs
        cursor.execute("SELECT COUNT(*) FROM active_jobs")
        total_jobs = cursor.fetchone()[0]

        if total_jobs == 0:
            print("No records found in database. Skipping reporting.")
            conn.close()
            return

        # Fetch all records
        cursor.execute("SELECT * FROM active_jobs")
        rows = cursor.fetchall()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        return

    # Map column index dynamically based on actual schema
    col_map = {name: idx for idx, name in enumerate(columns)}

    skill_counter = Counter()
    city_counter = Counter()
    exp_counter = Counter()
    work_arr_counter = Counter()
    processed_jobs = []

    for row in rows:
        title = row[col_map.get('title', 1)] if 'title' in col_map else "Unknown Title"
        org = row[col_map.get('organization', 2)] if 'organization' in col_map else "Unknown Organization"
        loc = row[col_map.get('location', 3)] if 'location' in col_map else "Unknown Location"
        skills_str = row[col_map.get('skills', 4)] if 'skills' in col_map else ""

        # Flexible checks for optional metadata columns
        exp_lvl = row[col_map['experience_level']] if 'experience_level' in col_map and row[
            col_map['experience_level']] else "Not Specified"
        work_arr = row[col_map['work_arrangement']] if 'work_arrangement' in col_map and row[
            col_map['work_arrangement']] else "Not Specified"

        # Salary parsing safety check
        salary = "Not Listed"
        for col_name in ['salary', 'max_salary', 'compensation', 'ai_salary_max_value']:
            if col_name in col_map and row[col_map[col_name]]:
                salary = row[col_map[col_name]]
                break

        # 1. Process Skills
        if skills_str:
            for skill in [s.strip() for s in skills_str.split(",")]:
                if skill:
                    skill_counter[skill] += 1

        # 2. Process Cities
        if loc and loc != "Unknown Location":
            city = loc.split(",")[0].strip()
            city_counter[city] += 1

        # 3. Process Experience Levels
        exp_counter[exp_lvl] += 1

        # 4. Process Work Arrangements
        work_arr_counter[work_arr] += 1

        # Track job details for top roles
        processed_jobs.append({
            "title": title or "Unknown Title",
            "organization": org or "Unknown Organization",
            "location": loc or "Unknown Location",
            "salary": salary
        })

    # --- CLI CONSOLE REPORT ---
    print("=" * 72)
    print("                🚀 EXECUTIVE JOB MARKET INTELLIGENCE REPORT                ")
    print("=" * 72)
    print(f"  📌 Dataset Overview : {total_jobs} Active Postings Analyzed")
    print(f"  🗄️  Source Database  : {DB_FILE}")
    print("=" * 72 + "\n")

    top_skills = skill_counter.most_common(5)
    top_cities = city_counter.most_common(5)
    top_exp = exp_counter.most_common(5)
    top_work = work_arr_counter.most_common(5)
    top_jobs = processed_jobs[:5]

    print("🔥 1. Top 5 In-Demand Skills:")
    for skill, count in top_skills:
        pct = (count / total_jobs) * 100
        bar = "█" * int(pct // 5)
        print(f"   • {skill:<25} -> {count:2d} postings ({pct:5.1f}%) {bar}")
    print("-" * 72)

    print("\n🏙️  2. Top 5 Hiring Cities:")
    for city, count in top_cities:
        pct = (count / total_jobs) * 100
        bar = "█" * int(pct // 5)
        print(f"   • {city:<25} -> {count:2d} postings ({pct:5.1f}%) {bar}")
    print("-" * 72)

    print("\n💰 3. Top 5 Featured / High-Value Openings:")
    for idx, job in enumerate(top_jobs, 1):
        print(f"   {idx}. {job['title']}")
        print(f"      🏢 Company: {job['organization']}  |  📍 Location: {job['location']}")
        print(f"      💵 Compensation: {job['salary']}\n")
    print("-" * 72)

    print("\n📈 4. Top Experience Levels Required:")
    for exp, count in top_exp:
        pct = (count / total_jobs) * 100
        print(f"   • {exp:<25} -> {count:2d} postings ({pct:5.1f}%)")
    print("-" * 72)

    print("\n🏠 5. Top Work Arrangements:")
    for arr, count in top_work:
        pct = (count / total_jobs) * 100
        print(f"   • {arr:<25} -> {count:2d} postings ({pct:5.1f}%)")
    print("=" * 72)

    # --- BUILD HTML EMAIL REPORT ---
    print("\n📧 Compiling and sending mobile-friendly executive HTML email...")

    skills_html = "".join([
        f"<tr><td style='padding:6px 0; font-size:13px;'><b>{s}</b></td><td style='text-align:right; color:#555;'>{c} jobs ({c / total_jobs * 100:.1f}%)</td></tr>"
        for s, c in top_skills
    ])

    cities_html = "".join([
        f"<tr><td style='padding:6px 0; font-size:13px;'><b>{city}</b></td><td style='text-align:right; color:#555;'>{c} jobs ({c / total_jobs * 100:.1f}%)</td></tr>"
        for city, c in top_cities
    ])

    jobs_html = "".join([
        f"<li style='margin-bottom:10px;'><b>{j['title']}</b> at <i>{j['organization']}</i><br><span style='font-size:12px; color:#666;'>📍 {j['location']} | 💵 {j['salary']}</span></li>"
        for j in top_jobs
    ])

    exp_html = "".join([
        f"<li><b>{e}</b>: {c} postings</li>" for e, c in top_exp
    ])

    work_html = "".join([
        f"<li><b>{w}</b>: {c} postings</li>" for w, c in top_work
    ])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; background-color: #f4f6f8; margin: 0; padding: 0; }}
            .wrapper {{ width: 100%; background-color: #f4f6f8; padding: 20px 0; }}
            .container {{ max-width: 600px; width: 100%; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #e1e4e8; overflow: hidden; }}
            .content {{ padding: 25px; }}
            h2 {{ color: #0366d6; font-size: 22px; margin-top: 0; }}
            h3 {{ color: #24292e; font-size: 15px; border-bottom: 2px solid #eaecef; padding-bottom: 6px; margin-top: 20px; }}
            .metric-box {{ background: #f6f8fa; padding: 12px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #0366d6; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            ul {{ padding-left: 18px; margin: 8px 0; font-size: 13px; }}
            .footer {{ font-size: 11px; color: #6a737d; text-align: center; margin-top: 25px; border-top: 1px solid #eaecef; padding-top: 12px; }}
            @media only screen and (max-width: 480px) {{ .content {{ padding: 15px !important; }} }}
        </style>
    </head>
    <body>
        <center class="wrapper">
            <table class="container" role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td class="content">
                        <h2>🚀 Market Intelligence Briefing</h2>
                        <p style="font-size: 13px; color: #586069;">Automated deep-insights analysis extracted from your active job database.</p>

                        <div class="metric-box">
                            <b>Total Postings Analyzed:</b> {total_jobs}
                        </div>

                        <h3>🔥 Top 5 In-Demand Skills</h3>
                        <table>{skills_html}</table>

                        <h3>🏙️ Top 5 Hiring Cities</h3>
                        <table>{cities_html}</table>

                        <h3>💰 Top Featured Openings</h3>
                        <ul>{jobs_html}</ul>

                        <h3>📈 Experience Levels Required</h3>
                        <ul>{exp_html}</ul>

                        <h3>🏠 Work Arrangements</h3>
                        <ul>{work_html}</ul>

                        <div class="footer">
                            Generated automatically by your Python Data Pipeline & NLP Engine.
                        </div>
                    </td>
                </tr>
            </table>
        </center>
    </body>
    </html>
    """

    headers = {
        "Authorization": f"Bearer {EMAIL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "onboarding@resend.dev",
        "to": RECEIVER_EMAIL,
        "subject": f"📊 Deep Market Intelligence & Analytics Report ({total_jobs} Roles)",
        "html": html_content
    }

    response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)

    if response.status_code in [200, 201]:
        print(f"✅ Successfully dispatched executive email report to {RECEIVER_EMAIL}!")
    else:
        print(f"❌ Failed to send email: {response.text}")


if __name__ == "__main__":
    run_deep_analytics()