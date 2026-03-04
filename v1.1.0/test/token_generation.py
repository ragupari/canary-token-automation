import requests
import csv
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
BASE_URL = "https://canarytokens.com"
API_ID = "d3aece8093b71007b5ccfedad91ebb11"
INPUT_CSV = "users_input.csv"    
OUTPUT_CSV = "users_token.csv"   
OUTPUT_DIR = "generated_tokens"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_request_session():
    session = requests.Session()
    retries = Retry(
        total=5, # Increased retries
        backoff_factor=2, # Wait longer between retries (2s, 4s, 8s...)
        status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def process_tokens():
    session = get_request_session()
    processed_data = {}

    # 1. Load existing progress if it exists (to allow resuming)
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_data[row['user_id']] = row

    # 2. Read the master input file
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    with open(INPUT_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        input_rows = list(reader)
        fieldnames = list(reader.fieldnames)
        if 'canary_link' not in fieldnames: fieldnames.append('canary_link')
        if 'generated_filename' not in fieldnames: fieldnames.append('generated_filename')

    print(f"Starting process. Total users: {len(input_rows)}")

    try:
        for row in input_rows:
            u_id = row['user_id']
            
            # SKIP if already successfully processed in a previous run
            if u_id in processed_data and processed_data[u_id]['canary_link'] not in ["ERROR", "FAILED", ""]:
                print(f"Skipping: {row['user_name']} (Already done)")
                continue

            print(f"Processing: {row['user_name']}...", end=" ", flush=True)
            
            base_filename = f"Salaries_Grade_V_and_Above_{u_id}.xlsx"
            row['generated_filename'] = base_filename
            memo_text = f"{u_id} | Name:{row['user_name']} | Email:{row['user_email']}"
            
            try:
                # Generate Token
                gen_url = f"{BASE_URL}/{API_ID}/generate"
                gen_res = session.post(gen_url, data={'email': row['assignee'], 'memo': memo_text, 'token_type': 'ms_excel'}, timeout=30)
                gen_res.raise_for_status()
                data = gen_res.json()
                
                t_id, a_token = data.get('token'), data.get('auth_token')
                
                # Download File
                file_res = session.get(f"{BASE_URL}/{API_ID}/download", params={'fmt': 'msexcel', 'auth': a_token, 'token': t_id}, timeout=30)
                file_res.raise_for_status()
                
                with open(os.path.join(OUTPUT_DIR, base_filename), 'wb') as f:
                    f.write(file_res.content)
                
                row['canary_link'] = f"{BASE_URL}/nest/manage/{a_token}/{t_id}"
                print("Success.")
                
            except Exception as e:
                print(f"Failed: {e}")
                row['canary_link'] = "FAILED"

            # Update the dictionary with current progress
            processed_data[u_id] = row
            
            # Save after EVERY successful user so we don't lose data
            with open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_data.values())
            
            time.sleep(3) # Increased delay to be safer with the API

    except KeyboardInterrupt:
        print("\nStopped by user.")
    
    print(f"Final results saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    process_tokens()