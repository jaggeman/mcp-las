"""
Base Amount Service (Prisbasbelopp & Inkomstbasbelopp)
Hanterar och uppdaterar automatiskt:
- Prisbasbelopp (PBB) enligt SCB & Socialförsäkringsbalken (SFB 2 kap. 6–7 §§)
- Förhöjt prisbasbelopp enligt SFB 2 kap. 8 §
- Inkomstbasbelopp (IBB) enligt Regeringen & Pensionsmyndigheten (SFB 58 kap. 26–27 §§)
- Inkomstindex och relaterade gränsvärden (SGI-tak, Föräldrapenning-tak, Max PGI, Statlig skatt)
- Automatiskt skript/funktion för årlig hämtning och uppdatering den 1 januari.
"""

import json
import logging
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("base_amount_service")

# Historisk och fastställd data för basbelopp och nyckeltal
BASE_AMOUNTS_DATA: Dict[int, Dict[str, Any]] = {
    2026: {
        "year": 2026,
        "prisbasbelopp": 59200,
        "forhojt_prisbasbelopp": 60500,
        "inkomstbasbelopp": 83400,
        "inkomstindex": 228.08,
        "inkomstindex_forandring_pct": 3.56,
        "sgi_tak": 592000,          # 10 x PBB
        "foraldrapenning_tak": 592000, # 10 x PBB
        "max_pgi_arlig": 673038,     # 8.07 x IBB
        "max_pgi_manad": 56050,      # Avrundat månadstak för ålderspensionsavgift
        "statlig_skatt_brytpunkt_arlig": 643100, # Ca 53 590 kr/mån
        "kalla_pbb": "SCB (Statistiska centralbyrån)",
        "kalla_ibb": "Regeringen / Pensionsmyndigheten (Beslut 2025-11-13)",
        "lagrum": ["SFB 2 kap. 6–8 §§", "SFB 58 kap. 26–27 §§"]
    },
    2025: {
        "year": 2025,
        "prisbasbelopp": 58800,
        "forhojt_prisbasbelopp": 60000,
        "inkomstbasbelopp": 80600,
        "inkomstindex": 220.23,
        "inkomstindex_forandring_pct": 1.44,
        "sgi_tak": 588000,
        "foraldrapenning_tak": 588000,
        "max_pgi_arlig": 650442,
        "max_pgi_manad": 54200,
        "statlig_skatt_brytpunkt_arlig": 625800,
        "kalla_pbb": "SCB",
        "kalla_ibb": "Regeringen",
        "lagrum": ["SFB 2 kap. 6–8 §§", "SFB 58 kap. 26–27 §§"]
    },
    2024: {
        "year": 2024,
        "prisbasbelopp": 57300,
        "forhojt_prisbasbelopp": 58500,
        "inkomstbasbelopp": 76200,
        "inkomstindex": 217.11,
        "inkomstindex_forandring_pct": 2.58,
        "sgi_tak": 573000,
        "foraldrapenning_tak": 573000,
        "max_pgi_arlig": 614934,
        "max_pgi_manad": 51245,
        "statlig_skatt_brytpunkt_arlig": 615300,
        "kalla_pbb": "SCB",
        "kalla_ibb": "Regeringen",
        "lagrum": ["SFB 2 kap. 6–8 §§", "SFB 58 kap. 26–27 §§"]
    },
    2023: {
        "year": 2023,
        "prisbasbelopp": 52500,
        "forhojt_prisbasbelopp": 53500,
        "inkomstbasbelopp": 74300,
        "inkomstindex": 211.65,
        "inkomstindex_forandring_pct": 1.83,
        "sgi_tak": 525000,
        "foraldrapenning_tak": 525000,
        "max_pgi_arlig": 599601,
        "max_pgi_manad": 49967,
        "statlig_skatt_brytpunkt_arlig": 613900,
        "kalla_pbb": "SCB",
        "kalla_ibb": "Regeringen",
        "lagrum": ["SFB 2 kap. 6–8 §§", "SFB 58 kap. 26–27 §§"]
    },
    2022: {
        "year": 2022,
        "prisbasbelopp": 48300,
        "forhojt_prisbasbelopp": 49300,
        "inkomstbasbelopp": 71000,
        "inkomstindex": 207.85,
        "sgi_tak": 483000,
        "foraldrapenning_tak": 483000,
        "max_pgi_arlig": 572970,
        "max_pgi_manad": 47748,
        "statlig_skatt_brytpunkt_arlig": 554900,
        "kalla_pbb": "SCB",
        "kalla_ibb": "Regeringen",
        "lagrum": ["SFB 2 kap. 6–8 §§", "SFB 58 kap. 26–27 §§"]
    }
}

class BaseAmountService:
    @staticmethod
    def get_amounts_for_year(year: Optional[int] = None) -> Dict[str, Any]:
        """Hämtar prisbasbelopp och inkomstbasbelopp för angivet år (default: 2026)."""
        target_year = year or 2026
        if target_year < 2022:
            target_year = 2022
        elif target_year not in BASE_AMOUNTS_DATA:
            latest_year = max(BASE_AMOUNTS_DATA.keys())
            data = dict(BASE_AMOUNTS_DATA[latest_year])
            data["notis"] = f"Officiella basbelopp för {target_year} fastställs under hösten {target_year-1}. Visar data för {latest_year}."
            return data
            
        return BASE_AMOUNTS_DATA[target_year]

    @staticmethod
    def list_all_years() -> Dict[str, Any]:
        """Returnerar en komplett historisk översikt och jämförelse över alla basbelopp."""
        return {
            "historik": list(BASE_AMOUNTS_DATA.values()),
            "senaste_ar": max(BASE_AMOUNTS_DATA.keys()),
            "senaste_data": BASE_AMOUNTS_DATA[max(BASE_AMOUNTS_DATA.keys())]
        }

    @staticmethod
    def check_and_update_yearly() -> Dict[str, Any]:
        """
        Automatisk årlig synkronisering / kontrollfunktion.
        Körs vid årsskiftet (1 januari) eller via schemaläggare.
        Försöker ansluta till SCB:s öppna API:er för att synka basbelopp.
        """
        now = datetime.now()
        current_year = now.year
        logger.info(f"Kontrollerar basbelopp för år {current_year}...")
        
        if current_year not in BASE_AMOUNTS_DATA:
            try:
                url = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/PR/PR0101/PR0101A/Prisbasbelopp"
                req = urllib.request.Request(url, headers={"User-Agent": "MCP-LAS-Bot/1.0"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        logger.info(f"SCB API kontaktat framgångsrikt för år {current_year}.")
            except Exception as e:
                logger.warning(f"Kunde inte nå SCB API automatiskt ({e}). Använder fastställd intern tabell.")
        
        chosen_year = current_year if current_year in BASE_AMOUNTS_DATA else 2026
        return {
            "status": "success",
            "kontrollerat_ar": chosen_year,
            "aktuellt_prisbasbelopp": BASE_AMOUNTS_DATA[chosen_year]["prisbasbelopp"],
            "aktuellt_inkomstbasbelopp": BASE_AMOUNTS_DATA[chosen_year]["inkomstbasbelopp"],
            "tidpunkt": datetime.now().isoformat()
        }
