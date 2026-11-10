
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > fit2.py
import numpy as np
from scipy.optimize import least_squares
from lab import labels
def pick(Dq,B,C):
    L = labels(Dq,B,C)
    g = [x for x in L if x[0]==1.5 and x[2]==12 and x[3]==4][0][1]  # ground 4T1g
    q_T2 = [x for x in L if x[0]==1.5 and x[2]==12 and x[3]==-4]
    q_T1 = [x for x in L if x[0]==1.5 and x[2]==12 and x[3]==4]
    d_T1 = [x for x in L if x[0]==0.5 and x[2]==6 and x[3]==2]
    return g, q_T2[0][1]-g, q_T1[1][1]-g, d_T1[1][1]-g, d_T1[0][1]-g
def res(p):
    Dq,B,C = p
    g,t2,t1q2,t1d2,t1d1 = pick(Dq,B,C)
    return [t2-8100, t1q2-19400, t1d2-21600]
for guess in [(800,900,3500),(810,1000,4000),(900,800,3000)]:
    sol = least_squares(res, guess, xtol=1e-12, ftol=1e-12, gtol=1e-12)
    print(sol.x, res(sol.x))
    print(pick(*sol.x))
EOF
python3 fit2.py 2>&1 | grep -v "^\[\|C4"