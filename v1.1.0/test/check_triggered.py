import requests
import csv
import time
import re

# Configuration
INPUT_CSV = "users_token.csv"
REPORT_CSV = "triggered_report.csv"
# The API ID from your logs
API_ID = "d3aece8093b71007b5ccfedad91ebb11"

def audit_tokens():
    results = []
    
    try:
        with open(INPUT_CSV, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: {INPUT_CSV} not found.")
        return

    print(f"Auditing {len(rows)} tokens via API...")

    for row in rows:
        u_id = row.get('user_id')
        u_name = row.get('user_name')
        manage_link = row.get('canary_link')
        
        if not manage_link or manage_link == "ERROR":
            continue

        # Convert web link to API link using Regex
        # Pattern: .../manage/AUTH/TOKEN -> .../manage?auth=AUTH&token=TOKEN
        match = re.search(r'manage/([^/]+)/([^/]+)', manage_link)
        if not match:
            print(f"Skipping {u_name}: Invalid link format.")
            continue
            
        auth_token = match.group(1)
        token_id = match.group(2)
        
        # Construct the direct API URL
        api_url = f"https://canarytokens.com/{API_ID}/manage?auth={auth_token}&token={token_id}"

        print(f"Auditing {u_name}...", end=" ")
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            # Check the "hits" list in the JSON structure
            hits = data.get('canarydrop', {}).get('triggered_details', {}).get('hits', [])
            
            if len(hits) == 0:
                triggered_status = "false"
            else:
                triggered_status = "true"
            
            results.append({
                'user_id': u_id,
                'user_name': u_name,
                'triggered': triggered_status
            })
            print(f"Status: {triggered_status}")

        except Exception as e:
            print(f"API Error: {e}")
            results.append({
                'user_id': u_id, 'user_name': u_name, 'triggered': "ERROR"
            })
            
        time.sleep(0.5)

    # Save summary
    with open(REPORT_CSV, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['user_id', 'user_name', 'triggered'])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nAudit complete! Results saved to {REPORT_CSV}")

if __name__ == "__main__":
    audit_tokens()