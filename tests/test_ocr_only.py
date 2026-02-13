from PIL import Image
import pytesseract

# 🔥 Make sure this matches your actual path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

image_path = r"workspaces/default/uploads/sample.jpg"  # change if needed

print("Testing OCR on:", image_path)

img = Image.open(image_path).convert("L")

text = pytesseract.image_to_string(img, lang="eng")

print("\nOCR OUTPUT:")
print("-" * 40)
print(text.strip() if text.strip() else "[No readable text found]")
print("-" * 40)
