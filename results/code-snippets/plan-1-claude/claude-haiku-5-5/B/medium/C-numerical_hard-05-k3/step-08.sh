cat << 'EOF' > solve.py
import d6,numpy as np
from scipy.optimize import brentq
def trip(x):
    w=d6.spectrum_singlet(x,1.0,4.5); w=w-w[0]
    groups=[]
    for e in w:
        if groups and abs(e-groups[-1][0])<1e-5: groups[-1][1]+=1
        else: groups.append([e,1])
    t=[e for e,d in groups if d==3 and e>1e-6]
    return t
r2=22740/13960; r3=29700/13960
f=lambda x: trip(x)[1]/trip(x)[0]-r2
x=brentq(f,1.8,2.3,xtol=1e-10)
t=trip(x)
print("x=Dq/B",x,"triplets/B",t, "ratio3", t[2]/t[0])
B=13960/t[0]
print("B=",B,"Dq=",x*B,"C=",4.5*B)
print("pred nu2,nu3:",t[1]*B,t[2]*B)
EOF
python3 solve.py