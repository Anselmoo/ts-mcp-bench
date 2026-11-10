cd <SANDBOX_TMP>/w && cat > fit.py << 'EOF'
from d3 import *
from scipy.optimize import least_squares
# subspaces
allup = [i for i,s in enumerate(states) if all(so[k][1]==1 for k in s)]
half = [i for i,s in enumerate(states) if sum(so[k][1] for k in s)==1]
def levels(Dq,B,C):
    H = build_H(Dq,B,C).real  # real symmetric? check below
    Hq = H[np.ix_(allup,allup)]
    q = np.sort(np.linalg.eigvalsh(Hq))
    Hh = H[np.ix_(half,half)]
    h = np.sort(np.linalg.eigvalsh(Hh))
    # remove quartet levels (each quartet spatial state appears once in half block)
    rem = list(h)
    for e in q:
        j = int(np.argmin([abs(x-e) for x in rem]))
        if abs(rem[j]-e)>1e-6: raise Exception("mismatch")
        rem.pop(j)
    return q, np.array(rem)
if __name__=="__main__":
    import sys
    Dq,B,C = 1917.0, 1000.0, 4000.0
    H = build_H(Dq,B,C)
    print("imag max", np.abs(H.imag).max())
    q,d = levels(Dq,B,C)
    print("quartet", np.round(q-q[0],1))
    print("doublet", np.round(d-q[0],1))
EOF
python3 fit.py