# PDF Redaction and Image Extraction Tool

A small Flask web app for cleaning up photo directory PDFs, where each page is a grid of profile photos with a `LastName, FirstName` label under every photo. The app rewrites the names, extracts the photos, and lets you remove selected people from the document in a second step.

This is a portfolio version of a freelance project. The client's documents are not included, so you need your own PDF in this layout to try it.

## Features

- Upload a PDF through a simple web form.
- Rewrites names written as `LastName, FirstName` to `FirstName LastName` and removes the word "Individual" from the pages.
- Extracts the roughly square photos larger than 30 pt and saves each one as a 100x100 PNG in `uploads/`, named after the person on that page (or `Unnamed_N` if no name is found).
- Adds a checkbox form field above every photo and shows the modified PDF in the browser, with a download button.
- Upload the PDF again with some boxes ticked and the app removes each ticked photo together with the name printed under it, drops the checkboxes, and shows the final PDF for download.

## Tech Stack

- Python and Flask
- PyMuPDF for reading, editing and redacting the PDF
- Pillow for resizing and saving the extracted photos
- Bootstrap 5 (loaded from a CDN) for the pages

## Project Structure

```
app.py              Flask routes and PDF processing
requirements.txt    Python dependencies
templates/
  upload.html       upload form
  display.html      modified PDF with checkboxes
  remove.html       upload form for the ticked PDF
  final.html        final PDF with download link
uploads/            created at runtime for uploaded and processed files (not tracked)
```

## Setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/Hamza-Tahirr/PDF-Redaction-and-Image-Extraction-Tool.git
cd PDF-Redaction-and-Image-Extraction-Tool
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5001/ in your browser. No API keys or environment variables are needed.

## Usage

1. Upload a PDF on the start page. The modified PDF opens with a checkbox above each photo.
2. Tick the boxes for the photos you want to remove. You can do this in the browser's PDF viewer or download the file and use any PDF reader that supports form fields. Save the PDF.
3. Click **Remove Ticked Photos** and upload the saved PDF.
4. The final PDF, without the removed photos and the checkboxes, is shown with a **Download Final PDF** button.

## Limitations

- The processing is written for one layout: a grid of photos with the name directly below each photo. Other layouts will need changes to the size check and the name pattern in `app.py`.
- Photos are paired with names in the order they appear on the page, so the file names of the saved photos depend on that order.
- Uploaded and processed files stay in `uploads/` until you delete them.
- The app runs on Flask's development server and is meant for local use.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
