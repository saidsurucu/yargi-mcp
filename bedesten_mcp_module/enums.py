# bedesten_mcp_module/enums.py

from typing import Literal

# Unified compressed enum for both Yargıtay and Danıştay chambers
BirimAdiEnum = Literal[
    "ALL",  # All chambers
    
    # Yargıtay (Court of Cassation) - Civil Chambers
    "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10",
    "H11", "H12", "H13", "H14", "H15", "H16", "H17", "H18", "H19", "H20",
    "H21", "H22", "H23",
    
    # Yargıtay - Criminal Chambers
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20",
    "C21", "C22", "C23",
    
    # Yargıtay - Councils and Assemblies
    "HGK",   # Hukuk Genel Kurulu
    "CGK",   # Ceza Genel Kurulu
    "BGK",   # Büyük Genel Kurulu
    "HBK",   # Hukuk Daireleri Başkanlar Kurulu
    "CBK",   # Ceza Daireleri Başkanlar Kurulu
    
    # Danıştay (Council of State) - Chambers
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "D11", "D12", "D13", "D14", "D15", "D16", "D17",
    
    # Danıştay - Councils and Boards
    "DBGK",  # Büyük Gen.Kur. (Grand General Assembly)
    "IDDK",  # İdare Dava Daireleri Kurulu
    "VDDK",  # Vergi Dava Daireleri Kurulu
    "IBK",   # İçtihatları Birleştirme Kurulu
    "IIK",   # İdari İşler Kurulu
    "DBK",   # Başkanlar Kurulu
    
    # Military High Administrative Court
    "AYIM",   # Askeri Yüksek İdare Mahkemesi
    "AYIMDK", # Askeri Yüksek İdare Mahkemesi Daireler Kurulu
    "AYIMB",  # Askeri Yüksek İdare Mahkemesi Başsavcılığı
    "AYIM1",  # Askeri Yüksek İdare Mahkemesi 1. Daire
    "AYIM2",  # Askeri Yüksek İdare Mahkemesi 2. Daire
    "AYIM3"   # Askeri Yüksek İdare Mahkemesi 3. Daire
]

# Mapping from abbreviated values to full Turkish API values
BIRIM_ADI_MAPPING = {
    "ALL": None,  # Will be handled specially in client
    
    # Yargıtay Civil Chambers (1-23)
    "H1": "1. Hukuk Dairesi", "H2": "2. Hukuk Dairesi", "H3": "3. Hukuk Dairesi",
    "H4": "4. Hukuk Dairesi", "H5": "5. Hukuk Dairesi", "H6": "6. Hukuk Dairesi",
    "H7": "7. Hukuk Dairesi", "H8": "8. Hukuk Dairesi", "H9": "9. Hukuk Dairesi",
    "H10": "10. Hukuk Dairesi", "H11": "11. Hukuk Dairesi", "H12": "12. Hukuk Dairesi",
    "H13": "13. Hukuk Dairesi", "H14": "14. Hukuk Dairesi", "H15": "15. Hukuk Dairesi",
    "H16": "16. Hukuk Dairesi", "H17": "17. Hukuk Dairesi", "H18": "18. Hukuk Dairesi",
    "H19": "19. Hukuk Dairesi", "H20": "20. Hukuk Dairesi", "H21": "21. Hukuk Dairesi",
    "H22": "22. Hukuk Dairesi", "H23": "23. Hukuk Dairesi",
    
    # Yargıtay Criminal Chambers (1-23)
    "C1": "1. Ceza Dairesi", "C2": "2. Ceza Dairesi", "C3": "3. Ceza Dairesi",
    "C4": "4. Ceza Dairesi", "C5": "5. Ceza Dairesi", "C6": "6. Ceza Dairesi",
    "C7": "7. Ceza Dairesi", "C8": "8. Ceza Dairesi", "C9": "9. Ceza Dairesi",
    "C10": "10. Ceza Dairesi", "C11": "11. Ceza Dairesi", "C12": "12. Ceza Dairesi",
    "C13": "13. Ceza Dairesi", "C14": "14. Ceza Dairesi", "C15": "15. Ceza Dairesi",
    "C16": "16. Ceza Dairesi", "C17": "17. Ceza Dairesi", "C18": "18. Ceza Dairesi",
    "C19": "19. Ceza Dairesi", "C20": "20. Ceza Dairesi", "C21": "21. Ceza Dairesi",
    "C22": "22. Ceza Dairesi", "C23": "23. Ceza Dairesi",
    
    # Yargıtay Councils and Assemblies
    "HGK": "Hukuk Genel Kurulu",
    "CGK": "Ceza Genel Kurulu",
    "BGK": "Büyük Genel Kurulu",
    "HBK": "Hukuk Daireleri Başkanlar Kurulu",
    "CBK": "Ceza Daireleri Başkanlar Kurulu",
    
    # Danıştay Chambers (1-17)
    "D1": "1. Daire", "D2": "2. Daire", "D3": "3. Daire", "D4": "4. Daire",
    "D5": "5. Daire", "D6": "6. Daire", "D7": "7. Daire", "D8": "8. Daire",
    "D9": "9. Daire", "D10": "10. Daire", "D11": "11. Daire", "D12": "12. Daire",
    "D13": "13. Daire", "D14": "14. Daire", "D15": "15. Daire", "D16": "16. Daire",
    "D17": "17. Daire",
    
    # Danıştay Councils and Boards
    "DBGK": "Büyük Gen.Kur.",
    "IDDK": "İdare Dava Daireleri Kurulu",
    "VDDK": "Vergi Dava Daireleri Kurulu",
    "IBK": "İçtihatları Birleştirme Kurulu",
    "IIK": "İdari İşler Kurulu",
    "DBK": "Başkanlar Kurulu",
    
    # Military High Administrative Court
    "AYIM": "Askeri Yüksek İdare Mahkemesi",
    "AYIMDK": "Askeri Yüksek İdare Mahkemesi Daireler Kurulu",
    "AYIMB": "Askeri Yüksek İdare Mahkemesi Başsavcılığı",
    "AYIM1": "Askeri Yüksek İdare Mahkemesi 1. Daire",
    "AYIM2": "Askeri Yüksek İdare Mahkemesi 2. Daire",
    "AYIM3": "Askeri Yüksek İdare Mahkemesi 3. Daire"
}

# Helper function to get full Turkish name from abbreviated value
def get_full_birim_adi(abbreviated_value: str) -> str:
    """Convert abbreviated birimAdi value to full Turkish name for API calls."""
    if abbreviated_value == "ALL" or not abbreviated_value:
        return ""  # Empty string for ALL or None
    
    return BIRIM_ADI_MAPPING.get(abbreviated_value, abbreviated_value)

# Helper function to validate abbreviated value
def is_valid_birim_adi(abbreviated_value: str) -> bool:
    """Check if abbreviated birimAdi value is valid."""
    return abbreviated_value in BIRIM_ADI_MAPPING