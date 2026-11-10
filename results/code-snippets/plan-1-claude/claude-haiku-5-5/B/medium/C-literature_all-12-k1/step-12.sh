cat > fit3.py << 'EOF'
import numpy as np
from fit2 import spectra
from scipy.optimize import least_squares
obs={'4T2':6150,'4A2':12400,'4T1P':16850}
def quartet_levels(p):
    Dq,B,C=p
    q,d=spectra(Dq,B,C)
    t1=q[0]; 
    # 3-fold levels & singlet
    return q
def model_q(p):
    q,_=spectra(p[0],p[1],p[2])
    q=q-q[0]
    # identify: ground triplet = 0; 4T2 = next triplet; 4A2 = singlet; 4T1P = top triplet
    t2=q[3]; a2=q[6]; t1p=q[7]
    return np.array([t2,a2,t1p])
def res(p):
    m=model_q(p); return (m-np.array([6150,12400,16850]))/100.
sol=least_squares(res,[615,800,3000],x_scale=[100,100,500],bounds=([300,300,1000],[1000,1500,6000]))
print("quartet fit Dq,B,C:",sol.x, res(sol.x)*100)
p=sol.x
q,d=spectra(*p)
lv=[]
for e in d:
    if not lv or abs(e-lv[-1][0])>1e-3: lv.append([e,1])
    else: lv[-1][1]+=1
print("doublet levels rel:",[(round(float(e-q[0]),0),n) for e,n in lv][:10])
EOF
python3 fit3.py 2>&1 | grep -v "cf eig"