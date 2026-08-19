import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for line in lines:
    # Виправляємо зайвий текст на кінці рядків
    if 'name"Прямокутний повітропровід"' in line:
        line = line.replace('name"Прямокутний повітропровід"', 'name')
    if 'name"Круглий повітропровід"' in line:
        line = line.replace('name"Круглий повітропровід"', 'name')
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
