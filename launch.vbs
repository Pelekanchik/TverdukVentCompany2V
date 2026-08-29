Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Admin\Desktop\TverdukVentCompany2V"
WshShell.Run "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe main.py", 0, False
