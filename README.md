# business-card-ocr

A small Flask web app for digitising business cards. Photograph or upload a card (front, or front and back), and the text is extracted with OCR and stored in MySQL so you can search your cards by any keyword.

## Features

- Upload the front only, or front and back, from the camera or the gallery. It works well from a phone on the same network.
- Preview the image and rotate it before submitting, so the OCR sees it upright.
- OCR with [docTR](https://github.com/mindee/doctr); the full recognised text is stored for each side.
- Live keyword search across all extracted text, with a thumbnail and snippet for each match.
- Detail page showing both sides of a card with their extracted text.
- Delete a card, which removes its database rows and image files.

## Tech stack

Python · Flask · MySQL · docTR (PyTorch) · Pillow · Bootstrap 5

## Project structure

```
business-card-ocr/
├── business_card_reader.py   # Flask app: routes for upload, search, detail, delete
├── utils/
│   └── bc_ocr.py             # docTR wrapper: image path in, text out
├── templates/                # start, upload, search and detail pages
├── schema.sql                # MySQL database + table
├── requirements.txt
└── static/cards/             # uploaded images (created at runtime, git-ignored)
```

## Running it

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create the database (MySQL 8):

   ```bash
   mysql -u root -p < schema.sql
   ```

3. Set the credentials as environment variables:

   ```
   DB_PASSWORD=your_mysql_password
   SECRET_KEY=any-random-string
   ```

   The database host and user default to `localhost` / `root`; change `DB_CONFIG` in `business_card_reader.py` if yours differ.

4. Run the app:

   ```bash
   python business_card_reader.py
   ```

   Open http://127.0.0.1:5200, or `http://<your-computer-ip>:5200` from a phone on the same network. The first run is slow while docTR downloads its models. Set `FLASK_DEBUG=1` if you want Flask's debug mode.

## How it works

1. The upload page rotates the image in the browser if needed, then posts it to `/upload`.
2. The server saves the image under `static/cards/` with a short random card ID, runs it through docTR, and stores the text in the `business_cards` table (one row per side).
3. If no back image is provided, a blank placeholder is stored for the back so every card always has two rows.
4. Search runs a `LIKE` query on the stored text.

## Known issues

- Search is plain substring matching, not fuzzy, and there is no parsing of the text into name, phone or email fields.
- OCR text is inserted into the search page as HTML, which is fine for personal use but should be escaped before exposing this to other users.
- No authentication, and the app listens on all network interfaces, so only run it on a trusted network.
- Uploaded images and card text are personal data, so the repository ignores `static/cards/`. Don't commit real cards.
