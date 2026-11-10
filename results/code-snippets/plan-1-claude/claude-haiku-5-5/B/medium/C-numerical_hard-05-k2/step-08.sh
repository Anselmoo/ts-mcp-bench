python3 - <<'EOF'
import re
src=open('d6.py').read()
old="""                if c==d or not (s>>d)&1: continue
                s1=s^(1<<d); g1=(-1)**bin(s&((1<<d)-1)).count('1')
                if not (s1>>c)&1: continue
                s2=s1^(1<<c); g2=(-1)**bin(s1&((1<<c)-1)).count('1')"""
new="""                if c==d or not (s>>c)&1: continue
                s1=s^(1<<c); g1=(-1)**bin(s&((1<<c)-1)).count('1')
                if not (s1>>d)&1: continue
                s2=s1^(1<<d); g2=(-1)**bin(s1&((1<<d)-1)).count('1')"""
assert old in src
open('d6.py','w').write(src.replace(old,new))
EOF
python3 -c "
import numpy as np
from d6 import *
h,V=build(1.0,4.5,0.0)
b,H,S2=ops(h,V)
w,U=np.linalg.eigh(H+100*S2)
s2=np.diag(U.T@S2@U); e=np.diag(U.T@H@U)
for val in sorted(set(np.round(s2,3))):
    print(val, np.round(sorted(set(np.round(e[np.abs(s2-val)<1e-3],3))),3))
"