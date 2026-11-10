cat > scan.py <<'EOF'
import d4,numpy as np
st,H0,S2=d4.build(0.0)
_,H1,_=d4.build(1.0)
Hcf = H1-H0
w,U = np.linalg.eigh(S2)
P = U[:, np.abs(w-2)<1e-6]
print('triplet subspace dim', P.shape[1])
def triplet_levels(x):
    Hs = P.T@(H0 + x*Hcf)@P
    e = np.linalg.eigvalsh(Hs)
    # group degeneracies
    lev=[]; 
    for v in e:
        if not lev or abs(v-lev[-1][0])>1e-6: lev.append([v,1])
        else: lev[-1][1]+=1
    return lev
if __name__=='__main__':
    for x in [0.0,1.0,1.5,2.0,2.5,3.0]:
        lev = triplet_levels(x)
        print(x, [(round(a-lev[0][0],3),m) for a,m in lev])
EOF
python3 scan.py 2>/dev/null