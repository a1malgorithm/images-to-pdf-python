Image2PDF GUI — Convert Images to a Single PDF

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/ahmedsyntax)

Professional, user-friendly PyQt6 desktop app that converts images (JPG, JPEG, PNG, JFIF) into a single PDF. Polished UI with a blue gradient header and smooth workflow.

Highlights:
- Drag & drop images or folders directly.
- Manual reordering via drag to set page order.
- Batch add (folders/files), remove selected, clear list.
- Natural sorting (1, 2, 10) with A→Z / Z→A controls.
- PNG transparency flattened onto white automatically.
- Optional resize: max width/height (px) while preserving aspect ratio.
- DPI control for PDF page mapping.
- Progress bar and cancel during conversion.
- Optional “open after save”.

Requirements:
- Python 3.8+
- Pillow
- PyQt6

Installation:
- (Recommended) Create and activate a virtual environment.
- Install dependencies: `pip install -r requirements.txt`.

Usage:
- Run: `python main.py`
- Click “Add Folder…” or “Add Files…”, or drop images/folder into the app.
- Drag to reorder pages if needed.
- Set optional resize/DPI, then “Convert to PDF…”.

Notes:
- Very large batches may consume significant memory (Pillow requires all pages in memory before saving). Consider resizing to reduce memory usage.

Support:
- Need help or found a bug? Open an issue from the template chooser: ../../issues/new/choose
- See: SUPPORT.md for how to get support and request features.

Contributing:
- PRs are welcome. Please open a discussion/issue first for large changes.

License:
- Copyright (c) 2025 Ahmedsyntax (https://ahmedsyntax.com)
- Licensed under the MIT License. See LICENSE for details.
