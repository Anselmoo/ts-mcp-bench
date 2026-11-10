cd <SANDBOX_TMP>/w && cat > fitall.py << 'EOF'
from ts import *
from dbl import analyze
from scipy.optimize import least_squares
def model(p):
    Dq,B,C = p
    q,_ = levels(Dq,B,C); g0=q[0]
    vals=[]
    for v in q:
        if not vals or abs(v-vals[-1][0])>1e-2: vals.append([v,1])
        else: vals[-1][1]+=1
    qr=[(v-g0,m) for v,m in vals]
    t2=[v for v,m in qr if m==12][1]; a2=[v for v,m in qr if m==4][0]; t1p=[v for v,m in qr if m==12][2]
    dbl=[(e-g0,dg,tr.real) for e,dg,tr in analyze(Dq,B,C)]
    t1=[e for e,dg,tr in dbl if dg==6 and abs(tr-2)<1e-6]
    return np.array([t2,a2,t1p,t1[1]])
obs=np.array([6150.,12400.,16850.,19000.])
def res(p): return (model(p)-obs)
best=None
for Dq0 in [550,650,750]:
  for B0 in [700,850,1000]:
    for C0 in [3000,4000,4500]:
        try:
            s=least_squares(res,[Dq0,B0,C0],x_scale=[100,100,300],max_nfev=200)
        except Exception as e:
            continue
        if best is None or s.cost<best.cost: best=s
print("params Dq,B,C:",best.x)
print("model:",model(best.x)); print("resid:",model(best.x)-obs)
EOF
timeout 900 python3 fitall.py 2>&1 | tail -5