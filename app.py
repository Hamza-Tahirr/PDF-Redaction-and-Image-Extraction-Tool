import io
import os
import re

import pymupdf
from flask import Flask, render_template, request, send_from_directory, url_for
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_photo(bbox):
    """Check if the bounding box is roughly square and larger than 30pt (profile photos)."""
    width = bbox.x1 - bbox.x0
    height = bbox.y1 - bbox.y0
    return width > 30 and height > 30 and abs(width - height) < 5

def save_image(image_data, image_name):
    """Save image bytes to the uploads directory with the name from the PDF."""
    image = Image.open(io.BytesIO(image_data))
    image = image.resize((100, 100))
    image_path = os.path.join(UPLOAD_FOLDER, f'{image_name}.png')
    image.save(image_path)
    return image_path

def redact_names_and_individuals(page, name_pattern, word_to_remove):
    """Rewrite 'LastName, FirstName' as 'FirstName LastName' and remove the word 'Individual'."""
    text = page.get_text("text")
    names_on_page = []
    for match in name_pattern.finditer(text):
        first_name = match.group(2)
        last_name = match.group(1)
        new_name = f"{first_name} {last_name}"
        names_on_page.append(new_name)
        for inst in page.search_for(match.group()):
            page.add_redact_annot(inst, fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_text(inst[:2], new_name, fontsize=11, fontname="helv")

    for inst in page.search_for(word_to_remove):
        page.add_redact_annot(inst, fill=(1, 1, 1))
        page.apply_redactions()

    return names_on_page

def extract_images_from_page(doc, page, image_names):
    """Extract profile photos from a page using provided names."""
    images_on_pages = []
    image_index = 0
    for img in page.get_images(full=True):
        xref = img[0]
        img_bbox = pymupdf.Rect(page.get_image_bbox(img))
        if is_photo(img_bbox):
            base_image = doc.extract_image(xref)
            image_data = base_image["image"]
            if image_index < len(image_names):
                image_name = image_names[image_index]
            else:
                image_name = f"Unnamed_{image_index + 1}"
            image_path = save_image(image_data, image_name)
            images_on_pages.append({
                'x0': img_bbox.x0,
                'y0': img_bbox.y0,
                'x1': img_bbox.x1,
                'y1': img_bbox.y1,
                'image_path': image_path,
                'image_name': image_name
            })
            image_index += 1
    return images_on_pages

def process_pdf(input_pdf_path, output_pdf_path):
    """Replace names, extract photos and add a checkbox above each photo."""
    doc = pymupdf.open(input_pdf_path)
    name_pattern = re.compile(r'(\b[A-Z][a-zA-Z]+), ([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)')
    word_to_remove = "Individual"

    images_on_pages = []

    for page_num, page in enumerate(doc):
        names_on_page = redact_names_and_individuals(page, name_pattern, word_to_remove)
        page_images = extract_images_from_page(doc, page, names_on_page)

        for i, img in enumerate(page_images):
            checkbox_widget = pymupdf.Widget()
            checkbox_widget.rect = pymupdf.Rect(img['x0'], img['y0'] - 20, img['x0'] + 15, img['y0'])
            checkbox_widget.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            checkbox_widget.field_name = f"checkbox_{page_num}_{i}"
            checkbox_widget.field_value = "Off"
            page.add_widget(checkbox_widget)

        images_on_pages.extend([{'page': page_num, **img} for img in page_images])

    doc.save(output_pdf_path)
    doc.close()

    return images_on_pages

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    filename = secure_filename(file.filename) if file else ''

    if not filename:
        return "No selected file", 400

    input_pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    output_pdf_path = os.path.join(UPLOAD_FOLDER, f'modified_{filename}')

    file.save(input_pdf_path)

    images_on_pages = process_pdf(input_pdf_path, output_pdf_path)

    return render_template('display.html',
                           pdf_url=url_for('serve_pdf', filename=f'modified_{filename}'),
                           images=images_on_pages,
                           filename=f'modified_{filename}')

@app.route('/uploads/<filename>')
def serve_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/image/<image_name>')
def serve_image(image_name):
    return send_from_directory(UPLOAD_FOLDER, image_name)

@app.route('/remove')
def remove():
    return render_template('remove.html')

@app.route('/remove_upload', methods=['POST'])
def remove_upload():
    file = request.files.get('file')
    filename = secure_filename(file.filename) if file else ''

    if not filename:
        return "No selected file", 400

    input_pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_pdf_path)

    doc = pymupdf.open(input_pdf_path)

    for page in doc:
        words = page.get_text("words")
        checkboxes = [w for w in page.widgets() if w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX]
        for widget in checkboxes:
            if widget.field_value == "Yes":
                # The checkbox ends exactly where its photo starts, so extend it
                # a little downwards to make it overlap the photo.
                checkbox_rect = widget.rect + (0, 0, 0, 5)

                img_rects_to_remove = []
                text_below_img_rects_to_remove = []

                for img in page.get_images(full=True):
                    img_bbox = pymupdf.Rect(page.get_image_bbox(img))
                    if img_bbox.intersects(checkbox_rect):
                        img_rects_to_remove.append(img_bbox)

                # Names are often wider than the photo, so remove every word on
                # the text lines that start under it, not only the part inside.
                for img_rect in img_rects_to_remove:
                    text_below_rect = pymupdf.Rect(img_rect.x0, img_rect.y1, img_rect.x1, img_rect.y1 + 20)
                    lines = {(w[5], w[6]) for w in words if pymupdf.Rect(w[:4]).intersects(text_below_rect)}
                    text_below_img_rects_to_remove.extend(
                        pymupdf.Rect(w[:4]) for w in words if (w[5], w[6]) in lines
                    )

                for rect in img_rects_to_remove + text_below_img_rects_to_remove:
                    page.add_redact_annot(rect, fill=(1, 1, 1))

        for widget in checkboxes:
            page.delete_widget(widget)
        page.apply_redactions()

    final_filename = f'final_{filename}'
    doc.save(os.path.join(UPLOAD_FOLDER, final_filename))
    doc.close()

    return render_template('final.html',
                           pdf_url=url_for('serve_pdf', filename=final_filename),
                           filename=final_filename)

@app.route('/final/<filename>')
def final(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
