cat > fit.py << 'EOF'
import d5, numpy as np
from scipy.optimize import least_squares
def doublets(Dq,B):
    H,S2=d5.build(Dq,B)
    w,v=np.linalg.eigh(H+1e6*S2)
    # S=1/2 states: S2 eigen 0.75
    sel=[]
    s2 = np.einsum('ip,ij,jp->p',v,S2,v)
    E=[]
    for k in range(len(w)):
        if abs(s2[k]-0.75)<1e-6: E.append(H.trace()*0+np.dot(v[:,k],H@v[:,k]))
    E=np.sort(np.array(E))
    return E-E[0]
if __name__=="__main__":
    E=doublets(1.0,1.0)
    print(len(E)); print(np.round(E,4))
EOF
python3 fit.py