cat > solve.py << 'EOF'
from fit import *
from scipy.optimize import fsolve
def pick(B,C):
    H=build_H(2660,B,C); L=levels(H)
    g=L[0][0]; Ls=[(round(e-g,3),d) for e,d in L]
    # 4T1(F): lower deg-12 level above the 4T2 (26600)
    t1=[e for e,d in Ls if d==12 and e>26000][0]
    # 2E: lowest deg-4 level above 4A2 (quartet 4A2 is at 0 with deg 4 too)
    e2=[e for e,d in Ls if d==4 and e>1000][0]
    return t1,e2
def F(p):
    t1,e2=pick(*p); return [t1-32500, e2-12820]
sol=fsolve(F,[700,3000],xtol=1e-10,full_output=True)
print(sol[0], F(sol[0]))
B,C=sol[0]
print(pick(B,C))
# check with trial points
for p in [(800,3500),(900,4000)]: print(p,pick(*p))
EOF
python3 solve.py 2>&1 | grep -v time