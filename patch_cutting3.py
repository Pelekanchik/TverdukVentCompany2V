import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    if i == 138:
        new.append('            messagebox.showerror("Помилка", "Помилка отримання виробів: " + str(e) + "\\n\\nДеталі в консолі.")\n')
    elif i == 139:
        new.append('    \n')  # додамо порожній рядок перед наступним методом
    elif i == 140:
        continue  # пропускаємо зайвий messagebox.showerror
    else:
        new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
