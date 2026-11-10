cat > fit2.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
exec(open('fit.py').read().split('# check free ion')[0])
def spectrum(F2,F4,Dq):
    q,dbl=levels(F2,F4,Dq)
    g=group(q,1e-6); gd=group(dbl,1e-6)
    return g,gd
def energies(p):
    Dq,F2,F4=p
    g,gd=spectrum(F2,F4,Dq)
    e0=g[0][0]  # ground quartet (4A2, degeneracy 1)
    quart=[(round(e-e0,3),n) for e,n in g]
    doub=[(round(e-e0,3),n) for e,n in gd]
    return quart,doub
def resid(p):
    Dq,F2,F4=p
    g,gd=spectrum(F2,F4,Dq)
    e0=g[0][0]
    qs=[e-e0 for e,n in g]
    # quartet levels: 4A2(1), 4T2(3), 4T1(3), 4T1(3)
    t2=[e for e,n in g if n==3][0]
    t1=[e for e,n in g if n==3][1:]
    return np.array([t2-19170, t1[0]-27260, t1[1]-42610, (gd[0][0]-e0)-17050])/1000.0
EOF
cat > go.py << 'EOF'
exec(open('fit2.py').read())
# explore
for p in [(1917,10000,5000),(1917,0,0)]:
    print(energies(p))
EOF
python3 go.py