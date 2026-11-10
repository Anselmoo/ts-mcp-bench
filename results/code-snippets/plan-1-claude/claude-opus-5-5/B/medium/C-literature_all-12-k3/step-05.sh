
cd <SANDBOX_TMP>/tmp.18wMokKLZh
sed -i 's/c(kk,so\[s\]\[0\],so\[b\]\[0\])/c(kk,so[b][0],so[s][0])/' d7.py
python3 -c "
from d7 import *
for e,l in table(0,800,3200)[:12]: print(round(e),l)
print()
for e,l in table(625,800,3200)[:20]: print(round(e),l)
"
