cd <SANDBOX_TMP>/w && cat > fit.py << 'EOF'
from d8 import *
from scipy.optimize import least_squares
def levels(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    H=H_matrix(Dq,F2/17.5,F4/17.5)
    w,v=np.linalg.eigh(H)
    # group degenerate levels
    lv=[]
    for x in w:
        if not lv or abs(x-lv[-1][0])>1e-6: lv.append([x,1])
        else: lv[-1][1]+=1
    return lv
lv=levels(500,800,3200)
for x,n in lv: print(round(x,3),n)
EOF
python3 fit.py