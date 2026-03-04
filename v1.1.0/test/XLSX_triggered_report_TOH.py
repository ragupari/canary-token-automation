import requests
import csv
import time
import re
import json
from datetime import datetime

# Configuration
INPUT_CSV = "users_token_xlsx.csv"
REPORT_CSV = "triggered_report_xlsx.csv"
API_ID = "d3aece8093b71007b5ccfedad91ebb11"
NETWORK_TIMEOUT = 10  # Seconds to wait for a response

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

        match = re.search(r'manage/([^/]+)/([^/]+)', manage_link)
        if not match:
            print(f"Skipping {u_name}: Invalid link format.")
            continue
            
        auth_token = match.group(1)
        token_id = match.group(2)
        api_url = f"https://canarytokens.com/{API_ID}/manage?auth={auth_token}&token={token_id}"

        print(f"Auditing {u_name}...", end=" ")
        
        try:
            # Added timeout to handle network delays
            response = requests.get(api_url, timeout=NETWORK_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            hits = data.get('canarydrop', {}).get('triggered_details', {}).get('hits', [])
            hits.sort(key=lambda x: x.get('time_of_hit', 0))
            
            triggered_status = "true" if len(hits) > 0 else "false"
            
            hit_details = []
            last_seen_per_ip = {} 

            for hit in hits:
                current_raw_time = hit.get('time_of_hit')
                ip_address = hit.get('src_ip', 'N/A')
                
                if current_raw_time is None:
                    continue

                should_record = False
                if ip_address not in last_seen_per_ip:
                    should_record = True
                else:
                    # 10 second tolerance logic
                    time_diff = abs(current_raw_time - last_seen_per_ip[ip_address])
                    if time_diff > 10:
                        should_record = True

                if should_record:
                    last_seen_per_ip[ip_address] = current_raw_time
                    formatted_time = datetime.fromtimestamp(current_raw_time).strftime('%Y-%m-%d %H:%M:%S')
                    
                    hit_details.append({
                        "time": formatted_time,
                        "ip": ip_address
                    })
            
            results.append({
                'user_id': u_id,
                'user_name': u_name,
                'triggered': triggered_status,
                'details': json.dumps(hit_details)
            })
            print(f"Status: {triggered_status} ({len(hit_details)} unique attempts)")

        except requests.exceptions.Timeout:
            print("Error: Request timed out due to network delay.")
            results.append({
                'user_id': u_id, 'user_name': u_name, 'triggered': "TIMEOUT", 'details': "[]"
            })
        except requests.exceptions.ConnectionError:
            print("Error: Failed to connect to the server.")
            results.append({
                'user_id': u_id, 'user_name': u_name, 'triggered': "CONN_ERROR", 'details': "[]"
            })
        except Exception as e:
            print(f"API Error: {e}")
            results.append({
                'user_id': u_id, 'user_name': u_name, 'triggered': "ERROR", 'details': "[]"
            })
            
        time.sleep(0.5)

    with open(REPORT_CSV, mode='w', encoding='utf-8', newline='') as file:
        fieldnames = ['user_id', 'user_name', 'triggered', 'details']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nAudit complete! Results saved to {REPORT_CSV}")

if __name__ == "__main__":
    audit_tokens()