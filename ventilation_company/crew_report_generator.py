"""Генератор PDF-звіту бригади про виконання робіт.

Спільна реалізація — у ventilation_company.crew_pdf_generator (клас CrewPDF,
режим mode="report"). Цей модуль — обгортка для зворотної сумісності імпортів.

Використання:
    generate_crew_report(works, crew, date_from, date_to, path, company)
"""

from __future__ import annotations

from ventilation_company.crew_pdf_generator import CrewPDF, generate_crew_report

__all__ = ["CrewPDF", "generate_crew_report"]
