cd <SANDBOX_TMP>; sed -i 's/V\[(a,b,cc,d)\]=F2\*/V[(a,b,cc,d)]=49*F2*/; s/+F4\*C\[(4,ma,mc)\]/+441*F4*C[(4,ma,mc)]/' a.py; python3 -c "
from a import *
for D in (0,1000):
    w=bands(900,4000,D);u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    print([(round(a),b) for a,b in u[:14]])
"