from dotenv import load_dotenv
load_dotenv()
import os
import json
from ocr_extractor import TextExtractor
from llm_handler import LLMHandler
from hsr_calculator import NutrientInput, calculate_hsr, print_result

def analyze_product_with_status(image_path):
    """Generator that yields status updates during analysis."""
    extractor = TextExtractor()
    
    # Step 1: OCR
    yield ("step1", "Extracting text from image...")
    ocr_text = extractor.extract_text(image_path)
    yield ("step1_done", "OCR complete ✓")
    
    # Step 2: LLM parsing
    yield ("step2", "Parsing nutrition data with AI...")
    llm_handler = LLMHandler()
    nutrition_data = llm_handler.extract_nutrition(ocr_text)
    yield ("step2_done", "Nutrition data extracted ✓")
    
    # Step 3: Mapping
    yield ("step3", "Mapping nutrition data...")
    n = nutrition_data.get("nutrition_per_100g", {})
    nutrients = NutrientInput(
        energy_kj=n.get("energy_kj") or 0,
        saturated_fat_g=n.get("saturated_fat_g") or 0,
        total_sugars_g=n.get("total_sugars_g") or 0,
        sodium_mg=n.get("sodium_mg") or 0,
        fibre_g=n.get("fibre_g") or 0,
        protein_g=n.get("protein_g") or 0,
        concentrated_fvnl_percent=0,
        fvnl_percent=0
    )
    category = nutrition_data.get("category", "2")
    yield ("step3_done", "Data mapped ✓")
    
    # Step 4: Calculate HSR
    yield ("step4", "Calculating Health Star Rating...")
    hsr_result = calculate_hsr(nutrients, category)
    yield ("step4_done", "Rating calculated ✓")
    
    # Return final result
    result = {
        "stars": hsr_result.health_star_rating,
        "product_name": nutrition_data.get("product_name", "Unknown Product"),
        "nutrition": {
            "energy_kj": n.get("energy_kj", 0),
            "saturated_fat_g": n.get("saturated_fat_g", 0),
            "total_sugars_g": n.get("total_sugars_g", 0),
            "sodium_mg": n.get("sodium_mg", 0),
            "protein_g": n.get("protein_g", 0),
            "fibre_g": n.get("fibre_g", 0),
            "carbohydrates_g": n.get("carbohydrates_g", 0),
            "total_fat_g": n.get("total_fat_g", 0),
        }
    }
    yield ("complete", result)




