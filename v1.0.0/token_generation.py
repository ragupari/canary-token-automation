import requests
import csv
import os
import time
import zipfile
import shutil
import logging
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- CONFIGURATION ---
BASE_URL = "https://canarytokens.com"
API_ID = "d3aece8093b71007b5ccfedad91ebb11" 
INPUT_CSV = "users_input.csv"
OUTPUT_CSV = "users_token.csv"
OUTPUT_DIR = "generated_tokens"
COVER_IMAGE_PATH = "cover.png" 

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 1. RETRYABLE INJECTION LOGIC ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def inject_confidential_cover(file_path, image_path):
    """Injects a cover image with internal retries for file/IO issues."""
    tmp_dir = f"tmp_edit_{int(time.time() * 1000)}"
    
    if not os.path.exists(image_path):
        logging.error(f"Cover image {image_path} missing.")
        return False

    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
            
        # XML Namespaces
        CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
        REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
        DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
        A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
        R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

        # Content Types Registration
        ct_path = os.path.join(tmp_dir, '[Content_Types].xml')
        ct_tree = etree.parse(ct_path)
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        if not ct_tree.xpath(f"//ct:Default[@Extension='{ext}']", namespaces={'ct': CT_NS}):
            etree.SubElement(ct_tree.getroot(), f"{{{CT_NS}}}Default", Extension=ext, ContentType=f"image/{ext}")
            ct_tree.write(ct_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        # Move Image
        media_dir = os.path.join(tmp_dir, 'xl', 'media')
        os.makedirs(media_dir, exist_ok=True)
        target_img_name = f"image_cover.{ext}"
        shutil.copy(image_path, os.path.join(media_dir, target_img_name))

        # Update Drawing Relationships
        rel_path = os.path.join(tmp_dir, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
        rel_tree = etree.parse(rel_path)
        rel_root = rel_tree.getroot()
        existing_rids = [int(rid.replace('rId', '')) for rid in rel_root.xpath("//@Id") if rid.startswith('rId')]
        new_rid_int = (max(existing_rids) if existing_rids else 0) + 1
        new_rid = f"rId{new_rid_int}"
        
        etree.SubElement(rel_root, f"{{{REL_NS}}}Relationship", 
                         Id=new_rid, 
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                         Target=f"../media/{target_img_name}")
        rel_tree.write(rel_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        # Update Drawing XML
        draw_path = os.path.join(tmp_dir, 'xl', 'drawings', 'drawing1.xml')
        draw_tree = etree.parse(draw_path)
        draw_root = draw_tree.getroot()
        
        anchor = etree.SubElement(draw_root, f"{{{DRAW_NS}}}twoCellAnchor", editAs="absolute")
        f_pos = etree.SubElement(anchor, f"{{{DRAW_NS}}}from")
        for t, v in [("col", "0"), ("colOff", "0"), ("row", "0"), ("rowOff", "0")]:
            etree.SubElement(f_pos, f"{{{DRAW_NS}}}{t}").text = v
        t_pos = etree.SubElement(anchor, f"{{{DRAW_NS}}}to")
        for t, v in [("col", "15"), ("colOff", "0"), ("row", "40"), ("rowOff", "0")]:
            etree.SubElement(t_pos, f"{{{DRAW_NS}}}{t}").text = v

        pic = etree.SubElement(anchor, f"{{{DRAW_NS}}}pic")
        nv_pic = etree.SubElement(pic, f"{{{DRAW_NS}}}nvPicPr")
        etree.SubElement(nv_pic, f"{{{DRAW_NS}}}cNvPr", id=str(new_rid_int + 10), name="ConfidentialCover")
        nv_cnv = etree.SubElement(nv_pic, f"{{{DRAW_NS}}}cNvPicPr")
        etree.SubElement(nv_cnv, f"{{{A_NS}}}picLocks", noGrp="1", noMove="1", noResize="1", noSelect="1")

        blip_fill = etree.SubElement(pic, f"{{{DRAW_NS}}}blipFill")
        etree.SubElement(blip_fill, f"{{{A_NS}}}blip", {f"{{{R_NS}}}embed": new_rid})
        stretch = etree.SubElement(blip_fill, f"{{{A_NS}}}stretch")
        etree.SubElement(stretch, f"{{{A_NS}}}fillRect")
        
        sp_pr = etree.SubElement(pic, f"{{{DRAW_NS}}}spPr")
        etree.SubElement(sp_pr, f"{{{A_NS}}}prstGeom", prst="rect")
        etree.SubElement(anchor, f"{{{DRAW_NS}}}clientData")

        draw_tree.write(draw_path, xml_declaration=True, encoding='UTF-8')

        # Re-build Zip
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    new_zip.write(full_p, os.path.relpath(full_p, tmp_dir))
        return True

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

# --- 2. MAIN EXECUTION LOOP WITH RETRY ---
def get_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def generate_and_download(session, row):
    """Attempts to generate and download the token, retrying on API/Network failure."""
    u_id = row.get('user_id', 'unknown')
    email = row.get('assignee', '')
    
    # Generate
    res = session.post(f"{BASE_URL}/{API_ID}/generate", 
                       data={'email': email, 'memo': f"UID:{u_id}", 'token_type': 'ms_excel'}, 
                       timeout=30)
    res.raise_for_status()
    data = res.json()
    
    # Download
    f_res = session.get(f"{BASE_URL}/{API_ID}/download", 
                        params={'fmt': 'msexcel', 'auth': data['auth_token'], 'token': data['token']}, 
                        timeout=45)
    f_res.raise_for_status()
    return f_res.content, data

def process_tokens():
    session = get_session()
    
    if not os.path.exists(INPUT_CSV):
        logging.error(f"Input file {INPUT_CSV} missing.")
        return

    try:
        with open(INPUT_CSV, 'r') as f:
            reader = list(csv.DictReader(f))
            if not reader: return
            fieldnames = list(reader[0].keys())
            for col in ['canary_link', 'file_name']:
                if col not in fieldnames: fieldnames.append(col)

        logging.info(f"Generating {len(reader)} tokens...")

        for row in reader:
            u_id = row.get('user_id', 'unknown')
            u_name = row.get('user_name', 'unknown')
            file_name = f"Salaries_Grade_V_and_Above_{u_id}.xlsb" #Can change the name of the output file.
            file_path = os.path.join(OUTPUT_DIR, file_name)
            row['file_name'] = file_name

            print(f"[*] Token {u_id}: {u_name} Processing...", end=" ", flush=True)
            try:
                content, api_data = generate_and_download(session, row)
                
                with open(file_path, 'wb') as f:
                    f.write(content)

                if inject_confidential_cover(file_path, COVER_IMAGE_PATH):
                    row['canary_link'] = f"{BASE_URL}/nest/manage/{api_data['auth_token']}/{api_data['token']}"
                    print("Done.")
                else:
                    row['canary_link'] = "INJECTION_FAILED"
            except Exception as e:
                logging.error(f"Final failure for UID {u_id}: {e}")
                row['canary_link'] = "FAILED_AFTER_RETRIES"
                print("Failed.")

            with open(OUTPUT_CSV, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reader)
            
            time.sleep(1)

    except Exception as e:
        logging.critical(f"Critical error: {e}")

if __name__ == "__main__":
    process_tokens()