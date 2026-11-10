cd <SANDBOX_TMP>; python3 -c "
from a import *
for D in (0,):
    w=bands(900,4000,D);u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    print([(round(a),b) for a,b in u[:10]])
"