import requests
import csv
import os
import time

# Configuration
BASE_URL = "https://canarytokens.org"
API_ID = "d3aece8093b71007b5ccfedad91ebb11"
INPUT_CSV = "users_output.csv"
OUTPUT_DIR = "generated_tokens"  # Files will be stored here

# Ensure the directory exists before starting
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_and_download_token(admin_email, memo, user_name):
    gen_url = f"{BASE_URL}/{API_ID}/generate"
    payload = {
        'email': admin_email, # Alert sent to the assignee/admin
        'memo': memo,         # Specific user tracking info
        'token_type': 'ms_excel'
    }
    
    try:
        # 1. Request Token Generation
        response = requests.post(gen_url, data=payload)
        response.raise_for_status()
        data = response.json()
        
        token_id = data.get('token')
        auth_token = data.get('auth_token')
        
        # 2. Request File Download
        download_params = {
            'fmt': 'msexcel',
            'auth': auth_token,
            'token': token_id
        }
        download_url = f"{BASE_URL}/{API_ID}/download"
        
        file_res = requests.get(download_url, params=download_params)
        file_res.raise_for_status()
        
        # 3. Save inside the specified folder
        file_path = os.path.join(OUTPUT_DIR, f"canary_{user_name}.xlsx")
        
        with open(file_path, 'wb') as f:
            f.write(file_res.content)
            
        print(f"[SUCCESS] Saved to {file_path} (Alerts to: {admin_email})")
        
    except Exception as e:
        print(f"[ERROR] Failed for {user_name}: {e}")

def run_batch():
    # Expects columns: user_id, user_name, user_email, assignee
    with open(INPUT_CSV, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Construct the exact memo format requested
            memo_text = f"{row['user_id']} | Name:{row['user_name']} | Email:{row['user_email']}"
            
            # Pass the admin email from 'assignee' column and user info
            generate_and_download_token(row['assignee'], memo_text, row['user_name'])
            
            # Sleep to avoid rate limiting
            time.sleep(1)

if __name__ == "__main__":
    run_batch()