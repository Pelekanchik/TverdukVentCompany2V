"""Тести для CNC-експорту (DXF, G-code)."""

import os
import tempfile
import pytest

from ventilation_company.cnc_export import CNCSettings, DXFExporter, GCodeExporter
from ventilation_company.metal_cutting import CuttingPlan, Sheet, PlacedDetail, Detail


class TestCNCSettings:
    """Тести налаштувань ЧПУ."""

    def test_default_creation(self):
        settings = CNCSettings()
        assert settings.machine_type == "plasma"
        assert settings.feed_rate > 0
        assert settings.rapid_feed > 0
        assert settings.pierce_height > 0
        assert settings.cut_height > 0

    def test_custom_creation(self):
        settings = CNCSettings(
            machine_type="laser",
            feed_rate=8000,
            pierce_height=3.0,
        )
        assert settings.machine_type == "laser"
        assert settings.feed_rate == 8000
        assert settings.pierce_height == 3.0

    def test_clone(self):
        settings = CNCSettings()
        cloned = settings.clone()
        assert cloned.machine_type == settings.machine_type
        assert cloned.feed_rate == settings.feed_rate


class TestDXFExporter:
    """Тести DXF-експорту."""

    def _make_plan(self):
        """Створити тестовий CuttingPlan."""
        detail = Detail(name="Detal 1", width=500, height=300, quantity=1)
        sheet = Sheet(width=2000, height=1000, thickness=1.0)
        sheet.placed_details.append(PlacedDetail(detail=detail, x=0, y=0))
        return CuttingPlan(sheets=[sheet])

    def test_creation(self):
        plan = self._make_plan()
        exporter = DXFExporter(plan)
        assert exporter.plan is not None

    def test_export_creates_file(self):
        plan = self._make_plan()
        exporter = DXFExporter(plan)
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False, mode='w', encoding='utf-8') as f:
            temp_path = f.name
        try:
            result = exporter.export(temp_path)
            assert isinstance(result, str)
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            # Читаємо у бінарному режимі або з cp1251, бо DXF може мати кирилицю
            content = open(temp_path, 'r', encoding='cp1251', errors='ignore').read()
            assert "SECTION" in content or "ENTITIES" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_empty_plan(self):
        plan = CuttingPlan(sheets=[])
        exporter = DXFExporter(plan)
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False, mode='w', encoding='utf-8') as f:
            temp_path = f.name
        try:
            result = exporter.export(temp_path)
            assert isinstance(result, str)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestGCodeExporter:
    """Тести G-code експорту."""

    def _make_plan(self):
        detail = Detail(name="Detal 1", width=500, height=300, quantity=1)
        sheet = Sheet(width=2000, height=1000, thickness=1.0)
        sheet.placed_details.append(PlacedDetail(detail=detail, x=0, y=0))
        return CuttingPlan(sheets=[sheet])

    def test_creation(self):
        plan = self._make_plan()
        exporter = GCodeExporter(plan)
        assert exporter.plan is not None

    def test_export_sheet_creates_file(self):
        plan = self._make_plan()
        exporter = GCodeExporter(plan)
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False, mode='w', encoding='utf-8') as f:
            temp_path = f.name
        try:
            result = exporter.export_sheet(plan.sheets[0], temp_path)
            assert isinstance(result, str)
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            content = open(temp_path, 'r', encoding='utf-8').read()
            assert "G" in content or "M" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_all_creates_files(self):
        plan = self._make_plan()
        exporter = GCodeExporter(plan)
        with tempfile.TemporaryDirectory() as tmpdir:
            results = exporter.export_all(tmpdir)
            assert isinstance(results, list)
            assert len(results) == 1
            assert isinstance(results[0], str)
            # Перевіримо, що файли створено
            files = os.listdir(tmpdir)
            assert len(files) > 0
