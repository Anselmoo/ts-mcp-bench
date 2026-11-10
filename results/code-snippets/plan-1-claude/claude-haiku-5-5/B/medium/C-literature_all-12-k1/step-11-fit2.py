import ts, numpy as np
from scipy.optimize import least_squares
b3=ts.occ_states(7,3); b1=ts.occ_states(7,1)
Mcf3,M3=ts.build(b3); Mcf1,M1=ts.build(b1)
def spectra(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    H3=Dq*Mcf3+F2*M3[2]+F4*M3[4]
    H1=Dq*Mcf1+F2*M1[2]+F4*M1[4]
    q=np.linalg.eigvalsh(H3); d=np.linalg.eigvalsh(H1)
    rest=list(d)
    for e in q:
        j=int(np.argmin([abs(x-e) for x in rest])); rest.pop(j)
    return np.sort(q), np.array(sorted(rest))
if __name__=="__main__":
    q,dbl=spectra(615,800,3000)
    print("quartets rel",np.round(q-q[0],1))
    # collapse doublets into distinct levels
    lv=[]
    for e in dbl:
        if not lv or abs(e-lv[-1][0])>1e-3: lv.append([e,1])
        else: lv[-1][1]+=1
    print("doublet levels rel:",[(round(e-q[0],1),n) for e,n in lv])
