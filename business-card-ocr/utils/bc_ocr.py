import os
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# --- SETUP MODEL (load once, it's heavy) ---
model = ocr_predictor(pretrained=True)

def extract_text(image_path: str) -> str:
    """
    Extracts text from an image using docTR OCR.
    Returns the recognized text as a string.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image
    doc = DocumentFile.from_images(image_path)

    # Run OCR
    result = model(doc)

    # Convert structured result to text
    return result.render().strip()


# --- TESTING ---
if __name__ == "__main__":
    # 🔹 Replace this path with your own image
    test_img = "path/to/card_image.jpg"

    try:
        text = extract_text(test_img)
        print("===== OCR RESULT =====")
        print(text)
    except Exception as e:
        print(f"Error: {e}")
