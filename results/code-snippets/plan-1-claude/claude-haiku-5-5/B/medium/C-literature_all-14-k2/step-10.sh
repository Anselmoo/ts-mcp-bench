cat > sym.py << 'EOF'
import numpy as np, itertools
from d7run import states, nso, W, X, Y, Z, orbs, idx
from fit import q_idx, d_idx, levels
# orbital functions as callables on coordinates
fun = [lambda x,y,z: x*y, lambda x,y,z: y*z, lambda x,y,z: z*x,
       lambda x,y,z: x*x-y*y, lambda x,y,z: 3*z*z-(x*x+y*y+z*z)]
nrm = [np.sqrt(np.sum(orbs[i][1]**2*W)) for i in range(5)]
def D_of(Rinv):  # Rinv: function mapping (X,Y,Z)->(X',Y',Z')
    xp,yp,zp = Rinv(X,Y,Z)
    D=np.zeros((5,5))
    for i in range(5):
        for j in range(5):
            fj = fun[j](xp,yp,zp)
            D[i,j]=np.sum(orbs[i][1]*fj*W)/nrm[j]/nrm[i]*1.0
    # normalize (fj norm equals nrm[j] as rotation invariance)
    return D
# C4 about z: inverse rotation by -90 deg: (x,y,z)->(y,-x,z)
D4 = D_of(lambda x,y,z:(y,-x,z))
print("orthogonal?", np.allclose(D4@D4.T,np.eye(5),atol=1e-6))
def Lambda(D):
    u=np.zeros((nso,nso))
    u[:5,:5]=D; u[5:,5:]=D
    n=len(states); L=np.zeros((n,n))
    occ=[[o for o in range(nso) if (s>>o)&1] for s in states]
    for i,I in enumerate(occ):
        for j,J in enumerate(occ):
            L[i,j]=np.linalg.det(u[np.ix_(I,J)])
    return L
L4=Lambda(D4)
def chars(H_sector_idx, Eigs_idx_sector):
    pass
def analyse(B,C,Dq):
    H=__import__('d7run').build(B,C,Dq)
    out={}
    for name,sec in (('Ms32',q_idx),('Ms12',d_idx)):
        Hs=H[np.ix_(sec,sec)]; Ls=L4[np.ix_(sec,sec)]
        ev,V=np.linalg.eigh(Hs)
        # cluster
        clusters=[]
        for k,e in enumerate(ev):
            if clusters and abs(e-clusters[-1][0])<1e-3: clusters[-1][1].append(k)
            else: clusters.append([e,[k]])
        res=[]
        for e,ks in clusters:
            Vk=V[:,ks]
            chi=np.trace(Vk.T@Ls@Vk)
            res.append((e,len(ks),round(chi.real,3)))
        out[name]=res
    return out
if __name__=='__main__':
    import sys
    B,C,Dq=map(float,sys.argv[1:4])
    o=analyse(B,C,Dq)
    g0=o['Ms32'][0][0]
    for name in o:
        print(name)
        for e,m,chi in o[name]:
            print(round(e-g0,0), m, chi)
EOF
python3 -B sym.py 960 4300 810