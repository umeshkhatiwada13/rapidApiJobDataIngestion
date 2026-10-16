import sqlite3

def view_jobs():
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, company, location, posted_date FROM job_postings")
    rows = cursor.fetchall()

    print(f"\n--- Total Jobs in SQLite DB: {len(rows)} ---\n")
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Company: {row[2]}")
        print(f"Location: {row[3]}")
        print(f"Posted: {row[4]}")
        print("-" * 50)

    conn.close()

if __name__ == "__main__":
    view_jobs()