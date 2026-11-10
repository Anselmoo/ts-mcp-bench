cat << 'EOF' > run2.py
import numpy as np, ts, group
from collections import defaultdict
B = 814.0; C = 3902.0
d = ts.build(4, 1.0, C/B)
basis = d['basis']
keep = [i for i,st in enumerate(basis) if sum(1 for x in st if ts.modes[x][1]>0)==2]
Hee = d['Hee'][np.ix_(keep,keep)]; Hcf = d['Hcf'][np.ix_(keep,keep)]
S2 = d['S2'][np.ix_(keep,keep)]
els = group.octa_group()
chartab = {'A1':{'E':1,'C3':1,'C2':1,'C4':1,'C2p':1},
 'A2':{'E':1,'C3':1,'C2':1,'C4':-1,'C2p':-1},
 'E':{'E':2,'C3':-1,'C2':2,'C4':0,'C2p':0},
 'T1':{'E':3,'C3':0,'C2':-1,'C4':1,'C2p':-1},
 'T2':{'E':3,'C3':0,'C2':-1,'C4':-1,'C2p':1}}
dims={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
Rs = [(c, d['Rot'](ax,ang)[np.ix_(keep,keep)]) for c,ax,ang in els]
def proj(G):
    P = np.zeros_like(Rs[0][1])
    for c,R in Rs: P = P + chartab[G][c]*R
    return P*dims[G]/24.0
PG = {G: proj(G) for G in chartab}
for G in PG:
    P=PG[G]; print(G, round(np.trace(P).real,6), np.allclose(P@P,P))
w, U = np.linalg.eigh(S2)
PS = {S: U[:, np.abs(w-S*(S+1))<1e-6] for S in (0,1,2)}
print({S: PS[S].shape[1] for S in PS})
def levels_at(Dq):
    H = Hee + Dq*Hcf
    out=[]
    for S in (0,1,2):
        Q = PS[S]
        if Q.shape[1]==0: continue
        for G in chartab:
            P = Q @ (Q.conj().T @ PG[G])
            u,s,vh = np.linalg.svd(P)
            r = int(np.sum(s>1e-8))
            if r==0: continue
            Bas = u[:,:r]
            ev = np.sort(np.linalg.eigvalsh(Bas.conj().T@H@Bas))
            ev = ev[::dims[G]]
            for e in ev: out.append((e,S,G))
    out.sort(key=lambda x:x[0])
    return out
if __name__=="__main__":
    for Dq in np.arange(0,4.01,0.5):
        L = levels_at(Dq); E0=L[0][0]
        print(f"Dq/B={Dq:.1f}")
        for e,S,G in L[:6]:
            print(f"   {2*S+1}{G}g  {e-E0:10.4f}")
EOF
time python3 run2.py