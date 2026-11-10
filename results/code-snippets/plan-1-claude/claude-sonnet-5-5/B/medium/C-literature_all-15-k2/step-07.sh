cd <SANDBOX_TMP>; sed -i 's/return float((-1)\*\*m1\*5\*gaunt(2,k,2,-m1,q,m2))/return float((-1)**m1*sqrt(4*np.pi\/(2*k+1))*gaunt(2,k,2,-m1,q,m2))/' a.py; grep -n "def c" -A4 a.py|head; python3 -c "
from a import *
for D in (0,1000):
    w=bands(900,4000,D);u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    print([(round(a),b) for a,b in u[:14]])
"