cd /dev/shm/w && cat > fit.py << 'EOF'
import numpy as np, d3
from scipy.optimize import least_squares
def FkOf(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return {0:0.0,2:F2,4:F4}
def spectrum(Dq,B,C):
    F=FkOf(B,C)
    b,H=d3.build(3,F,Dq)
    up=[i for i,s in enumerate(b) if all(o%2==0 for o in s)]  # all spin-up (even index)
    Hq=H[np.ix_(up,up)]
    eq=np.sort(np.linalg.eigvalsh(Hq))
    # quartet levels (mult from M_S=3/2 block)
    qlev=group(eq)
    # M_S=1/2 sector: 2 up,1 down
    half=[i for i,s in enumerate(b) if sum(1 for o in s if o%2==0)==2]
    eh=np.sort(np.linalg.eigvalsh(H[np.ix_(half,half)]))
    # remove quartet eigenvalues
    rem=list(eh)
    for e,m in qlev:
        for _ in range(m):
            j=int(np.argmin([abs(x-e) for x in rem])); rem.pop(j)
    dlev=group(np.array(rem))
    return qlev,dlev
def group(e,tol=1e-6):
    out=[]
    for x in e:
        if out and abs(x-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
if __name__=="__main__":
    q,d=spectrum(0.0,1000.0,4000.0)
    print("quartets",[(round(e,1),m) for e,m in q])
    print("doublets",[(round(e,1),m) for e,m in d])
EOF
python3 fit.py