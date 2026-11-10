cat > scan.py <<'EOF'
import d4,numpy as np
# precompute the B-linear parts: H = B*(Hee) + Dq*(Hcf); build with B=1 and Dq=0 and Dq=1
st,H0,S2=d4.build(0.0)
_,H1,_=d4.build(1.0)
Hcf = H1-H0
def triplets(x):
    H = H0 + x*Hcf
    # restrict to S=1 by diagonalizing H + big*(S2-2)^2 style: use projection eigen
    ev,vec = np.linalg.eigh(H + 1e4*(S2-2*np.eye(len(S2)))@(S2-2*np.eye(len(S2))))
    out=[]
    for k in range(len(ev)):
        v=vec[:,k]; s=v@S2@v
        if abs(s-2)<1e-3:
            out.append(H[:,:].dot(v)@v)  # expectation
    return sorted(out)
for x in [0.0,1.0,1.5,2.0]:
    t = triplets(x)
    t = np.array(t); print(x, np.round(t-t[0],3))
EOF
python3 scan.py