"""
Конфігурація системи вентиляційної виробничої фірми.

Тут лише структурні константи (шляхи, типи вентиляції).
Бізнес-дані (ціни, ПДВ, ставки) живуть у налаштуваннях:
  • PricingSettings      — data/pricing_settings.json (метал, націнки, зарплати/м²)
  • BusinessSettings     — data/business_settings.json (ПДВ, комплектуючі, посади)
"""

import os

from ventilation_company.paths import APP_ROOT as _APP_ROOT
from ventilation_company.paths import DATA_DIR as _DATA_DIR

BASE_DIR = str(_APP_ROOT)
DATA_DIR = str(_DATA_DIR)
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Виправлено: DB_PATH вказує на кореневу data/company.db (не ventilation_company/data/company.db)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "company.db")

VENTILATION_TYPES = [
    "припливна",
    "витяжна",
    "припливно-витяжна",
    "димовидалення",
    "кондиціонування",
]
