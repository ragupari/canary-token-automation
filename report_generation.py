import requests
import csv
import os
import time
import re
import json
import logging
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- CONFIGURATION ---
INPUT_CSV = "users_token.csv"
REPORT_CSV = "triggered_report.csv"
API_ID = "d3aece8093b71007b5ccfedad91ebb11"
NETWORK_TIMEOUT = 15  # Increased timeout for stability

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- 1. ROBUST SESSION SETUP ---
def get_audit_session():
    """Configures a requests session with standard HTTP-level retries."""
    s = requests.Session()
    # Retries for common server-side errors (500, 502, 503, 504)
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

# --- 2. RETRYABLE API AUDIT LOGIC ---
@retry(
    stop=stop_after_attempt(4), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout)),
    reraise=True
)
def fetch_token_status(session, api_url):
    """Fetches token status with exponential backoff on network failure."""
    response = session.get(api_url, timeout=NETWORK_TIMEOUT)
    response.raise_for_status()
    return response.json()

# --- 3. MAIN AUDIT PROCESS ---
def audit_tokens():
    session = get_audit_session()
    results = []
    
    if not os.path.exists(INPUT_CSV):
        logging.error(f"Input file {INPUT_CSV} not found.")
        return

    try:
        with open(INPUT_CSV, mode='r', encoding='utf-8') as file:
            reader = list(csv.DictReader(file))
            if not reader:
                logging.error("Input CSV is empty.")
                return
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return

    logging.info(f"Auditing {len(reader)} tokens via Canary API...")

    for row in reader:
        u_id = row.get('user_id', 'Unknown')
        u_name = row.get('user_name', 'Unknown')
        manage_link = row.get('canary_link', '')
        
        # Skip invalid entries
        if not manage_link or manage_link in ["ERROR", "FAILED", "INJECTION_FAILED"]:
            logging.warning(f"Skipping {u_name}: No valid canary link.")
            continue

        # Extract tokens from URL using Regex
        match = re.search(r'manage/([^/]+)/([^/]+)', manage_link)
        if not match:
            logging.warning(f"Skipping {u_name}: Invalid link format ({manage_link})")
            continue
            
        auth_token = match.group(1)
        token_id = match.group(2)
        api_url = f"https://canarytokens.com/{API_ID}/manage?auth={auth_token}&token={token_id}"

        print(f"[*] Auditing {u_name}...", end=" ", flush=True)
        
        try:
            data = fetch_token_status(session, api_url)
            
            # Extract and sort hits
            hits = data.get('canarydrop', {}).get('triggered_details', {}).get('hits', [])
            hits.sort(key=lambda x: x.get('time_of_hit', 0))
            
            hit_details = []
            last_seen_per_ip = {} 

            for hit in hits:
                raw_time = hit.get('time_of_hit')
                ip_addr = hit.get('src_ip', 'N/A')
                
                if raw_time is None: continue

                # Logic to record unique attempts (10-second gap per IP)
                should_record = False
                if ip_addr not in last_seen_per_ip:
                    should_record = True
                else:
                    if abs(raw_time - last_seen_per_ip[ip_addr]) > 10:
                        should_record = True

                if should_record:
                    last_seen_per_ip[ip_addr] = raw_time
                    fmt_time = datetime.fromtimestamp(raw_time).strftime('%Y-%m-%d %H:%M:%S')
                    hit_details.append({"time": fmt_time, "ip": ip_addr})
            
            triggered_status = "true" if hit_details else "false"
            results.append({
                'user_id': u_id,
                'user_name': u_name,
                'triggered': triggered_status,
                'details': json.dumps(hit_details)
            })
            print(f"Status: {triggered_status} ({len(hit_details)} hits)")

        except Exception as e:
            logging.error(f"\nFinal API failure for {u_name}: {e}")
            results.append({
                'user_id': u_id, 'user_name': u_name, 'triggered': "AUDIT_ERROR", 'details': "[]"
            })
            
        # Polite delay to avoid API rate limiting
        time.sleep(0.5)

    # Save Final Report
    try:
        with open(REPORT_CSV, mode='w', encoding='utf-8', newline='') as file:
            fieldnames = ['user_id', 'user_name', 'triggered', 'details']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Audit complete! Results saved to {REPORT_CSV}")
    except Exception as e:
        logging.error(f"Failed to save report: {e}")

if __name__ == "__main__":
    audit_tokens()