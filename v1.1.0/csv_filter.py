import csv
import json

INPUT_CSV = "live_demo/report.csv"
EMAIL_FILES = [
    "live_demo/demo_users.csv",
    "users_token_01.csv",
        "users_token_02.csv",
            "users_token_03.csv",
                "users_token_04.csv",
                    "users_token_05.csv",
]
OUTPUT_CSV = "live_demo/final_report.csv"

# Load all email files into one lookup (first match wins)
email_map = {}

for email_file in EMAIL_FILES:
    with open(email_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row["user_id"]
            if user_id not in email_map:
                email_map[user_id] = row["user_email"]

with open(INPUT_CSV, newline="", encoding="utf-8") as infile, \
     open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as outfile:

    reader = csv.DictReader(infile)
    fieldnames = ["email", "no_of_times", "details"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        if row["triggered"].lower() != "true":
            continue

        user_id = row["user_id"]
        email = email_map.get(user_id)
        if not email:
            continue

        try:
            details_list = json.loads(row["details"])
        except json.JSONDecodeError:
            continue

        indexed_details = {
            str(i + 1): {
                "time": entry.get("time"),
                "ip": entry.get("ip")
            }
            for i, entry in enumerate(details_list)
        }

        writer.writerow({
            "email": email,
            "no_of_times": len(details_list),
            "details": json.dumps(indexed_details, ensure_ascii=False)
        })

print("Final CSV created:", OUTPUT_CSV)
