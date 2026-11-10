cat > fit.py << 'EOF'
from oct import levels
import numpy as np
from scipy.optimize import least_squares
def model(p):
    Dq,B,C=p
    L=levels(Dq,B,C)
    q=sorted([r for r in L if abs(r[0]-3.75)<0.01],key=lambda r:r[1])
    g=[r for r in L if abs(r[0]-0.75)<0.01]
    E0=q[0][1]
    # 4T2g: quartet, chi=-4 with 12 states (lowest such)
    T2=[r for r in q if r[2]==12 and np.real(r[3])<0][0][1]-E0
    P=[r for r in q if r[2]==12 and np.real(r[3])>0][-1][1]-E0
    # doublet T1g second: 6-block with chi=+2 above 4T1P? choose the one nearest 21600 among chi=+2 blocks (2 T1 each)
    dub=[r[1]-E0 for r in g if r[2]==6 and np.real(r[3])>1.5]
    return T2,P,dub
p0=[810,900,4000]
print(model(p0))
def res(p):
    T2,P,dub=model(p)
    d2=min(dub,key=lambda x:abs(x-21600))
    return [T2-8100,P-19400,d2-21600]
sol=least_squares(res,p0,x_scale=[100,100,500])
print(sol.x, res(sol.x), model(sol.x))
EOF
python3 fit.py