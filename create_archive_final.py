import shutil
import os

src = os.path.expanduser("~/Desktop/TverdukVentCompany2V_Etapy1-5_Fixed")
dst = os.path.expanduser("~/Desktop/TverdukVentCompany2V_Etapy1-5_Final")

shutil.make_archive(dst, 'zip', src)
print(f"Archive created: {dst}.zip")
print(f"Size: {os.path.getsize(dst + '.zip') / 1024 / 1024:.1f} MB")
