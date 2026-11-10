
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > solve.py
import numpy as np, time
from fit import levels
from scipy.optimize import least_squares
def model(p):
    Dq,B,C=p
    Esx,cl=levels(Dq,B,C)
    T=[e for e,d in cl if d==3 and e>1]
    E=[e for e,d in cl if d==2 and e>1]
    return T,E
def res(p):
    T,E=model(p)
    return [T[0]-19240, T[1]-21890, E[0]-23000]
t=time.time(); print(model([750,800,3200])); print(time.time()-t)
sol=least_squares(res,[750,700,3000],diff_step=1e-3,x_scale=[100,100,500])
print(sol.x, sol.fun)
print(model(sol.x))
EOF
timeout 900 python3 solve.py
