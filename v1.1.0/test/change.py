import zipfile
import os
import shutil
from lxml import etree

def inject_confidential_cover(input_xlsx, cover_image_path, output_xlsx):
    tmp_dir = 'tmp_cover_edit'
    if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
    
    with zipfile.ZipFile(input_xlsx, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)

    # 1. Inject the Cover Image file
    media_dir = os.path.join(tmp_dir, 'xl', 'media')
    if not os.path.exists(media_dir): os.makedirs(media_dir)
    # Using a generic name and keeping original extension
    ext = os.path.splitext(cover_image_path)[1]
    target_img_name = f"cover{ext}"
    shutil.copy(cover_image_path, os.path.join(media_dir, target_img_name))

    # 2. Update Relationships for the drawing
    rel_file = os.path.join(tmp_dir, 'xl', 'drawings', '_rels', 'drawing1.xml.rels')
    # Use proper namespace handling for the relationship ID
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    tree = etree.parse(rel_file)
    root = tree.getroot()
    new_id = f"rId{len(root) + 1}"
    etree.SubElement(root, f"{{{rel_ns}}}Relationship", 
                     Id=new_id, 
                     Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                     Target=f"../media/{target_img_name}")
    tree.write(rel_file, xml_declaration=True, encoding='UTF-8')

    # 3. Modify Worksheet XML for a "Locked-Down" UI
    sheet_file = os.path.join(tmp_dir, 'xl', 'worksheets', 'sheet1.xml')
    sheet_tree = etree.parse(sheet_file)
    sheet_root = sheet_tree.getroot()
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    
    sheet_views = sheet_root.find(f".//{{{main_ns}}}sheetViews")
    if sheet_views is not None:
        view = sheet_views.find(f".//{{{main_ns}}}sheetView")
        if view is not None:
            view.set("showGridLines", "0")
            view.set("showRowColHeaders", "0")
            view.set("showFormulas", "0")
            view.set("view", "pageLayout")  # Makes the sheet look like a formal page
            view.set("tabSelected", "1")

    sheet_tree.write(sheet_file, xml_declaration=True, encoding='UTF-8')

    # 4. Inject Professional Drawing XML (with Locks)
    drawing_file = os.path.join(tmp_dir, 'xl', 'drawings', 'drawing1.xml')
    xdr = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    
    draw_tree = etree.parse(drawing_file)
    draw_root = draw_tree.getroot()
    
    # Create a clean anchor
    anchor = etree.SubElement(draw_root, f"{xdr}twoCellAnchor", editAs="absolute")
    
    f_pos = etree.SubElement(anchor, f"{xdr}from")
    for tag, val in [("col", "0"), ("colOff", "0"), ("row", "0"), ("rowOff", "0")]:
        etree.SubElement(f_pos, f"{xdr}{tag}").text = val
        
    t_pos = etree.SubElement(anchor, f"{xdr}to")
    for tag, val in [("col", "20"), ("colOff", "0"), ("row", "80"), ("rowOff", "0")]:
        etree.SubElement(t_pos, f"{xdr}{tag}").text = val

    pic = etree.SubElement(anchor, f"{xdr}pic")
    nv_pic = etree.SubElement(pic, f"{xdr}nvPicPr")
    etree.SubElement(nv_pic, f"{xdr}cNvPr", id="101", name="ConfidentialCover", descr="Confidential")
    
    # Professional touch: Lock the image so users can't move it
    nv_cnv_pic = etree.SubElement(nv_pic, f"{xdr}cNvPicPr")
    etree.SubElement(nv_cnv_pic, f"{a}picLocks", noGrp="1", noMove="1", noResize="1", noSelect="1")
    
    blip_f = etree.SubElement(pic, f"{xdr}blipFill")
    # Correctly namespaced r:embed attribute
    etree.SubElement(blip_f, f"{a}blip", {f"{r}embed": new_id})
    etree.SubElement(blip_f, f"{a}stretch", {}, etree.Element(f"{a}fillRect"))
    
    etree.SubElement(pic, f"{xdr}spPr", {}, etree.Element(f"{a}prstGeom", prst="rect"))
    etree.SubElement(anchor, f"{xdr}clientData")
    
    draw_tree.write(drawing_file, xml_declaration=True, encoding='UTF-8')

    # 5. Re-zip
    with zipfile.ZipFile(output_xlsx, 'w', zipfile.ZIP_DEFLATED) as new_zip:
        for root_dir, _, files in os.walk(tmp_dir):
            for file in files:
                full_path = os.path.join(root_dir, file)
                # Keep internal structure consistent
                new_zip.write(full_path, os.path.relpath(full_path, tmp_dir))

    shutil.rmtree(tmp_dir)
    print(f"Professional cover page applied to {output_xlsx}")

# Run the script
inject_confidential_cover('generated_tokens/Salaries_Grade_V_and_Above_4.xlsx', 'cover.png', 'secure_document.xlsx')