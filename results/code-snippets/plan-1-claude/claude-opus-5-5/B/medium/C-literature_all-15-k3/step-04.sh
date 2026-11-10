
cd <SANDBOX_TMP> && cat << 'EOF' > fitme.py
import numpy as np
from scipy.optimize import least_squares
M=np.load('mats.npz'); HD,HB,HC,SS=M['HD'],M['HB'],M['HC'],M['SS']
# restrict to Ms=1/2 subspace? just use all; spin by S2
def levels(Dq,B,C):
    H=Dq*HD+B*HB+C*HC
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,SS,v)
    S=np.round((-1+np.sqrt(1+4*s))/2*2)/2
    w=w-w.min()
    # group
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        deg=j-i; Sv=S[i]; out.append((w[i],int(2*Sv+1),deg//int(2*Sv+1)));i=j
    return out
print(levels(0,1000,4000)[:6])
for l in levels(850,850,3500)[:15]: print(l)
EOF
python fitme.py