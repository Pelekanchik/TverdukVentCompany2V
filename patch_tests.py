import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

# Знаходимо рядок з "class TestCategoryWasteFactors:" і замінюємо все після нього
new = []
for i, line in enumerate(lines):
    if 'class TestCategoryWasteFactors:' in line:
        new.append(line)
        new.append('    """Тести коефіцієнтів запасу на брак/поворот."""\n')
        new.append('\n')
        new.append('    def test_default_factors_are_zero(self):\n')
        new.append('        from ventilation_company.gui.settings_tab import DEFAULT_CATEGORY_WASTE_FACTORS\n')
        new.append('        assert DEFAULT_CATEGORY_WASTE_FACTORS["rect_duct"] == 0.0\n')
        new.append('        assert DEFAULT_CATEGORY_WASTE_FACTORS["rect_fitting"] == 0.0\n')
        new.append('        assert DEFAULT_CATEGORY_WASTE_FACTORS["round_duct"] == 0.0\n')
        new.append('        assert DEFAULT_CATEGORY_WASTE_FACTORS["round_fitting"] == 0.0\n')
        new.append('\n')
        new.append('    def test_cost_engine_with_category_waste(self):\n')
        new.append('        from ventilation_company.calculations.cost_engine import CostEngine\n')
        new.append('        engine = CostEngine()\n')
        new.append('        result = engine.calculate(\n')
        new.append('            product_type="повітропровід прямокутний",\n')
        new.append('            material_name="оцинкована сталь",\n')
        new.append('            thickness_mm=0.7,\n')
        new.append('            surface_area_m2=1.0,\n')
        new.append('            blank_area_m2=1.1,\n')
        new.append('            material_area_m2=1.2,\n')
        new.append('            category_waste_percent=10.0,\n')
        new.append('        )\n')
        new.append('        # category_waste_cost = material_cost * 10%\n')
        new.append('        expected_waste = result.material_cost * 0.1\n')
        new.append('        assert abs(result.category_waste_cost - expected_waste) < 0.01\n')
        new.append('        assert result.category_waste_percent == 10.0\n')
        break
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
