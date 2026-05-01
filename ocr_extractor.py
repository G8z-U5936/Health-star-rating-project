from PIL import Image
import pytesseract
import os

class TextExtractor:
    def extract_text(self, image_path):
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                raise FileNotFoundError("Image file does not exist")

            # Resource management using context manager
            with Image.open(image_path) as img:
                text = pytesseract.image_to_string(img, lang='eng')

            return text

        except FileNotFoundError as e:
            print(f"File Error: {e}")

        except Exception as e:
            print(f"Unexpected Error: {e}")
