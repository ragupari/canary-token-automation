import csv
import uuid
import os
import json
import logging
import shutil
import time
import zipfile
import requests
import questionary
import re
import sys
from tqdm import tqdm
from datetime import datetime
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.rule import Rule
from rich.theme import Theme
from rich.live import Live
from rich.align import Align
from rich import box
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("canary_automation.log")
    ]
)

CANARY_BASE_URL = "https://canarytokens.com"
# --- SECURITY: Use environment variables instead of hardcoded values ---
DEFAULT_API_ID = os.environ.get("CANARY_API_ID", "d3aece8093b71007b5ccfedad91ebb11") # Default provided for dev/demo only


class UI:
    """Helper class for consistent, premium terminal UI."""
    console = Console()

    @staticmethod
    def banner():
        title = r"""
  _____  _     _     _              _        __ 
 |  __ \| |   (_)   | |            | |  _   / / 
 | |__) | |__  _ ___| |__   ___  __| | (_) | |  
 |  ___/| '_ \| / __| '_ \ / _ \/ _` |     | |  
 | |    | | | | \__ \ | | |  __/ (_| |  _  | |  
 |_|    |_| |_|_|___/_| |_|\___|\__,_| (_) | |  
                                            \_\ 
                                                
"""
        UI.console.print(Panel(Align.center(Text(title, style="bold cyan")), subtitle="[bold white]Create and manage canary tokens[/bold white]", border_style="bright_blue", padding=(0, 2)))

    @staticmethod
    def heading(text, style="bold yellow"):
        UI.console.print(f"\n[bold yellow]>>>[/bold yellow] [white]{text}[/white]")
        UI.console.print(Rule(style="dim yellow"))

    @staticmethod
    def success(text):
        UI.console.print(f"[bold green]✔ {text}[/bold green]")

    @staticmethod
    def error(text):
        UI.console.print(f"[bold red]✘ {text}[/bold red]")

    @staticmethod
    def warning(text):
        UI.console.print(f"[bold orange3]! {text}[/bold orange3]")

    @staticmethod
    def info(text):
        UI.console.print(f"[bold blue]ℹ {text}[/bold blue]")

    @staticmethod
    def highlight(text):
        UI.console.print(f"[bold yellow]⚠ {text}[/bold yellow]")

    @staticmethod
    def stats_panel(total, engaged, hits):
        rate = ((engaged/total)*100) if total else 0
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row("[cyan]Total Tokens Tracked:[/cyan]", f"[bold white]{total}[/bold white]")
        grid.add_row("[cyan]Users Engaged (Clicked):[/cyan]", f"[bold yellow]{engaged}[/bold yellow]")
        grid.add_row("[cyan]Engagement Rate:[/cyan]", f"[bold {'red' if rate > 20 else 'green'}]{rate:.2f}%[/bold {'red' if rate > 20 else 'green'}]")
        grid.add_row("[cyan]Total Triggers (Hits):[/cyan]", f"[bold magenta]{hits}[/bold magenta]")
        
        UI.console.print(Panel(grid, title="[bold white]Campaign Performance Summary[/bold white]", border_style="bright_blue", expand=False, padding=(1, 4)))

