import requests
import csv
import os
import time
import zipfile
import shutil
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://canarytokens.com"
API_ID = "d3aece8093b71007b5ccfedad91ebb11" 
INPUT_CSV = "users_input.csv"
OUTPUT_CSV = "users_token.csv"
OUTPUT_DIR = "generated_tokens"
COVER_IMAGE_PATH = "cover.png" 

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 1. ROBUST EXCEL INJECTION LOGIC ---
def inject_confidential_cover(file_path, image_path):
    """Injects a cover image while ensuring Excel's internal XML structure remains valid."""
    tmp_dir = f"tmp_edit_{int(time.time())}"
    
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)

    # Namespaces
    CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
    REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
    DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
    A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
    R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    # A. Register the image extension in [Content_Types].xml
    ct_path = os.path.join(tmp_dir, '[Content_Types].xml')
    ct_tree = etree.parse(ct_path)
    ext = os.path.splitext(image_path)[1].lower().replace('.', '')
    if not ct_tree.xpath(f"//ct:Default[@Extension='{ext}']", namespaces={'ct': CT_NS}):
        etree.SubElement(ct_tree.getroot(), f"{{{CT_NS}}}Default", Extension=ext, ContentType=f"image/{ext}")
        ct_tree.write(ct_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # B. Move the image into the media folder
    media_dir = os.path.join(tmp_dir, 'xl', 'media')
    if not os.path.exists(media_dir): os.makedirs(media_dir)
    target_img_name = f"image_cover.{ext}"
    shutil.copy(image_path, os.path.join(media_dir, target_img_name))

    # C. Update the Relationship file
    rel_path = os.path.join(tmp_dir, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
    rel_tree = etree.parse(rel_path)
    rel_root = rel_tree.getroot()
    
    # Calculate a new safe Relationship ID
    existing_rids = [int(rid.replace('rId', '')) for rid in rel_root.xpath("//@Id")]
    new_rid_int = (max(existing_rids) if existing_rids else 0) + 1
    new_rid = f"rId{new_rid_int}"
    
    etree.SubElement(rel_root, f"{{{REL_NS}}}Relationship", 
                     Id=new_rid, 
                     Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                     Target=f"../media/{target_img_name}")
    rel_tree.write(rel_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # D. Update drawing1.xml to display the image
    draw_path = os.path.join(tmp_dir, 'xl', 'drawings', 'drawing1.xml')
    draw_tree = etree.parse(draw_path)
    draw_root = draw_tree.getroot()
    
    # Create the picture anchor
    anchor = etree.SubElement(draw_root, f"{{{DRAW_NS}}}twoCellAnchor", editAs="absolute")
    
    # Position: Fill the whole screen (Roughly)
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
    etree.SubElement(blip_fill, f"{{{A_NS}}}stretch", {}, etree.Element(f"{{{A_NS}}}fillRect"))
    
    etree.SubElement(pic, f"{{{DRAW_NS}}}spPr", {}, etree.Element(f"{{{A_NS}}}prstGeom", prst="rect"))
    etree.SubElement(anchor, f"{{{DRAW_NS}}}clientData")

    draw_tree.write(draw_path, xml_declaration=True, encoding='UTF-8')

    # E. Re-zip the file back into an XLSX
    with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                # Ensure the path inside the zip is relative to the tmp_dir
                new_zip.write(full_path, os.path.relpath(full_path, tmp_dir))
    
    shutil.rmtree(tmp_dir)

# --- 2. MAIN EXECUTION LOOP ---
def get_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def process_tokens():
    session = get_session()
    processed_ids = []

    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} missing.")
        return

    with open(INPUT_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = list(reader[0].keys())
        if 'canary_link' not in fieldnames: fieldnames.append('canary_link')

    print(f"Starting. Generating {len(reader)} tokens...")

    for row in reader:
        u_id = row['user_id']
        file_name = f"Confidential_Salary_Report_{u_id}.xlsx"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        print(f"User {u_id}: Downloading...", end=" ", flush=True)
        try:
            # Generate
            res = session.post(f"{BASE_URL}/{API_ID}/generate", 
                               data={'email': row['assignee'], 'memo': f"UID:{u_id}", 'token_type': 'ms_excel'})
            data = res.json()
            
            # Download
            f_res = session.get(f"{BASE_URL}/{API_ID}/download", 
                                params={'fmt': 'msexcel', 'auth': data['auth_token'], 'token': data['token']})
            
            with open(file_path, 'wb') as f:
                f.write(f_res.content)

            # Inject
            inject_confidential_cover(file_path, COVER_IMAGE_PATH)
            row['canary_link'] = f"{BASE_URL}/nest/manage/{data['auth_token']}/{data['token']}"
            print("Done.")

        except Exception as e:
            print(f"Failed: {e}")
            row['canary_link'] = "FAILED"

        # Save progress immediately
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)
        
        time.sleep(2)

if __name__ == "__main__":
    process_tokens()