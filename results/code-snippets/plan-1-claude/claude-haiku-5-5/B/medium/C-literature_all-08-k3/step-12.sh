cat > /tmp/tsbench-run-hvexjx5r/fit.py << 'EOF'
from d5 import *
from scipy.optimize import least_squares
def spec(p):
    Dq,B,C=p
    w,s2=levels(Dq,B,C)
    w6=w[np.abs(s2-35/4)<1e-6][0]
    q=np.sort(w[np.abs(s2-15/4)<1e-6])-w6
    # distinct levels
    g=[]
    for x in q:
        if not g or abs(x-g[-1][0])>1e-3: g.append([x,1])
        else: g[-1][1]+=1
    return g
def resid(p):
    g=spec(p)
    # levels: T1(G)=first (n=12), T2(G)=second (n=12), E+A1(G)=third (n=12)
    e1,e2,e3=g[0][0],g[1][0],g[2][0]
    return [e1-19180,e2-22130,e3-23370]
sol=least_squares(resid,[1900,700,3000],xtol=1e-12,ftol=1e-12,gtol=1e-12)
print(sol.x, resid(sol.x))
Dq,B,C=sol.x
print("Dq",Dq,"B",B,"C",C,"C/B",C/B)
print([ (round(e,1),n) for e,n in spec(sol.x)[:5]])
EOF
cd /tmp/tsbench-run-hvexjx5r && python3 fit.py