"""Генератор PDF-плану монтажних робіт для бригад.

Спільна реалізація — у ventilation_company.crew_pdf_generator (клас CrewPDF,
режим mode="plan"). Цей модуль — обгортка для зворотної сумісності імпортів.

Використання:
    generate_crew_plan(works, crew, date_from, date_to, path, company)
"""

from __future__ import annotations

from ventilation_company.crew_pdf_generator import CrewPDF, generate_crew_plan

__all__ = ["CrewPDF", "generate_crew_plan"]
