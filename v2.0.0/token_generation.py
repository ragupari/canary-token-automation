import requests
import csv
import os
import time
import zipfile
import shutil
import logging
import sys
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime

# ─────────────────────────────────────────────
#  TERMINAL UI LAYER  (purely cosmetic)
# ─────────────────────────────────────────────

RESET      = "\033[0m"
BOLD       = "\033[1m"
DIM        = "\033[2m"
FG_WHITE   = "\033[97m"
FG_GRAY    = "\033[90m"
FG_CYAN    = "\033[96m"
FG_GREEN   = "\033[92m"
FG_YELLOW  = "\033[93m"
FG_RED     = "\033[91m"
FG_BLUE    = "\033[94m"

WIDTH = 72

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def banner():
    sys.stdout.write("\033[2J\033[H")
    print()
    print(FG_CYAN + BOLD + "┌" + "─" * (WIDTH - 2) + "┐" + RESET)
    title = "CANARY TOKEN GENERATOR"
    sub   = "Excel / MS-Office Deployment Pipeline"
    pt = (WIDTH - 2 - len(title)) // 2
    ps = (WIDTH - 2 - len(sub))   // 2
    print(FG_CYAN + BOLD + "│" + " " * pt + FG_WHITE + title + " " * (WIDTH - 2 - pt - len(title)) + FG_CYAN + "│" + RESET)
    print(FG_CYAN + BOLD + "│" + " " * ps + FG_GRAY  + sub   + " " * (WIDTH - 2 - ps - len(sub))   + FG_CYAN + "│" + RESET)
    print(FG_CYAN + BOLD + "└" + "─" * (WIDTH - 2) + "┘" + RESET)
    print()

def section(label: str):
    tag   = f"  {label}  "
    left  = 2
    right = WIDTH - left - len(tag)
    print()
    print(FG_GRAY + "─" * left + FG_CYAN + BOLD + tag + RESET + FG_GRAY + "─" * right + RESET)

def log_info(msg):
    print(f"  {FG_GRAY}{_ts()}{RESET}  {FG_BLUE}·{RESET}  {FG_WHITE}{msg}{RESET}")

def log_ok(msg):
    print(f"  {FG_GRAY}{_ts()}{RESET}  {FG_GREEN}✔{RESET}  {FG_WHITE}{msg}{RESET}")

def log_warn(msg):
    print(f"  {FG_GRAY}{_ts()}{RESET}  {FG_YELLOW}⚠{RESET}  {FG_YELLOW}{msg}{RESET}")

def log_err(msg):
    print(f"  {FG_GRAY}{_ts()}{RESET}  {FG_RED}✖{RESET}  {FG_RED}{msg}{RESET}")

def log_crit(msg):
    print(f"  {FG_GRAY}{_ts()}{RESET}  {FG_RED}{BOLD}☠{RESET}  {FG_RED}{BOLD}{msg}{RESET}")

def progress_bar(current, total, width=36):
    pct    = current / total if total else 0
    filled = int(width * pct)
    bar    = FG_GREEN + "█" * filled + FG_GRAY + "░" * (width - filled) + RESET
    return f"[{bar}] {FG_WHITE}{current:>3}/{total}{RESET}"

def job_line(uid, name, current, total, status="working"):
    icons = {
        "working": FG_YELLOW + "⟳" + RESET,
        "done":    FG_GREEN  + "✔" + RESET,
        "failed":  FG_RED    + "✖" + RESET,
        "inject":  FG_CYAN   + "⊕" + RESET,
    }
    icon  = icons.get(status, "·")
    pb    = progress_bar(current, total)
    label = f"{FG_CYAN}{uid:<12}{RESET}{FG_GRAY}│{RESET} {FG_WHITE}{name:<22}{RESET}"
    print(f"  {icon}  {label}  {pb}")

