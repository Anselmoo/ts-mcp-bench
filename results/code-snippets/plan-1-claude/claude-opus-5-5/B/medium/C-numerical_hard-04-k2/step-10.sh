cat > go.py <<'EOF'
from fit2 import *
obs=np.array([29360,29620,31640])
def calc(p):
    L=levels(*p); e0=L[0][0]
    d=[(e-e0,g) for e,s,g in L[1:] if s==0.0]
    return d
def res(p): return np.array([x for x,g in calc(p)[:3]])-obs
best=None
for Dq in [2500,3000,3500,4000]:
  for B in [300,500,700]:
    r=least_squares(res,[Dq,B])
    if best is None or r.cost<best.cost: best=r
    print(Dq,B,r.x,r.fun)
print(best.x,best.fun,calc(best.x)[:5]); show(*best.x)
EOF
python3 go.py