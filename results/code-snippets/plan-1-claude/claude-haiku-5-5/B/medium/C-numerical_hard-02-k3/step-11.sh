cat > sym.py << 'EOF'
import numpy as np
exec(open('run.py').read().split('F={0:0.0')[0])
F={0:0.0,2:79.1,4:54.18}
HF=build(F,0.0); HD=build({0:0,2:0,4:0},1.0)
S=S2()
Lz=np.array([sum(m for m in [ (i//2)-2 for i in det]) for det in dets],float)
R=np.diag(np.exp(-1j*np.pi/2*Lz))
np.savez('mats.npz',HF=HF,HD=HD,S=S,R=R)
def analyze(x):
    H=HF+x*HD
    e,U=np.linalg.eigh(H)
    # group
    groups=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-6: j+=1
        V=U[:,i:j]
        s2=np.real(np.trace(V.conj().T@S@V))/(j-i)
        c4=np.trace(V.conj().T@R@V)
        groups.append((e[i],j-i,round(s2,3),np.round(c4,3)))
        i=j
    return groups
import sys
for x in [1.0,2.0,2.5,3.0]:
    g=analyze(x)
    print('x=',x)
    for t in g[:12]: print('  E=%.4f deg=%d S(S+1)=%s C4=%s'%t)
EOF
python3 sym.py