def summary_table(results):
    section("SESSION SUMMARY")
    print()
    ok    = sum(1 for r in results if r.get('canary_link', '') not in ("INJECTION_FAILED", "FAILED_AFTER_RETRIES"))
    fail  = len(results) - ok
    cw    = [14, 28, WIDTH - 14 - 28 - 8]
    print(f"  {FG_CYAN}{BOLD}{'USER ID':<{cw[0]}}{'USER NAME':<{cw[1]}}{'STATUS':<{cw[2]}}{RESET}")
    print("  " + FG_GRAY + "─" * (WIDTH - 4) + RESET)
    for r in results:
        uid   = r.get('user_id',   '—')
        uname = r.get('user_name', '—')
        link  = r.get('canary_link', '')
        if link in ("INJECTION_FAILED", "FAILED_AFTER_RETRIES"):
            st = FG_RED + link + RESET
        else:
            st = FG_GREEN + "DEPLOYED" + RESET
        print(f"  {FG_WHITE}{uid:<{cw[0]}}{FG_GRAY}{uname:<{cw[1]}}{RESET}{st}")
    print()
    print("  " + FG_GRAY + "─" * (WIDTH - 4) + RESET)
    print(f"  {FG_GREEN}Deployed : {ok}{RESET}   {FG_RED}Failed : {fail}{RESET}   {FG_WHITE}Total : {len(results)}{RESET}")
    print()

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
BASE_URL         = "https://canarytokens.com"
API_ID           = "d3aece8093b71007b5ccfedad91ebb11"
INPUT_CSV        = "live_demo/demo_users.csv"
OUTPUT_CSV       = "live_demo/demo_user_token.csv"
OUTPUT_DIR       = "live_demo/generated_tokens"
COVER_IMAGE_PATH = "cover.png"

