cat > fullfit.py << 'EOF'
import numpy as np
from fit2 import spectra
from scipy.optimize import least_squares
obs=np.array([6150,12400,16850,19000.])
def levels(p):
    q,d=spectra(p[0],p[1],p[2])
    q=q-q[0]
    lv=[]
    for e in d:
        e=e-spectra_ground[0]
        if not lv or abs(e-lv[-1][0])>1e-3: lv.append([e,1])
        else: lv[-1][1]+=1
    return q,lv
def model(p,cand):
    global spectra_ground
    q,d=spectra(p[0],p[1],p[2]); spectra_ground=q
    qq=q-q[0]
    dd=[]
    for e in d:
        e=e-q[0]
        if not dd or abs(e-dd[-1][0])>1e-3: dd.append([e,1])
        else: dd[-1][1]+=1
    trip=[e for e,n in dd if n==3]
    return np.array([qq[3],qq[6],qq[7],trip[cand]])
for cand in range(0,6):
    f=lambda p: (model(p,cand)-obs)/100.
    best=None
    for s in [(615,800,3000),(650,900,4000),(700,700,3000)]:
        try:
            sol=least_squares(f,s,bounds=([300,300,1000],[1200,1500,7000]))
        except Exception as ex: continue
        if best is None or sol.cost<best.cost: best=sol
    print(cand, np.round(best.x,1), np.round(model(best.x,cand),0), round(best.cost,1))
EOF
python3 fullfit.py 2>&1 | grep -v "cf eig"