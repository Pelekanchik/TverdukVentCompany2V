import zipfile

with zipfile.ZipFile('stage1_improved_area.zip', 'w') as z:
    z.write('ventilation_company/standard_products.py')
    z.write('ventilation_company/manufacturing_params.py')
    z.write('test_stage1_smoke.py')
print('ZIP_CREATED')