logging.basicConfig(level=logging.CRITICAL)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
#  1. RETRYABLE INJECTION LOGIC  (unchanged)
# ─────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def inject_confidential_cover(file_path, image_path):
    tmp_dir = f"tmp_edit_{int(time.time() * 1000)}"
    if not os.path.exists(image_path):
        log_warn(f"Cover image not found: {image_path}")
        return False
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        CT_NS   = "http://schemas.openxmlformats.org/package/2006/content-types"
        REL_NS  = "http://schemas.openxmlformats.org/package/2006/relationships"
        DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
        A_NS    = "http://schemas.openxmlformats.org/drawingml/2006/main"
        R_NS    = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

        ct_path = os.path.join(tmp_dir, '[Content_Types].xml')
        ct_tree = etree.parse(ct_path)
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        if not ct_tree.xpath(f"//ct:Default[@Extension='{ext}']", namespaces={'ct': CT_NS}):
            etree.SubElement(ct_tree.getroot(), f"{{{CT_NS}}}Default",
                             Extension=ext, ContentType=f"image/{ext}")
            ct_tree.write(ct_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        media_dir = os.path.join(tmp_dir, 'xl', 'media')
        os.makedirs(media_dir, exist_ok=True)
        target_img_name = f"image_cover.{ext}"
        shutil.copy(image_path, os.path.join(media_dir, target_img_name))

        rel_path = os.path.join(tmp_dir, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
        rel_tree = etree.parse(rel_path)
        rel_root = rel_tree.getroot()
        existing_rids = [int(rid.replace('rId', ''))
                         for rid in rel_root.xpath("//@Id") if rid.startswith('rId')]
        new_rid_int = (max(existing_rids) if existing_rids else 0) + 1
        new_rid = f"rId{new_rid_int}"
        etree.SubElement(rel_root, f"{{{REL_NS}}}Relationship",
                         Id=new_rid,
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                         Target=f"../media/{target_img_name}")
        rel_tree.write(rel_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        draw_path = os.path.join(tmp_dir, 'xl', 'drawings', 'drawing1.xml')
        draw_tree = etree.parse(draw_path)
        draw_root = draw_tree.getroot()

        anchor = etree.SubElement(draw_root, f"{{{DRAW_NS}}}twoCellAnchor", editAs="absolute")
        f_pos  = etree.SubElement(anchor, f"{{{DRAW_NS}}}from")
        for t, v in [("col","0"),("colOff","0"),("row","0"),("rowOff","0")]:
            etree.SubElement(f_pos, f"{{{DRAW_NS}}}{t}").text = v
        t_pos  = etree.SubElement(anchor, f"{{{DRAW_NS}}}to")
        for t, v in [("col","15"),("colOff","0"),("row","40"),("rowOff","0")]:
            etree.SubElement(t_pos, f"{{{DRAW_NS}}}{t}").text = v

        pic    = etree.SubElement(anchor, f"{{{DRAW_NS}}}pic")
        nv_pic = etree.SubElement(pic,    f"{{{DRAW_NS}}}nvPicPr")
        etree.SubElement(nv_pic, f"{{{DRAW_NS}}}cNvPr",
                         id=str(new_rid_int + 10), name="ConfidentialCover")
        nv_cnv = etree.SubElement(nv_pic, f"{{{DRAW_NS}}}cNvPicPr")
        etree.SubElement(nv_cnv, f"{{{A_NS}}}picLocks",
                         noGrp="1", noMove="1", noResize="1", noSelect="1")

        blip_fill = etree.SubElement(pic, f"{{{DRAW_NS}}}blipFill")
        etree.SubElement(blip_fill, f"{{{A_NS}}}blip", {f"{{{R_NS}}}embed": new_rid})
        stretch = etree.SubElement(blip_fill, f"{{{A_NS}}}stretch")
        etree.SubElement(stretch, f"{{{A_NS}}}fillRect")

        sp_pr = etree.SubElement(pic, f"{{{DRAW_NS}}}spPr")
        etree.SubElement(sp_pr, f"{{{A_NS}}}prstGeom", prst="rect")
        etree.SubElement(anchor, f"{{{DRAW_NS}}}clientData")

        draw_tree.write(draw_path, xml_declaration=True, encoding='UTF-8')

        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    new_zip.write(full_p, os.path.relpath(full_p, tmp_dir))
        return True

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

# ─────────────────────────────────────────────
#  2. NETWORK SESSION  (unchanged)
# ─────────────────────────────────────────────
def get_session():
    s       = requests.Session()
    retries = Retry(total=5, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def generate_and_download(session, row):
    u_id  = row.get('user_id',  'unknown')
    email = row.get('assignee', '')

    res = session.post(f"{BASE_URL}/{API_ID}/generate",
                       data={'email': email, 'memo': f"UID:{u_id}", 'token_type': 'ms_excel'},
                       timeout=30)
    res.raise_for_status()
    data = res.json()

    f_res = session.get(f"{BASE_URL}/{API_ID}/download",
                        params={'fmt': 'msexcel', 'auth': data['auth_token'], 'token': data['token']},
                        timeout=45)
    f_res.raise_for_status()
    return f_res.content, data

# ─────────────────────────────────────────────
#  3. MAIN EXECUTION LOOP
# ─────────────────────────────────────────────
def process_tokens():
    banner()
    session = get_session()

    section("ENVIRONMENT")
    log_info(f"Base URL   : {BASE_URL}")
    log_info(f"API ID     : {API_ID}")
    log_info(f"Input CSV  : {INPUT_CSV}")
    log_info(f"Output dir : {OUTPUT_DIR}")
    log_info(f"Cover img  : {COVER_IMAGE_PATH}")

    if not os.path.exists(INPUT_CSV):
        log_crit(f"Input file not found: {INPUT_CSV}")
        print()
        return

    if os.path.exists(COVER_IMAGE_PATH):
        log_ok("Cover image located.")
    else:
        log_warn("Cover image missing — injection step will be skipped.")

    try:
        with open(INPUT_CSV, 'r') as f:
            reader = list(csv.DictReader(f))
            if not reader:
                log_warn("Input CSV is empty. Nothing to do.")
                return
            fieldnames = list(reader[0].keys())
            for col in ['canary_link', 'file_name']:
                if col not in fieldnames:
                    fieldnames.append(col)
    except Exception as e:
        log_crit(f"Failed to read CSV: {e}")
        return

    total = len(reader)
    log_ok(f"Loaded {total} record(s) from {INPUT_CSV}")

    section("TOKEN GENERATION")
    print()

    start_ts = time.time()

    for idx, row in enumerate(reader, 1):
        u_id   = row.get('user_id',   'unknown')
        u_name = row.get('user_name', 'unknown')
        fname  = f"Salaries_Grade_V_and_Above_{u_id}.xlsb"
        fpath  = os.path.join(OUTPUT_DIR, fname)
        row['file_name'] = fname

        job_line(u_id, u_name, idx - 1, total, status="working")

        try:
            content, api_data = generate_and_download(session, row)

            with open(fpath, 'wb') as f:
                f.write(content)

            sys.stdout.write("\033[F\033[K")
            job_line(u_id, u_name, idx, total, status="inject")

            if inject_confidential_cover(fpath, COVER_IMAGE_PATH):
                row['canary_link'] = f"{BASE_URL}/nest/manage/{api_data['auth_token']}/{api_data['token']}"
                sys.stdout.write("\033[F\033[K")
                job_line(u_id, u_name, idx, total, status="done")
            else:
                row['canary_link'] = "INJECTION_FAILED"
                sys.stdout.write("\033[F\033[K")
                job_line(u_id, u_name, idx, total, status="failed")
                log_warn(f"Cover injection failed for UID {u_id}")

        except Exception as e:
            row['canary_link'] = "FAILED_AFTER_RETRIES"
            sys.stdout.write("\033[F\033[K")
            job_line(u_id, u_name, idx, total, status="failed")
            log_err(f"UID {u_id} — {e}")

        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)

        time.sleep(1)

    elapsed = time.time() - start_ts
    summary_table(reader)

    section("DONE")
    log_ok(f"Output CSV  : {OUTPUT_CSV}")
    log_ok(f"Output dir  : {OUTPUT_DIR}")
    log_info(f"Elapsed     : {elapsed:.1f}s")
    print()

# ─────────────────────────────────────────────
if __name__ == "__main__":
    process_tokens()