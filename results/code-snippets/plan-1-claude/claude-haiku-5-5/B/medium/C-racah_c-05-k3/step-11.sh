
cat << 'EOF' > run.py
import numpy as np
exec(open('fit.py').read().split('if __name__')[0])
from scipy.optimize import least_squares
def pick(Dq,B,C):
    (s1,q),(s2,d)=levels(Dq,B,C)
    # quartet groups
    qg=[(e,m) for e,m in q]
    # ground = lowest group (mult 4)
    E0=qg[0][0]
    quart=[(e-E0,m) for e,m in qg]
    t2=[e for e,m in quart if m==12]
    dbl=[(e-E0,m) for e,m in d]
    return quart, dbl
def resid(p):
    Dq,B,C=p
    quart,dbl=pick(Dq,B,C)
    t=[e for e,m in quart if m==12]
    d4=[e for e,m in dbl if m==4]
    return [t[0]-17500, t[1]-23860, t[2]-37910, d4[0]-12090]
sol=least_squares(resid,[1750,600,2400],x_scale=[1000,500,2000])
print(sol.x, resid(sol.x))
quart,dbl=pick(*sol.x)
print("quartets",[(round(e),m) for e,m in quart])
print("doublets lowest",[(round(e),m) for e,m in dbl[:8]])
EOF
python3 run.py 2>&1 | tail -6
