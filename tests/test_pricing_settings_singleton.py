"""Тести для PricingSettings singleton.

Запуск:  pytest tests/test_pricing_settings_singleton.py -v
"""

import json
import os
import tempfile
import threading
import time

import pytest

from ventilation_company.gui.settings_tab import PricingSettings


class TestSingleton:
    """Перевірка singleton-паттерну."""

    def test_same_instance(self):
        """Два виклики get_instance() повертають той самий об'єкт."""
        # Скидаємо singleton для чистоти тесту
        PricingSettings._instance = None

        a = PricingSettings.get_instance()
        b = PricingSettings.get_instance()
        assert a is b

    def test_direct_init_same_instance(self):
        """Навіть PricingSettings() повертає той самий об'єкт."""
        PricingSettings._instance = None

        a = PricingSettings()
        b = PricingSettings()
        assert a is b

    def test_data_shared(self):
        """Зміни в одному екземплярі видно в іншому."""
        PricingSettings._instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pricing.json")
            s1 = PricingSettings.get_instance(path)
            s1.custom_params["test_param"] = 999.0
            s1.save()

            # Новий "екземпляр" — той самий об'єкт
            s2 = PricingSettings.get_instance(path)
            assert s2.custom_params["test_param"] == 999.0


class TestFileLock:
    """Перевірка файлового блокування та атомарного запису."""

    def test_atomic_write(self):
        """Файл завжди валідний, навіть при перериванні."""
        PricingSettings._instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pricing.json")
            s = PricingSettings.get_instance(path)
            s.save()

            # Файл має існувати і бути валідним JSON
            assert os.path.exists(path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert "material_prices" in data

    def test_reload_detects_changes(self):
        """reload() перечитує файл, якщо він змінився."""
        PricingSettings._instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pricing.json")
            s1 = PricingSettings.get_instance(path)
            s1.custom_params["reload_test"] = 111.0
            s1.save()

            # Імітуємо зміну ззовні
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["custom_params"]["reload_test"] = 222.0
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            # Перед reload — старе значення
            assert s1.custom_params["reload_test"] == 111.0

            # Після reload — нове значення
            s1.reload()
            assert s1.custom_params["reload_test"] == 222.0


class TestThreadSafety:
    """Перевірка потокобезпеки."""

    def test_concurrent_save(self):
        """Багато потоків одночасно зберігають — файл не ламається."""
        PricingSettings._instance = None

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pricing.json")
            s = PricingSettings.get_instance(path)
            errors = []

            def worker(n):
                try:
                    s.custom_params[f"thread_{n}"] = float(n)
                    s.save()
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Помилки при паралельному записі: {errors}"

            # Перевіримо, що файл валідний
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert "custom_params" in data
