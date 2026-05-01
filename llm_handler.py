import os
from openai import OpenAI
import json


NUTRITION_EXTRACTION_SYSTEM_PROMOT = """
    You are a nutrition label parser. Given OCR-extracted text from a food product image, extract and format the nutritional information cleanly.

    **Instructions:**
    1. Identify the NUTRITIONAL INFORMATION section from the text
    2. Fix common OCR errors (e.g., "hydrate" → "Carbohydrate", "turated" → "Saturated", missing letters)
    3. Extract: Serving Size, Energy (kJ), Carbohydrates, Sugars, Fat, Protein, Sodium, and any other nutrients present
    4. Output in a clean, structured format

    **Category Classification:**
    Classify the product into ONE of these categories:
    - "1D" - Dairy beverages (dairy-based drinks)
    - "2" - Foods (general food products)
    - "2D" - Dairy foods (yogurt, etc.)
    - "3" - Fats, oils
    - "3D" - Cheese products

    **Output Format:**
    ```json
    {
    "product_name": "<extracted or 'Unknown'>",
    "category": "<1D|2|2D|3|3D>",
    "serving_size": "<value with unit>",
    "servings_per_pack": "<number or 'N/A'>",
    "nutrition_per_100g": {
        "energy_kj": <number>,
        "carbohydrate_g": <number>,
        "total_sugars_g": <number>,
        "added_sugars_g": <number>,
        "total_fat_g": <number>,
        "saturated_fat_g": <number>,
        "trans_fat_g": <number>,
        "protein_g": <number>,
        "sodium_mg": <number>,
        "fibre_g": <number>
    },
    "nutrition_per_serve": {
        "energy_kj": <number>,
        "rda_percent": <number>
    },
    "allergens": ["<list of allergens>"],
    "key_ingredients": ["<top 3-5 main ingredients>"]
    }
"""


class LLMHandler:
    def __init__(self):
        self.client = OpenAI(
            base_url = "https://openrouter.ai/api/v1",
            api_key =  os.getenv("API_KEY"),
        )

    def extract_nutrition(self, ocr_text: str):
        client = self.client

        response = client.chat.completions.create(
            model = "openai/gpt-5.4-nano",
            messages = [
                {
                    "role": "system",
                    "content": NUTRITION_EXTRACTION_SYSTEM_PROMOT,
                },
                {
                    "role": "user",
                    "content": ocr_text
                }
            ],
            # Forces the model to output valid JSON
            response_format = {"type": "json_object"},
            extra_body = {
                "reasoning": {"enabled": True}
            }
        )

        # 1. Get the raw text content
        raw_content = response.choices[0].message.content
        
        # 2. Parse it into a Python Dictionary
        try:
            parsed_data = json.loads(raw_content)
            return parsed_data
        except json.JSONDecodeError:
            print("Model failed to provide valid JSON.")
            return raw_content
