#!/usr/bin/env python3
"""
Health Star Rating (HSR) Calculator
Based on the Australian Health Star Rating System

This calculator implements the HSR algorithm as defined in:
- HSR Calculator 4.2.xlsm
- FSANZ NPSC (Nutrient Profiling Scoring Criterion)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional 
import bisect


class HSRCategory(Enum):
    """HSR Food Categories"""
    DAIRY_BEVERAGES = "1D - Dairy beverages"
    FOODS = "2 - Foods"
    DAIRY_FOODS = "2D - Dairy foods"
    FATS_OILS = "3 - Fats, oils"
    CHEESE = "3D - Cheese"


class NPSCCategory(Enum):
    """NPSC Category Groups"""
    BEVERAGES = 1  # Category 1
    FOOD = 2       # Category 2
    FATS_OILS_CHEESE = 3  # Category 3


@dataclass
class NutrientInput:
    """Nutrient values per 100g"""
    energy_kj: float = 0.0
    saturated_fat_g: float = 0.0
    total_sugars_g: float = 0.0
    sodium_mg: float = 0.0
    fibre_g: float = 0.0
    protein_g: float = 0.0
    concentrated_fvnl_percent: float = 0.0  # Concentrated Fruit/Veg %
    fvnl_percent: float = 0.0  # Fruit, Veg, Nuts, Legumes %


@dataclass
class HSRResult:
    """HSR Calculation Result"""
    hsr_category: str
    npsc_category: int
    baseline_energy_points: int
    baseline_sat_fat_points: int
    baseline_sugar_points: int
    baseline_sodium_points: int
    total_baseline_points: int
    modifying_fvnl_points: int
    modifying_fibre_points: int
    modifying_protein_points: int
    total_modifying_points: int
    hsr_profiler_score: int
    hsr_star_points: int
    health_star_rating: float


# ============================================================================
# LOOKUP TABLES
# ============================================================================

# HSR Category to NPSC Category mapping
HSR_TO_NPSC = {
    "1D - Dairy beverages": (1, "Beverages"),
    "2 - Foods": (2, "Food"),
    "2D - Dairy foods": (2, "Food"),
    "3 - Fats, oils": (3, "Fats/Oils/Cheese"),
    "3D - Cheese": (3, "Fats/Oils/Cheese"),
}

# Short code to full category mapping (for convenience)
SHORT_TO_FULL_CATEGORY = {
    "1D": "1D - Dairy beverages",
    "2": "2 - Foods",
    "2D": "2D - Dairy foods",
    "3": "3 - Fats, oils",
    "3D": "3D - Cheese",
}

# Star points to Health Star Rating mapping (Lookups A1:B11)
STAR_POINTS_TO_HSR = {
    1: 0.5,
    2: 1.0,
    3: 1.5,
    4: 2.0,
    5: 2.5,
    6: 3.0,
    7: 3.5,
    8: 4.0,
    9: 4.5,
    10: 5.0,
}

# Calibration endpoints by HSR Category (Lookups A55:D64)
# Format: {category: (less_healthy_endpoint, more_healthy_endpoint, range)}
CATEGORY_ENDPOINTS = {
    "1D - Dairy beverages": (6, -2, 8),
    "2 - Foods": (29, -15, 44),
    "2D - Dairy foods": (14, -3, 17),
    "3 - Fats, oils": (45, 10, 35),
    "3D - Cheese": (41, 23, 18),
}

# Star increment by category (Lookups C2:D11)
# Category -> star increment value
STAR_INCREMENT = {
    "1D - Dairy beverages": 0.8,  # range/10 = 8/10
    "2 - Foods": 4.4,             # range/10 = 44/10
    "2D - Dairy foods": 1.7,      # range/10 = 17/10
    "3 - Fats, oils": 3.5,        # range/10 = 35/10
    "3D - Cheese": 1.8,           # range/10 = 18/10
}

# ============================================================================
# POINTS TABLE A - Baseline Points
# ============================================================================

# Category 1 & 2 Foods - Extended tables
TABLE_A_CAT12 = {
    'energy': [
        (0, 0), (335.01, 1), (670.01, 2), (1005.01, 3), (1340.01, 4),
        (1675.01, 5), (2010.01, 6), (2345.01, 7), (2680.01, 8), (3015.01, 9),
        (3350.01, 10), (3685.01, 11)
    ],
    'sat_fat': [
        (0, 0), (1.01, 1), (2.01, 2), (3.01, 3), (4.01, 4), (5.01, 5),
        (6.01, 6), (7.01, 7), (8.01, 8), (9.01, 9), (10.01, 10),
        (11.21, 11), (12.51, 12), (13.91, 13), (15.51, 14), (17.31, 15),
        (19.31, 16), (21.61, 17), (24.11, 18), (26.91, 19), (30.01, 20),
        (33.51, 21), (37.41, 22), (41.71, 23), (46.61, 24), (52.01, 25),
        (58.01, 26), (64.71, 27), (72.31, 28), (80.61, 29), (90.01, 30)
    ],
    'sugar': [
        (0, 0), (5.01, 1), (8.91, 2), (12.81, 3), (16.81, 4), (20.71, 5),
        (24.61, 6), (28.51, 7), (32.41, 8), (36.31, 9), (40.31, 10),
        (44.21, 11), (48.11, 12), (52.01, 13), (55.91, 14), (59.81, 15),
        (63.81, 16), (67.71, 17), (71.61, 18), (75.51, 19), (79.41, 20),
        (83.31, 21), (87.31, 22), (91.21, 23), (95.11, 24), (99.01, 25)
    ],
    'sodium': [
        (0, 0), (90.01, 1), (180.01, 2), (270.01, 3), (360.01, 4),
        (450.01, 5), (540.01, 6), (630.01, 7), (720.01, 8), (810.01, 9),
        (900.01, 10), (990.01, 11), (1080.01, 12), (1170.01, 13),
        (1260.01, 14), (1350.01, 15), (1440.01, 16), (1530.01, 17),
        (1620.01, 18), (1710.01, 19), (1800.01, 20), (1890.01, 21),
        (1980.01, 22), (2070.01, 23), (2160.01, 24), (2250.01, 25),
        (2340.01, 26), (2430.01, 27), (2520.01, 28), (2610.01, 29),
        (2700.01, 30)
    ]
}

# Category 3 Foods (Fats, Oils, Cheese) - Linear tables as per HC Standard 1.2.7
TABLE_A_CAT3 = {
    'energy': [
        (0, 0), (335.01, 1), (670.01, 2), (1005.01, 3), (1340.01, 4),
        (1675.01, 5), (2010.01, 6), (2345.01, 7), (2680.01, 8), (3015.01, 9),
        (3350.01, 10), (3685.01, 11)
    ],
    'sat_fat': [
        (0, 0), (1.01, 1), (2.01, 2), (3.01, 3), (4.01, 4), (5.01, 5),
        (6.01, 6), (7.01, 7), (8.01, 8), (9.01, 9), (10.01, 10),
        (11.01, 11), (12.01, 12), (13.01, 13), (14.01, 14), (15.01, 15),
        (16.01, 16), (17.01, 17), (18.01, 18), (19.01, 19), (20.01, 20),
        (21.01, 21), (22.01, 22), (23.01, 23), (24.01, 24), (25.01, 25),
        (26.01, 26), (27.01, 27), (28.01, 28), (29.01, 29), (30.01, 30)
    ],
    'sugar': [
        (0, 0), (5.01, 1), (9.01, 2), (13.51, 3), (18.01, 4), (22.51, 5),
        (27.01, 6), (31.01, 7), (36.01, 8), (40.01, 9), (45.01, 10)
    ],
    'sodium': [
        (0, 0), (90.01, 1), (180.01, 2), (270.01, 3), (360.01, 4),
        (450.01, 5), (540.01, 6), (630.01, 7), (720.01, 8), (810.01, 9),
        (900.01, 10), (990.01, 11), (1080.01, 12), (1170.01, 13),
        (1260.01, 14), (1350.01, 15), (1440.01, 16), (1530.01, 17),
        (1620.01, 18), (1710.01, 19), (1800.01, 20), (1890.01, 21),
        (1980.01, 22), (2070.01, 23), (2160.01, 24), (2250.01, 25),
        (2340.01, 26), (2430.01, 27), (2520.01, 28), (2610.01, 29),
        (2700.01, 30)
    ]
}

# ============================================================================
# POINTS TABLE C - Modifying Points
# ============================================================================

# Concentrated FVNL points (Column A)
TABLE_C_CONC_FVNL = [
    (0, 0), (25, 1), (43, 2), (52, 3), (63, 4),
    (67, 5), (80, 6), (90, 7), (99.5, 8), (100, 9)
]

# FVNL % points (Column B)
TABLE_C_FVNL = [
    (0, 0), (40.01, 1), (60.01, 2), (67.01, 3), (75.01, 4),
    (80.01, 5), (90.01, 6), (95.01, 7), (99.51, 8), (100, 9)
]

# Fibre points (Column C)
TABLE_C_FIBRE = [
    (0, 0), (0.91, 1), (1.91, 2), (2.81, 3), (3.71, 4),
    (4.71, 5), (5.41, 6), (6.31, 7), (7.31, 8), (8.41, 9),
    (9.71, 10), (11.21, 11), (13.01, 12), (15.01, 13),
    (17.31, 14), (20.01, 15)
]

# Protein points (Column D)
TABLE_C_PROTEIN = [
    (0, 0), (1.61, 1), (3.2, 2), (4.81, 3), (6.41, 4),
    (8.01, 5), (9.61, 6), (11.61, 7), (13.91, 8), (16.71, 9),
    (20.01, 10), (24.01, 11), (28.91, 12), (34.71, 13),
    (41.61, 14), (50.01, 15)
]

# ============================================================================
# CONSTANTS
# ============================================================================

A_TIPPING_POINT = 13  # Lookups C106
FVNL_TIPPING_POINT = 5  # Lookups C120


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def lookup_points(value: float, table: list) -> int:
    """
    Lookup points from a table using VLOOKUP-like logic.
    The table is a list of (threshold, points) tuples.
    Returns the points for the highest threshold <= value.
    """
    if value < 0:
        value = 0
    
    points = 0
    for threshold, pts in table:
        if value >= threshold:
            points = pts
        else:
            break
    return points


def normalize_category(hsr_category: str) -> str:
    """
    Normalize HSR category - accepts both short codes and full names.
    Examples: "1D" -> "1D - Dairy beverages", "2 - Foods" -> "2 - Foods"
    """
    # If it's a short code, convert to full name
    if hsr_category in SHORT_TO_FULL_CATEGORY:
        return SHORT_TO_FULL_CATEGORY[hsr_category]
    # If it's already a full name, return as-is
    if hsr_category in HSR_TO_NPSC:
        return hsr_category
    raise ValueError(f"Unknown HSR category: {hsr_category}. Valid: {list(SHORT_TO_FULL_CATEGORY.keys())}")


def get_npsc_category(hsr_category: str) -> int:
    """Get NPSC category number from HSR category"""
    full_category = normalize_category(hsr_category)
    return HSR_TO_NPSC[full_category][0]


def calculate_weighted_fvnl(conc_fvnl: float, fvnl: float) -> float:
    """
    Calculate weighted FVNL percentage.
    Formula: 100 * (FVNL + 2*ConcentratedFVNL) / (FVNL + 2*ConcentratedFVNL + (100 - ConcentratedFVNL - FVNL))
    """
    numerator = fvnl + 2 * conc_fvnl
    denominator = fvnl + 2 * conc_fvnl + (100 - conc_fvnl - fvnl)
    
    if denominator == 0:
        return 0.0
    
    return round(100 * numerator / denominator, 2)


def is_all_concentrated_fvnl(conc_fvnl: float, fvnl: float) -> bool:
    """Check if all fruit/veg is concentrated (no regular FVNL)"""
    return conc_fvnl > 0 and fvnl == 0


# ============================================================================
# MAIN CALCULATION FUNCTIONS
# ============================================================================

def calculate_baseline_points(nutrients: NutrientInput, npsc_category: int) -> dict:
    """
    Calculate baseline points (Table A) for energy, sat fat, sugars, and sodium.
    Returns dict with individual and total baseline points.
    """
    # Select table based on NPSC category
    if npsc_category == 3:
        table = TABLE_A_CAT3
    else:
        table = TABLE_A_CAT12
    
    energy_points = lookup_points(nutrients.energy_kj, table['energy'])
    sat_fat_points = lookup_points(nutrients.saturated_fat_g, table['sat_fat'])
    sugar_points = lookup_points(nutrients.total_sugars_g, table['sugar'])
    sodium_points = lookup_points(nutrients.sodium_mg, table['sodium'])
    
    total = energy_points + sat_fat_points + sugar_points + sodium_points
    
    return {
        'energy': energy_points,
        'sat_fat': sat_fat_points,
        'sugar': sugar_points,
        'sodium': sodium_points,
        'total': total
    }


def calculate_modifying_points(
    nutrients: NutrientInput,
    npsc_category: int,
    total_baseline: int,
    all_conc_fvnl: bool
) -> dict:
    """
    Calculate modifying points (Table C) for FVNL, fibre, and protein.
    Returns dict with individual and total modifying points.
    """
    # Calculate FVNL points
    if all_conc_fvnl:
        # Use concentrated FVNL table
        fvnl_points = lookup_points(nutrients.concentrated_fvnl_percent, TABLE_C_CONC_FVNL)
    else:
        # Use weighted FVNL
        weighted_fvnl = calculate_weighted_fvnl(
            nutrients.concentrated_fvnl_percent,
            nutrients.fvnl_percent
        )
        fvnl_points = lookup_points(weighted_fvnl, TABLE_C_FVNL)
    
    # Calculate fibre points (Category 1 Beverages get 0 fibre points)
    if npsc_category == 1:
        fibre_points = 0
    else:
        fibre_points = lookup_points(nutrients.fibre_g, TABLE_C_FIBRE)
    
    # Calculate protein points
    protein_points = lookup_points(nutrients.protein_g, TABLE_C_PROTEIN)
    
    # Determine total modifying points based on rules
    # If baseline < 13 (A_TIPPING_POINT): count all modifying points
    # Else if FVNL points >= 5 (FVNL_TIPPING_POINT): count all modifying points
    # Else: count only FVNL + Fibre (no protein)
    
    if total_baseline < A_TIPPING_POINT:
        total = fvnl_points + fibre_points + protein_points
    elif fvnl_points >= FVNL_TIPPING_POINT:
        total = fvnl_points + fibre_points + protein_points
    else:
        total = fvnl_points + fibre_points
    
    return {
        'fvnl': fvnl_points,
        'fibre': fibre_points,
        'protein': protein_points,
        'total': total
    }


def calculate_hsr_star_points(
    hsr_profiler_score: int,
    hsr_category: str
) -> int:
    """
    Calculate HSR star points from profiler score.
    Formula: ROUND(10.499 - ((score - more_healthy_endpoint) / range) * 10)
    Clamped between 1 and 10.
    """
    hsr_category = normalize_category(hsr_category)
    if hsr_category not in CATEGORY_ENDPOINTS:
        raise ValueError(f"Unknown HSR category: {hsr_category}")
    
    less_healthy, more_healthy, score_range = CATEGORY_ENDPOINTS[hsr_category]
    
    # Calculate star points
    # Formula from Excel: 10.499 - ((N - more_healthy) / range) * 10
    if score_range == 0:
        star_points = 10
    else:
        star_points = round(10.499 - ((hsr_profiler_score - more_healthy) / score_range) * 10)
    
    # Clamp between 1 and 10
    star_points = max(1, min(10, star_points))
    
    return star_points


def calculate_health_star_rating(star_points: int) -> float:
    """Convert star points to Health Star Rating (0.5 to 5.0)"""
    return STAR_POINTS_TO_HSR.get(star_points, 0.5)


def calculate_hsr(
    nutrients: NutrientInput,
    hsr_category: str
) -> HSRResult:
    """
    Calculate the complete Health Star Rating for a food product.
    
    Args:
        nutrients: NutrientInput with all nutrient values per 100g
        hsr_category: HSR category - accepts short codes ("1D", "2", "2D", "3", "3D")
                      or full names ("1D - Dairy beverages", "2 - Foods", etc.)
    
    Returns:
        HSRResult with all intermediate and final values
    """
    # Normalize category (accepts both "1D" and "1D - Dairy beverages")
    hsr_category = normalize_category(hsr_category)
    
    # Get NPSC category
    npsc_category = get_npsc_category(hsr_category)
    
    # Check if all FVNL is concentrated
    all_conc_fvnl = is_all_concentrated_fvnl(
        nutrients.concentrated_fvnl_percent,
        nutrients.fvnl_percent
    )
    
    # Calculate baseline points (Table A)
    baseline = calculate_baseline_points(nutrients, npsc_category)
    
    # Calculate modifying points (Table C)
    modifying = calculate_modifying_points(
        nutrients, npsc_category, baseline['total'], all_conc_fvnl
    )
    
    # Calculate HSR Profiler Score
    hsr_profiler_score = baseline['total'] - modifying['total']
    
    # Calculate HSR Star Points
    star_points = calculate_hsr_star_points(hsr_profiler_score, hsr_category)
    
    # Get Health Star Rating
    health_star_rating = calculate_health_star_rating(star_points)
    
    return HSRResult(
        hsr_category=hsr_category,
        npsc_category=npsc_category,
        baseline_energy_points=baseline['energy'],
        baseline_sat_fat_points=baseline['sat_fat'],
        baseline_sugar_points=baseline['sugar'],
        baseline_sodium_points=baseline['sodium'],
        total_baseline_points=baseline['total'],
        modifying_fvnl_points=modifying['fvnl'],
        modifying_fibre_points=modifying['fibre'],
        modifying_protein_points=modifying['protein'],
        total_modifying_points=modifying['total'],
        hsr_profiler_score=hsr_profiler_score,
        hsr_star_points=star_points,
        health_star_rating=health_star_rating
    )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_hsr_categories() -> list:
    """Return list of valid HSR categories"""
    return list(HSR_TO_NPSC.keys())


def print_result(result: HSRResult):
    """Pretty print the HSR calculation result"""
    print("\n" + "=" * 60)
    print("HEALTH STAR RATING CALCULATION RESULT")
    print("=" * 60)
    print(f"\nCategory: {result.hsr_category}")
    print(f"NPSC Category: {result.npsc_category}")
    
    print("\n--- Baseline Points (Table A) ---")
    print(f"  Energy Points:      {result.baseline_energy_points}")
    print(f"  Saturated Fat:      {result.baseline_sat_fat_points}")
    print(f"  Total Sugars:       {result.baseline_sugar_points}")
    print(f"  Sodium:             {result.baseline_sodium_points}")
    print(f"  TOTAL BASELINE:     {result.total_baseline_points}")
    
    print("\n--- Modifying Points (Table C) ---")
    print(f"  FVNL Points:        {result.modifying_fvnl_points}")
    print(f"  Fibre Points:       {result.modifying_fibre_points}")
    print(f"  Protein Points:     {result.modifying_protein_points}")
    print(f"  TOTAL MODIFYING:    {result.total_modifying_points}")
    
    print("\n--- Final Results ---")
    print(f"  HSR Profiler Score: {result.hsr_profiler_score}")
    print(f"  HSR Star Points:    {result.hsr_star_points}")
    print(f"  HEALTH STAR RATING: {result.health_star_rating} ⭐")
    print("=" * 60)


# ============================================================================
# MAIN - DEMO
# ============================================================================

if __name__ == "__main__":
    print("Health Star Rating Calculator")
    print("-" * 40)
    
    # Example 1: Regular food product
    print("\nExample 1: Cereal Bar")
    nutrients1 = NutrientInput(
        energy_kj=1680,
        saturated_fat_g=5.2,
        total_sugars_g=22.0,
        sodium_mg=180,
        fibre_g=3.5,
        protein_g=6.0,
        concentrated_fvnl_percent=0,
        fvnl_percent=25
    )
    result1 = calculate_hsr(nutrients1, "2 - Foods")
    print_result(result1)
    
    # Example 2: Dairy product
    print("\nExample 2: Yogurt")
    nutrients2 = NutrientInput(
        energy_kj=450,
        saturated_fat_g=2.5,
        total_sugars_g=12.0,
        sodium_mg=60,
        fibre_g=0,
        protein_g=5.0,
        concentrated_fvnl_percent=0,
        fvnl_percent=15
    )
    result2 = calculate_hsr(nutrients2, "2D - Dairy foods")
    print_result(result2)
    
    # Example 3: Cheese
    print("\nExample 3: Cheddar Cheese")
    nutrients3 = NutrientInput(
        energy_kj=1680,
        saturated_fat_g=21.0,
        total_sugars_g=0.5,
        sodium_mg=620,
        fibre_g=0,
        protein_g=25.0,
        concentrated_fvnl_percent=0,
        fvnl_percent=0
    )
    result3 = calculate_hsr(nutrients3, "3D - Cheese")
    print_result(result3)
    
    # Example 4: Olive Oil
    print("\nExample 4: Olive Oil")
    nutrients4 = NutrientInput(
        energy_kj=3390,
        saturated_fat_g=14.0,
        total_sugars_g=0,
        sodium_mg=0,
        fibre_g=0,
        protein_g=0,
        concentrated_fvnl_percent=0,
        fvnl_percent=0
    )
    result4 = calculate_hsr(nutrients4, "3 - Fats, oils")
    print_result(result4)
    
    # Interactive mode
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("\nAvailable HSR Categories:")
    for i, cat in enumerate(get_hsr_categories(), 1):
        print(f"  {i}. {cat}")
