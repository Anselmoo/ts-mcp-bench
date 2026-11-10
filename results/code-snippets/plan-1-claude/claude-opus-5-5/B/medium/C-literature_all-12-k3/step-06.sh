
cd <SANDBOX_TMP>/tmp.18wMokKLZh
sed -i "s/orb=deg\/\/(2 if spin==4 else 1)/orb=deg/" d7.py
python3 -c "
from d7 import *
for e,l in table(625,800,3200)[:20]: print(round(e),l)
"
