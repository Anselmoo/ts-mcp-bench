cat > fit.py << 'EOF'
import ts, numpy as np
from scipy.optimize import least_squares
b3=ts.occ_states(7,3); b1=ts.occ_states(7,1)
Mcf3,M3=ts.build(b3); Mcf1,M1=ts.build(b1)
def spectra(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    H3=Dq*Mcf3+F2*M3[2]+F4*M3[4]
    H1=Dq*Mcf1+F2*M1[2]+F4*M1[4]
    q=np.linalg.eigvalsh(H3); d=np.linalg.eigvalsh(H1)
    # remove quartet levels from M_S=1/2 spectrum
    rest=list(d)
    for e in q:
        j=int(np.argmin([abs(x-e) for x in rest])); rest.pop(j)
    return np.sort(q), np.array(sorted(rest))
if __name__=="__main__":
    q,dbl=spectra(1.0,0.0,0.0)
    print("free-ish check Dq=0,B=1,C=0 quartets:",np.round(q,3))
    q,dbl=spectra(615,800,3000)
    print("quartets",np.round(q-q[0],1))
    # group doublets
    print("doublets",np.round(dbl-q[0],1))
EOF
python3 fit.py