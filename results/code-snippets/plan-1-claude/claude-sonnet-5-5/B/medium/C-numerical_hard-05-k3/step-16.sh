cd <SANDBOX_TMP> && sed -i 's|F={2:(49\*B+7\*C)/49,4:(63\*C/5)/441}|F={2:49*B+7*C,4:63*C/5}|' a.py && python3 t.py && python3 -c "
from a import *
print(levels(singlets(1600,500,2250),5))"