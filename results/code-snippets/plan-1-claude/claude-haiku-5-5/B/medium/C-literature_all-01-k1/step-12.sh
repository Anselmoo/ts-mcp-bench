
cd /tmp/tsbench-run-de_x16pn && cat << 'EOF' > solve.py
exec(open('fit2.py').read().split('for B,Dq')[0])
from scipy.optimize import fsolve
def gaps(p):
    Dq,B=p
    L=levels(B,Dq)
    d={n:e for e,n in L}
    E=[e for e,n in L]; N=[n for e,n in L]
    g0=E[0]
    return E,N
def res(p):
    Dq,B=p
    E,N=gaps(p)
    return [E[1]-E[0]-4400, E[3]-E[0]-15500]
sol=fsolve(res,[450,700],xtol=1e-12)
print(sol, res(sol))
E,N=gaps(sol); print([(round(e-E[0],1),n) for e,n in zip(E,N)])
EOF
python3 solve.py