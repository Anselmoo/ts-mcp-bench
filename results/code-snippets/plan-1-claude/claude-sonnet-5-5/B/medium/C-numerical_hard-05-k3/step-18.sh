cd <SANDBOX_TMP> && python3 -c "
from a import *
B=777.68;Dq=1593.16
print(spectrum(Dq,B,4.5*B,3,3)[:3], spectrum(Dq,B,4.5*B,5,1)[:2])
print(sorted(spectrum(Dq,B,4.5*B,4,2))[:3])"