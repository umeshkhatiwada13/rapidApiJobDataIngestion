import sqlite3
import re
from collections import Counter


def analyze_job_skills(db_file="jobs.db"):
    """Reads job descriptions from SQLite, extracts tech skills, and prints market trends."""
    print("Analyzing job market descriptions for key skills...")

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Fetch all job descriptions
        cursor.execute("SELECT title, description FROM job_postings")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return

    if not rows:
        print("No job records found in the database to analyze.")
        return

    # Comprehensive skill vocabulary targeting senior Java / tech roles
    target_skills = [
        "java", "python", "spring boot", "postgresql", "sql",
        "docker", "kubernetes", "aws", "azure", "gcp",
        "react", "typescript", "golang", "graphql", "terraform", "ci/cd"
    ]

    skill_counter = Counter()
    role_count = len(rows)

    for title, description in rows:
        if not description:
            continue

        # Convert description to lowercase for case-insensitive matching
        desc_lower = description.lower()

        for skill in target_skills:
            # Use word boundaries (\b) to ensure exact skill matches (e.g., match 'go' or 'java')
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, desc_lower):
                skill_counter[skill] += 1

    # Print out the structured market intelligence report
    print(f"\n=== TECH MARKET SKILLS REPORT (Based on {role_count} Postings) ===")
    for skill, count in skill_counter.most_common():
        percentage = (count / role_count) * 100
        bar = "█" * int(percentage // 5)  # Visual bar graph representation
        print(f"{skill.upper():<12} | {count} jobs ({percentage:.0f}%) -> {bar}")

    print("=" * 65)


if __name__ == "__main__":
    analyze_job_skills()