class PDFReport(FPDF):
    def header(self):
        # Logo part
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(0, 102, 204)
        self.cell(0, 10, 'Phishing Simulation With Canary Tokens Report', align='C', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(128)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', align='C', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

    def create_table(self, header, data, col_widths, merge_first_col=False):
        row_h = 6
        header_h = 7
        page_bottom_threshold = 265 # A4 is 297mm
        
        def draw_header():
            self.set_font('helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            for i, h in enumerate(header):
                self.cell(col_widths[i], header_h, h, border=1, fill=True)
            self.ln()
            self.set_font('helvetica', '', 9)

        draw_header()
        
        if not data: return

        if merge_first_col:
            # Pre-calculate spans for the first column
            spans = []
            i = 0
            while i < len(data):
                val = data[i][0]
                count = 1
                j = i + 1
                while j < len(data) and data[j][0] == val:
                    count += 1
                    j += 1
                spans.append((i, count))
                i = j
            
            span_map = {start: count for start, count in spans}
            
            for idx, row in enumerate(data):
                # Check for page break ONLY at the START of a merged group
                if idx in span_map:
                    group_height = row_h * span_map[idx]
                    if self.get_y() + group_height > page_bottom_threshold:
                        self.add_page()
                        draw_header()

                current_x = self.get_x()
                current_y = self.get_y()

                if idx in span_map:
                    # Start of a merged group - draw the big centered cell
                    span_count = span_map[idx]
                    self.cell(col_widths[0], row_h * span_count, str(row[0]), border=1, align='C', 
                              new_x=XPos.RIGHT, new_y=YPos.TOP)
                else:
                    # Move to the next column for continuation rows (keeping alignment)
                    self.set_xy(current_x + col_widths[0], current_y)
                
                # Draw other columns for this specific row
                for i in range(1, len(row)):
                    self.cell(col_widths[i], row_h, str(row[i]), border=1, 
                              new_x=XPos.RIGHT if i < len(row)-1 else XPos.LMARGIN, 
                              new_y=YPos.TOP if i < len(row)-1 else YPos.NEXT)
        else:
            # Normal table logic (No merging)
            for row in data:
                if self.get_y() + row_h > page_bottom_threshold:
                    self.add_page()
                    draw_header()

                for i, item in enumerate(row):
                    self.cell(col_widths[i], row_h, str(item), border=1, 
                              new_x=XPos.RIGHT if i < len(row)-1 else XPos.LMARGIN, 
                              new_y=YPos.TOP if i < len(row)-1 else YPos.NEXT)

class CanarySimulationTool:
    def __init__(self, api_id=DEFAULT_API_ID):
        self.api_id = api_id
        self.session = self._setup_session()

    def _setup_session(self):
        """Configures a retry-resilient requests session."""
        s = requests.Session()
        retries = Retry(total=5, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retries))
        return s

    # --- 1. INPUT PARSING ---
    def parse_input_csv(self, file_path, default_assignee=None):
        """
        Reads target recipients and metadata from a CSV file.
        Expects columns: id, name, email, assignee
        """
        targets = []
        if not os.path.exists(file_path):
            logging.error(f"Input file not found: {file_path}")
            return []

        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for index, row in enumerate(reader, start=1):
                    # Create our own sequential Canary_ID in CNRY-XXXX format
                    row['Canary_ID'] = f"{index:04d}"
                    if default_assignee:
                        row['assignee'] = default_assignee
                    targets.append(row)
            logging.info(f"Loaded {len(targets)} recipients from {file_path}")
            return targets
        except Exception as e:
            logging.error(f"Error parsing CSV {file_path}: {e}")
            return []

    # --- 2. ASSET GENERATION ---
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
    def generate_canary_asset(self, recipient_metadata):
        """
        Generates a unique identifier and associates it with a canary trigger.
        In this implementation, it interfaces with the CanaryTokens API.
        """
        cid = recipient_metadata.get('Canary_ID', 'unknown')
        email_val = recipient_metadata.get('assignee', '')
        memo = f"CID:{cid} - {recipient_metadata.get('name', 'Unknown')}"

        try:
            # Generate the token
            res = self.session.post(
                f"{CANARY_BASE_URL}/{self.api_id}/generate",
                data={'email': email_val, 'memo': memo, 'token_type': 'ms_excel'},
                timeout=30
            )
            res.raise_for_status()
            api_data = res.json()
            
            # Associate a unique UUID for internal tracking if needed
            internal_uuid = str(uuid.uuid4())
            
            return {
                "Canary_ID": cid,
                "internal_uuid": internal_uuid,
                "auth_token": api_data['auth_token'],
                "canary_token": api_data['token'],
                "manage_url": f"{CANARY_BASE_URL}/nest/manage/{api_data['auth_token']}/{api_data['token']}"
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 'Unknown'
            msg = e.response.text if e.response else str(e)
            logging.error(f"Failed to generate canary asset for {user_id}. API HTTP {status}: {msg}")
            raise Exception(f"API HTTP {status}: {msg}")
        except Exception as e:
            logging.error(f"Failed to generate canary asset for {user_id}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
    def fetch_token_history(self, token, auth_token):
        """
        Fetches history (trigger incidents) of a specific token.
        """
        try:
            url = f"{CANARY_BASE_URL}/{self.api_id}/history"
            params = {'token': token, 'auth': auth_token}
            res = self.session.get(url, params=params, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data.get('history', {}).get('hits', [])
            return []
        except Exception as e:
            logging.error(f"Failed to fetch history for token {token}: {e}")
            return []

    def filter_unique_hits(self, raw_hits):
        """
        Takes raw API hit objects and deduplicates based on IP and a 10s temporal gap.
        Returns a minimal, clean list of hits.
        """
        raw_hits.sort(key=lambda x: x.get('time_of_hit', 0))
        hit_details = []
        last_seen_per_ip = {} 

        for hit in raw_hits:
            raw_time = hit.get('time_of_hit')
            ip_addr = hit.get('src_ip', 'N/A')
            
            if raw_time is None: continue

            should_record = False
            if ip_addr not in last_seen_per_ip:
                should_record = True
            elif abs(raw_time - last_seen_per_ip[ip_addr]) > 10:
                should_record = True

            if should_record:
                last_seen_per_ip[ip_addr] = raw_time
                fmt_time = datetime.fromtimestamp(raw_time).strftime('%Y-%m-%d %H:%M:%S')
                
                agent = hit.get('useragent', '')
                if len(agent) > 30: agent = agent[:27] + '...'
                
                hit_details.append({
                    "Time": fmt_time, 
                    "IP Addr": ip_addr,
                    "Location": f"{hit.get('geo_info',{}).get('city','')}, {hit.get('geo_info',{}).get('country','')}",
                    "User Agent": agent
                })
                
        return hit_details

    # --- 3. FILE PACKAGING ---
    def package_document(self, asset_data, template_path, output_path, cover_image=None):
        """
        Downloads the canary-enabled document and optionally injects a cover image.
        """
        try:
            # Download the template with the token embedded
            download_res = self.session.get(
                f"{CANARY_BASE_URL}/{self.api_id}/download",
                params={
                    'fmt': 'msexcel',
                    'auth': asset_data['auth_token'],
                    'token': asset_data['canary_token']
                },
                timeout=45
            )
            download_res.raise_for_status()
            
            # Save the file
            with open(output_path, 'wb') as f:
                f.write(download_res.content)

            # Optional cover image injection (Specific to OOXML/XLSB)
            if cover_image and os.path.exists(cover_image):
                self._inject_cover_image(output_path, cover_image)
            
            return True
        except Exception as e:
            logging.error(f"Error packaging document for {asset_data['user_id']}: {e}")
            return False

    def _inject_cover_image(self, file_path, image_path):
        """
        Injects a cover image into the XLSB/XLSX file by modifying internal XML structures.
        This provides a programmatic way to associate a unique identifier with a visual asset.
        """
        tmp_dir = f"tmp_edit_{uuid.uuid4().hex[:8]}"
        
        if not os.path.exists(image_path):
            logging.error(f"Cover image {image_path} missing.")
            return False

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
                
            # XML Namespaces for OpenXML
            CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
            REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
            DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
            A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
            R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

            # 1. Content Types Registration
            ct_path = os.path.join(tmp_dir, '[Content_Types].xml')
            ct_tree = etree.parse(ct_path)
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            if not ct_tree.xpath(f"//ct:Default[@Extension='{ext}']", namespaces={'ct': CT_NS}):
                etree.SubElement(ct_tree.getroot(), f"{{{CT_NS}}}Default", Extension=ext, ContentType=f"image/{ext}")
                ct_tree.write(ct_path, xml_declaration=True, encoding='UTF-8', standalone=True)

            # 2. Move Image to Media Folder
            media_dir = os.path.join(tmp_dir, 'xl', 'media')
            os.makedirs(media_dir, exist_ok=True)
            target_img_name = f"image_cover.{ext}"
            shutil.copy(image_path, os.path.join(media_dir, target_img_name))

            # 3. Update Drawing Relationships
            rel_path = os.path.join(tmp_dir, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
            if not os.path.exists(rel_path):
                 # Fallback if drawing1 doesn't exist (basic template)
                 logging.warning("Drawing relationships file not found in template. Skipping injection.")
                 return False

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

            # 4. Update Drawing XML to place the image
            draw_path = os.path.join(tmp_dir, 'xl', 'drawings', 'drawing1.xml')
            draw_tree = etree.parse(draw_path)
            draw_root = draw_tree.getroot()
            
            anchor = etree.SubElement(draw_root, f"{{{DRAW_NS}}}twoCellAnchor", editAs="absolute")
            # Positioning (Full screen cover)
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

            # 5. Re-build the Zip package
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for root, dirs, files in os.walk(tmp_dir):
                    for file in files:
                        full_p = os.path.join(root, file)
                        new_zip.write(full_p, os.path.relpath(full_p, tmp_dir))
            return True

        except Exception as e:
            logging.error(f"Injection process failed: {e}")
            return False
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    # --- 4. OUTPUT MANAGEMENT ---
    def export_tracking_csv(self, tracking_list, output_path, selected_input_fields=None, append=False):
        """Generates a mapping CSV of recipients to their unique URLs."""
        if not tracking_list:
            return

        try:
            canonical_asset_fields = ["internal_uuid", "auth_token", "canary_token", "manage_url", "file_path"]
            
            if selected_input_fields is None:
                all_keys = list(tracking_list[0].keys())
                keys = [k for k in all_keys if k not in canonical_asset_fields] + canonical_asset_fields
            else:
                 keys = selected_input_fields + canonical_asset_fields

            mode = 'a' if append else 'w'
            with open(output_path, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                if mode == 'w':
                    writer.writeheader()
                writer.writerows(tracking_list)
        except Exception as e:
            logging.error(f"Failed to export tracking CSV: {e}")

def prompt_for_range(total_items):
    default_range = f"1-{total_items}"
    while True:
        range_input = questionary.text(
            f"Enter range to process (1-{total_items}):",
            default=default_range
        ).ask()
        
        if range_input is None: return None
        
        try:
            parts = range_input.split('-')
            if len(parts) != 2: raise ValueError()
            start_idx = int(parts[0].strip())
            end_idx = int(parts[1].strip())
            if start_idx < 1 or end_idx > total_items or start_idx > end_idx:
                raise ValueError()
            return start_idx - 1, end_idx
        except ValueError:
            UI.error(f"Invalid range format. Please use 'start-end' (e.g., 1-{total_items}).")

# --- 5. REPORTING MODULE ---
def run_report_menu():
    try:
        UI.heading("Phishing Simulation Report Engine")
        
        tracking_csv_path = questionary.path(
            "Enter the path to the tracking map CSV file:",
            default="tracking_map.csv"
        ).ask()
        
        if tracking_csv_path is None: return
        
        if not os.path.exists(tracking_csv_path):
            UI.error(f"Tracking file '{tracking_csv_path}' not found.")
            return
            
        UI.info("Reading tracking CSV...")
        recipients = []
        with open(tracking_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                recipients.append(row)
                
        if not recipients:
            UI.error("Tracking file is empty.")
            return
            
        tool = CanarySimulationTool()
        
        while True:
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Overall Summary",
                    "Generate Complete Report (PDF)",
                    "Generate Full Report (CSV)",
                    "Generate Compromised Report (CSV)",
                    "View Specific User Trigger (Email Search)",
                    "Back to Main Menu",
                    "Exit execution"
                ]
            ).ask()
            
            if action == "Exit execution" or action is None:
                exit(0)
            elif action == "Back to Main Menu":
                return
            elif action == "Overall Summary":
                UI.info("Fetching latest triggers. Please wait...")
                engaged_users = set()
                total_hits = 0
                
                with tqdm(total=len(recipients), desc="Scanning Tokens", unit="doc", dynamic_ncols=True) as pbar:
                    for row in recipients:
                        token = row.get("canary_token")
                        auth = row.get("auth_token")
                        if token and auth:
                            raw_hits = tool.fetch_token_history(token, auth)
                            hits = tool.filter_unique_hits(raw_hits)
                            if hits:
                                engaged_users.add(row.get('Canary_ID', 'unknown'))
                                total_hits += len(hits)
                            time.sleep(0.5) # Polite delay
                        pbar.update(1)
                        
                total_users = len(recipients)
                UI.stats_panel(total_users, len(engaged_users), total_hits)

            elif action == "Generate Complete Report (PDF)":
                report_out = questionary.path(
                    "Enter path to save PDF Report:",
                    default="campaign_summary.pdf"
                ).ask()
                if not report_out: continue

                UI.info("Compiling data for PDF report. Please wait...")
                
                engaged_count = 0
                total_hits_count = 0
                summary_table_data = [] # Everyone
                detailed_hits_map = {}  # Map email -> list of hit details

                with tqdm(total=len(recipients), desc="Scanning Tokens", unit="doc", dynamic_ncols=True) as pbar:
                    for row in recipients:
                        token = row.get("canary_token")
                        auth = row.get("auth_token")
                        hits = []
                        if token and auth:
                            raw_hits = tool.fetch_token_history(token, auth)
                            hits = tool.filter_unique_hits(raw_hits)
                            
                            comp_status = "No"
                            if hits:
                                engaged_count += 1
                                total_hits_count += len(hits)
                                comp_status = "Yes"
                                
                                # Collect data for detailed logs
                                email_search = row.get("email", "N/A")
                                if email_search not in detailed_hits_map:
                                    detailed_hits_map[email_search] = []
                                    
                                for hit in hits:
                                    detailed_hits_map[email_search].append([
                                        hit.get("Time", "N/A"),
                                        hit.get("IP Addr", "N/A"),
                                        hit.get("Location", "N/A")
                                    ])
                            
                            # Add user to the main summary list (always included)
                            summary_table_data.append([
                                row.get("Canary_ID", "N/A"),
                                row.get("email", "N/A"),
                                comp_status,
                                len(hits),
                                hits[-1]['Time'] if hits else "N/A"
                            ])
                            
                            time.sleep(0.5) 
                        pbar.update(1)

                try:
                    pdf = PDFReport()
                    pdf.alias_nb_pages()
                    pdf.add_page()
                    
                    # Executive Summary
                    pdf.chapter_title("1. Executive Summary")
                    pdf.set_font('helvetica', '', 11)
                    pdf.cell(0, 7, f"Total Distribution: {len(recipients)} users", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.cell(0, 7, f"Engaged Users (Clicked): {engaged_count}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    rate = (engaged_count / len(recipients) * 100) if recipients else 0
                    pdf.cell(0, 7, f"Engagement Rate: {rate:.2f}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.cell(0, 7, f"Total Hits Triggered: {total_hits_count}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(10)

                    # Summary Table (ALL USERS)
                    pdf.chapter_title("2. Distribution & Engagement List")
                    header = ["ID", "Email Address", "Hit?", "Hits", "Last Seen"]
                    widths = [10, 85, 15, 15, 65]
                    pdf.create_table(header, summary_table_data, widths)
                    pdf.ln(10)
                    
                    # Detailed Logs (One Single Table, Grouped by Email)
                    if detailed_hits_map:
                        pdf.chapter_title("3. Detailed Compromise Logs (IP/Location/Time)")
                        pdf.set_font('helvetica', 'I', 10)
                        pdf.cell(0, 7, "All individual trigger events recorded during the campaign.", 
                                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(2)

                        # Flatten the data for the table
                        all_detailed_hits = []
                        # Keep records grouped by email by using the map keys
                        for email in sorted(detailed_hits_map.keys()):
                            for hit_row in detailed_hits_map[email]:
                                # Prepend email to the hit row
                                all_detailed_hits.append([email] + hit_row)
                        
                        header = ["Email Address", "Trigger Time", "IP Address", "Approx. Location"]
                        widths = [60, 45, 30, 55]
                        pdf.create_table(header, all_detailed_hits, widths, merge_first_col=True)
                    else:
                        pdf.chapter_title("3. Detailed Compromise Logs")
                        pdf.set_font('helvetica', 'I', 11)
                        pdf.cell(0, 10, "No individual compromise events recorded.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                    pdf.output(report_out)
                    UI.success(f"PDF Report successfully generated: {report_out}")
                except Exception as e:
                    UI.error(f"Failed to Generate Complete Report (PDF): {e}")
                
            elif action == "Generate Full Report (CSV)":
                range_indices = prompt_for_range(len(recipients))
                if not range_indices: continue
                recipients_to_process = recipients[range_indices[0]:range_indices[1]]
                
                report_out = questionary.path(
                    "Enter path to save full report CSV:",
                    default="campaign_report.csv"
                ).ask()
                if not report_out: continue
                
                UI.info("Fetching data and generating full report CSV. Please wait...")
                report_data = []
                first_write = True
                with tqdm(total=len(recipients_to_process), desc="Building Report", unit="doc", dynamic_ncols=True) as pbar:
                    for idx, row in enumerate(recipients_to_process, 1):
                        token = row.get("canary_token")
                        auth = row.get("auth_token")
                        hits = []
                        if token and auth:
                            raw_hits = tool.fetch_token_history(token, auth)
                            hits = tool.filter_unique_hits(raw_hits)
                            time.sleep(0.5) # Polite delay
                            
                        report_entry = {k: v for k, v in row.items()}
                        for k in ["internal_uuid", "canary_token", "auth_token", "manage_url", "file_path", "assignee"]:
                            report_entry.pop(k, None)
                        
                        report_entry["is_compromised"] = "Yes" if hits else "No"
                        report_entry["trigger_count"] = len(hits)
                        report_entry["last_triggered"] = hits[-1]['Time'] if hits else "N/A"
                        report_entry["details"] = json.dumps(hits)
                        
                        report_data.append(report_entry)
                        pbar.update(1)
                        
                        if idx % 5 == 0 or idx == len(recipients_to_process):
                            if report_data:
                                try:
                                    keys = list(report_data[0].keys())
                                    mode = 'w' if first_write else 'a'
                                    with open(report_out, mode, newline='', encoding='utf-8') as f:
                                        writer = csv.DictWriter(f, fieldnames=keys)
                                        if mode == 'w':
                                            writer.writeheader()
                                        writer.writerows(report_data)
                                    first_write = False
                                    report_data = []
                                except Exception as e:
                                    UI.error(f"Error saving report batch: {e}")
                
                UI.success(f"Full report saved to: {report_out}")
                    
            elif action == "Generate Compromised Report (CSV)":
                range_indices = prompt_for_range(len(recipients))
                if not range_indices: continue
                recipients_to_process = recipients[range_indices[0]:range_indices[1]]
                
                report_out = questionary.path(
                    "Enter path to save compromised report CSV:",
                    default="compromised_report.csv"
                ).ask()
                if not report_out: continue

                UI.info("Fetching data and generating compromised report CSV. Please wait...")
                report_data = []
                first_write = True
                found_compromised = False
                
                with tqdm(total=len(recipients_to_process), desc="Building Report", unit="doc", dynamic_ncols=True) as pbar:
                    for idx, row in enumerate(recipients_to_process, 1):
                        token = row.get("canary_token")
                        auth = row.get("auth_token")
                        hits = []
                        if token and auth:
                            raw_hits = tool.fetch_token_history(token, auth)
                            hits = tool.filter_unique_hits(raw_hits)
                            time.sleep(0.5) # Polite delay
                            
                        if hits:
                            found_compromised = True
                            report_entry = {k: v for k, v in row.items()}
                            for k in ["internal_uuid", "canary_token", "auth_token", "manage_url", "file_path", "assignee"]:
                                report_entry.pop(k, None)
                            
                            report_entry["is_compromised"] = "Yes"
                            report_entry["trigger_count"] = len(hits)
                            report_entry["last_triggered"] = hits[-1]['Time']
                            report_entry["details"] = json.dumps(hits)
                            
                            report_data.append(report_entry)
                        pbar.update(1)
                        
                        if idx % 5 == 0 or idx == len(recipients_to_process):
                            if report_data:
                                try:
                                    keys = list(report_data[0].keys())
                                    mode = 'w' if first_write else 'a'
                                    with open(report_out, mode, newline='', encoding='utf-8') as f:
                                        writer = csv.DictWriter(f, fieldnames=keys)
                                        if mode == 'w':
                                            writer.writeheader()
                                        writer.writerows(report_data)
                                    first_write = False
                                    report_data = []
                                except Exception as e:
                                    UI.error(f"Error saving report batch: {e}")
                
                if not found_compromised:
                    UI.success("No users were compromised.")
                else:
                    UI.success(f"Compromised report saved to: {report_out}")

            elif action == "View Specific User Trigger (Email Search)":
                # Extract emails for autocomplete
                user_choices = [r['email'] for r in recipients if r.get('email')]
                    
                search_term = questionary.autocomplete(
                    "Search for user email:",
                    choices=user_choices
                ).ask()
                
                if not search_term: continue
                
                found = [r for r in recipients if r.get('email') == search_term]
                
                if not found:
                    UI.error(f"User email '{search_term}' not found in tracking map.")
                    continue
                    
                target = found[0]
                token = target.get("canary_token")
                auth = target.get("auth_token")
                
                UI.info(f"Fetching data for {target.get('name', target.get('email'))}...")
                raw_hits = tool.fetch_token_history(token, auth)
                hits = tool.filter_unique_hits(raw_hits)
                
                if not hits:
                    UI.warning("No triggers recorded for this user.")
                else:
                    UI.warning(f"User '{target.get('name', target.get('email'))}' triggered the token {len(hits)} unique times!")
                    table = Table(title=f"Trigger History for {target.get('name')}", box=box.ROUNDED)
                    for key in hits[0].keys():
                        table.add_column(key, style="cyan")
                    for hit in hits:
                        table.add_row(*[str(v) for v in hit.values()])
                    UI.console.print(table)
    except Exception as e:
        UI.error(f"An unexpected error occurred in Report Engine: {e}")
        logging.exception("Report Engine Failure")

# --- CAMPAIGN WIZARD FLOW ---
def run_campaign_wizard():
    try:
        UI.heading("Canary Security Campaign Wizard")
    
        # 1. Prompt for Input CSV & Preview
        input_csv_path = questionary.path(
            "Enter the path to the input CSV file:",
            default="users_input.csv"
        ).ask()
        if input_csv_path is None: return
            
        if not os.path.exists(input_csv_path):
            UI.error(f"Input file '{input_csv_path}' not found.")
            return

        UI.info("Reading input CSV...")
        tool = CanarySimulationTool()
        
        # Parse the csv
        targets = tool.parse_input_csv(input_csv_path)
        if not targets: return

        # Dynamic Field Mapping & Validation for 'email'
        mapped_email_field = None
        if targets and 'email' not in targets[0]:
            UI.error("Field 'email' not found in the CSV headers.")
            headers = list(targets[0].keys())
            mapped_email_field = questionary.select(
                "Which column contains the user EMAIL addresses?",
                choices=headers
            ).ask()
            
            if mapped_email_field is None: return

            # Validation with Regex (Supports xx.xx@xx.xx etc.)
            email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            
            # Check a few rows for validation to be sure
            sample_count = min(len(targets), 10)
            for i in range(sample_count):
                email_val = targets[i].get(mapped_email_field, "").strip()
                if not re.match(email_regex, email_val):
                    UI.error(f"Validation Error: Column '{mapped_email_field}' contains an invalid email format at row {i+1}: '{email_val}'")
                    UI.info("Ensure the column exclusively contains valid email addresses.")
                    return

            # Perform the mapping
            for target in targets:
                target['email'] = target[mapped_email_field]
            UI.success("CSV Headers mapped successfully.")

        UI.info("Preview of the first 5 entries:")
        table = Table(box=box.ROUNDED)
        if targets:
            # We filter labels to show key fields first in preview
            preview_cols = ['Canary_ID', 'name', 'email']
            for key in preview_cols:
                if key in targets[0]:
                    table.add_column(key, style="cyan")
            # Add any other fields from the original CSV
            for key in targets[0].keys():
                if key not in preview_cols:
                    table.add_column(key, style="dim white")

            for row in targets[:5]:
                row_vals = []
                # First build vals for preview columns
                for key in preview_cols:
                    if key in row: row_vals.append(str(row[key]))
                # Then the rest
                for key, val in row.items():
                    if key not in preview_cols: row_vals.append(str(val))
                table.add_row(*row_vals)
            UI.console.print(table)
        
        # Prompt for Assignee Email (Using standard input to prevent buffered keystroke skipping)
        has_csv_assignee = len(targets) > 0 and 'assignee' in targets[0]
        
        while True:
            if has_csv_assignee:
                prompt_msg = "Enter the assignee email for these canaries (leave blank to use values from CSV):"
            else:
                prompt_msg = "Enter the assignee email for these canaries (REQUIRED since not in CSV):"
                
            assignee_email = questionary.text(prompt_msg).ask()
            
            if assignee_email is None: return # Handle cancellation
            assignee_email = assignee_email.strip()
            
            if assignee_email:
                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", assignee_email):
                    UI.error("Please enter a valid email address.")
                    continue
                    
                for target in targets:
                    target['assignee'] = assignee_email
                UI.success(f"Assignee updated to {assignee_email} for all {len(targets)} recipients.")
                break
            elif has_csv_assignee:
                UI.info("Using existing CSV values for assignees.")
                break
            else:
                UI.error("You must enter an assignee email because the CSV lacks an 'assignee' column.")

        # 2. Prompt for Cover Image
        cover_image_path = questionary.autocomplete(
            "Enter path to cover image (blank to skip):",
            choices=["cover.png", "none"]
        ).ask()
        if cover_image_path is None: return
        cover_image_path = cover_image_path.strip()

        if not cover_image_path or cover_image_path.lower() == 'none':
            cover_image_path = None
            UI.info("Skipping cover image injection.")
        elif not os.path.exists(cover_image_path):
            UI.error(f"Cover image '{cover_image_path}' not found.")
            return

        # 3. Prompt for Output Directory for Canary Files
        files_output_dir = questionary.path(
            "Enter the directory to store the generated canary documents:",
            default="generated_canaries"
        ).ask()
        if files_output_dir is None: return
        os.makedirs(files_output_dir, exist_ok=True)
        
        # 4. Prompt for Output Tracking CSV path
        tracking_csv_path = questionary.path(
            "Enter the path to save the tracking CSV file:",
            default="tracking_map.csv"
        ).ask()
        if tracking_csv_path is None: return
        UI.highlight("Keep this CSV safe! It's essential to track the tokens and generate reports later.")
            
        # Ensure the directory for tracking CSV exists
        tracking_csv_dir = os.path.dirname(tracking_csv_path)
        if tracking_csv_dir:
            os.makedirs(tracking_csv_dir, exist_ok=True)

        # Prompt for Columns
        
        # Standard: Always include Canary_ID and email in the tracking map for engagement correlation.
        mandatory_fields = ["Canary_ID", "email"]
        
        # Exclude mandatory fields AND the original mapped column (if used) from ADDITIONAL choices
        excluded_from_selection = mandatory_fields + ([mapped_email_field] if mapped_email_field else [])
        
        field_choices = [f for f in targets[0].keys() if f not in excluded_from_selection]
        
        selected_others = questionary.checkbox(
            f"Select ADDITIONAL fields for the tracking CSV ({', '.join(mandatory_fields)} will be included automatically):",
            choices=field_choices
        ).ask()
        
        if selected_others is None: 
            return # User cancelled the prompt
            
        selected_input_fields = mandatory_fields + (selected_others or [])

        # 6. Prompt for base filename for canaries
        base_filename = questionary.text(
            "Enter the base name for the generated files (e.g. 'Confidential_Report'):",
            default="Confidential_Report"
        ).ask()
        if base_filename is None: return
        
        # Strip any extension if the user accidentally provided one
        if base_filename.endswith(".xlsb"):
            base_filename = base_filename[:-5]
    
        UI.heading("Execution Started")
        
        range_indices = prompt_for_range(len(targets))
        if not range_indices: return
        targets_to_process = targets[range_indices[0]:range_indices[1]]

        tracking_data = []
        first_write = True

        # 7. Process each recipient
        logging.info("Starting asset generation and packaging...")
        UI.info(f"Processing {len(targets_to_process)} recipients...")
        
        # Use tqdm for a progress bar
        with tqdm(total=len(targets_to_process), desc="Generating Canaries", unit="doc", dynamic_ncols=True) as pbar:
            for idx, target in enumerate(targets_to_process, 1):
                try:
                    # Asset Generation
                    asset = tool.generate_canary_asset(target)
                    
                    # File Packaging
                    filename = f"{base_filename}_{target['Canary_ID']}.xlsb"
                    out_path = os.path.join(files_output_dir, filename)
                    
                    if tool.package_document(asset, "template.xlsb", out_path, cover_image=cover_image_path):
                        tracking_entry = {**target, **asset, "file_path": out_path}
                        tracking_data.append(tracking_entry)
                        logging.info(f"Packaged document for {target.get('name', target.get('Canary_ID'))}")
                        
                        email_display = target.get('email') or target.get('assignee') or target.get('Canary_ID', 'unknown')
                        # Update progress bar description with the last processed user
                        pbar.set_postfix_str(f"Last: {email_display}")
                        tqdm.write(f"[*] Generated {filename} for {email_display}")
                    else:
                        tqdm.write(f"[!] Failed to package {filename}")
                    
                    time.sleep(1) # Rate limiting
                except KeyboardInterrupt:
                    tqdm.write("\n[!] Campaign generation interrupted by user. Saving existing progress...")
                    break
                except RetryError as e:
                    real_err = e.last_attempt.exception() if e.last_attempt else e
                    logging.error(f"Failed processing {target.get('Canary_ID', 'unknown')} (Retries exhausted): {real_err}")
                    tqdm.write(f"[!] Failed processing {target.get('Canary_ID', 'unknown')}: {real_err}")
                except Exception as e:
                    logging.error(f"Failed processing {target.get('Canary_ID', 'unknown')}: {e}")
                    tqdm.write(f"[!] Failed processing {target.get('Canary_ID', 'unknown')}: {e}")
                
                pbar.update(1)
                
                # Batch write every 5 users or at finish
                if idx % 5 == 0 or idx == len(targets_to_process):
                    if tracking_data:
                        tool.export_tracking_csv(tracking_data, tracking_csv_path, selected_input_fields=selected_input_fields, append=not first_write)
                        first_write = False
                        tracking_data = []

        # Let's catch lingering tracking data if interrupted
        if tracking_data:
            tool.export_tracking_csv(tracking_data, tracking_csv_path, selected_input_fields=selected_input_fields, append=not first_write)

        UI.success("Execution complete!")
        UI.info(f"Documents saved to: [bold white]{files_output_dir}/[/bold white]")
        UI.info(f"Tracking data saved to: [bold white]{tracking_csv_path}[/bold white]")

    except Exception as e:
        UI.error(f"An unexpected error occurred in Campaign Wizard: {e}")
        logging.exception("Campaign Wizard Failure")

# --- MAIN ENTRY POINT ---
def main():
    try:
        while True:
            UI.banner()
            mode = questionary.select(
                "What would you like to do?",
                choices=[
                    "1. New Campaign (Generate Tokens)",
                    "2. Report Gen (Previous Campaigns)",
                    "3. Help & Documentation",
                    "Exit"
                ]
            ).ask()
            
            if mode == "1. New Campaign (Generate Tokens)":
                run_campaign_wizard()
            elif mode == "2. Report Gen (Previous Campaigns)":
                run_report_menu()
            elif mode == "3. Help & Documentation":
                if getattr(sys, 'frozen', False):
                    application_path = sys._MEIPASS
                else:
                    application_path = os.path.dirname(os.path.abspath(__file__))
                
                doc_path = os.path.join(application_path, "DOCUMENTATION.md")
                
                if os.path.exists(doc_path):
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        UI.console.print(Panel(Markdown(f.read()), title="Help & Documentation", border_style="bright_blue"))
                    UI.console.input("\n[bold cyan]Press Enter to return to the main menu...[/bold cyan]")
                else:
                    UI.error("DOCUMENTATION.md not found in the current directory.")
            else:
                UI.info("Exiting...")
                break
    except (KeyboardInterrupt, EOFError):
        UI.warning("Execution interrupted by user. Exiting gracefully.")

if __name__ == "__main__":
    main()
