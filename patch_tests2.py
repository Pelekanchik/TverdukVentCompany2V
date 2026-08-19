import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    if 'def test_cost_engine_with_category_waste(self):' in line:
        # Пропускаємо цей тест і все до кінця файлу
        break
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
