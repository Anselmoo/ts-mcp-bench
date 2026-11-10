cat > fit.py << 'EOF'
import numpy as np, itertools
d=np.load('mats.npz'); HF,HD,S,R=d['HF'],d['HD'],d['S'],d['R']
obs=np.array([22900,23730,24580.])
def trip_levels(x):
    H=HF+x*HD
    e,U=np.linalg.eigh(H)
    out=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-6: j+=1
        V=U[:,i:j]
        s2=np.real(np.trace(V.conj().T@S@V))/(j-i)
        if abs(s2-2)<1e-6:
            c4=np.real(np.trace(V.conj().T@R@V))
            out.append((e[i],j-i,c4))
        i=j
    return out
for x in np.arange(2.6,4.6,0.5):
    L=trip_levels(x)
    e0=L[0][0]
    print('x',x,[(round(v-e0,3),dg,round(c,2)) for v,dg,c in L[:7]])
EOF
python3 fit.py