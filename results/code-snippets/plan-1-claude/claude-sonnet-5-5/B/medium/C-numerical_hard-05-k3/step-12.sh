cd <SANDBOX_TMP> && sed -i 's/+=0.5\*gv/-=0.5*gv/' a.py && python3 t.py && python3 -c "
from a import *
print(levels(singlets(1600,500,2250),5))"