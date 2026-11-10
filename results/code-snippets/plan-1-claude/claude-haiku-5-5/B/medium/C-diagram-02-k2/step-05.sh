cat << 'EOF' > run.py
import numpy as np, ts
from scipy.linalg import null_space
B = 814.0; C = 3902.0
Cr = C/B
d = ts.build(4, 1.0, Cr)
D = d['D']; basis = d['basis']
# Sz=0 subspace
keep = [i for i,st in enumerate(basis) if sum(1 for x in st if ts.modes[x][1]>0)==2]
Hee = d['Hee'][np.ix_(keep,keep)]; Hcf = d['Hcf'][np.ix_(keep,keep)]
S2 = d['S2'][np.ix_(keep,keep)]
# rotation reps
classes = [("E",1,0.0,np.array([0,0,1.]))]
reps = {
 'E':  (1, d['Rot']([0,0,1.],0.0)),
 'C3': (8, d['Rot']([1,1,1.],2*np.pi/3)),
 'C2': (3, d['Rot']([0,0,1.],np.pi)),
 'C4': (6, d['Rot']([0,0,1.],np.pi/2)),
 'C2p':(6, d['Rot']([1,1,0.],np.pi)),
}
names = list(reps)
R = {k: reps[k][1][np.ix_(keep,keep)] for k in names}
sizes = {k: reps[k][0] for k in names}
# character table O: order E, 8C3, 3C2, 6C4, 6C2'
chartab = {
 'A1':[1,1,1,1,1], 'A2':[1,1,1,-1,-1], 'E':[2,-1,2,0,0],
 'T1':[3,0,-1,1,-1], 'T2':[3,0,-1,-1,1]}
order = ['E','C3','C2','C4','C2p']
dims = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
def proj(G):
    P = np.zeros_like(R['E'])
    for g_i,k in enumerate(order):
        P = P + sizes[k]*chartab[G][g_i]*R[k]
    return P*dims[G]/24.0
# check rep consistency: characters of full space
for G in chartab:
    pass
def levels_at(Dq):
    H = Hee + Dq*Hcf
    out = []
    for S in (0,1,2):
        w, U = np.linalg.eigh(S2)
        Qs = U[:, np.abs(w-S*(S+1))<1e-6]
        if Qs.shape[1]==0: continue
        for G in ['A1','A2','E','T1','T2']:
            P = Qs @ Qs.conj().T @ proj(G)  # not hermitian-safe, use basis of range
            # orthonormal basis of range of P
            u, s, vh = np.linalg.svd(P)
            r = np.sum(s>1e-8)
            if r==0: continue
            Bas = u[:, :r]
            Hr = Bas.conj().T @ H @ Bas
            ev = np.sort(np.linalg.eigvalsh(Hr))
            dG = dims[G]
            ev = ev[::dG]
            for e in ev: out.append((e, S, G))
    out.sort()
    return out
if __name__=="__main__":
    lab = lambda S,G: f"{2*S+1}{G}g"
    for Dq in np.arange(0,4.01,0.5):
        L = levels_at(Dq)
        E0 = L[0][0]
        print(f"Dq/B={Dq:.1f}")
        for e,S,G in L[:6]:
            print(f"   {lab(S,G):8s} {e-E0:10.4f}")
EOF
time python3 run.py