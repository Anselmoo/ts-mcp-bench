import numpy as np
from scipy.linalg import expm, eigh
from scipy.spatial.transform import Rotation as Rot
d=np.load('ops.npz')
H2,Hcf=d['H2'],d['Hcf']; Ls=[d['Lx'],d['Ly'],d['Lz']]; Sz=d['Sz']; S2=d['S2']
# group of O (24 rotations)
gens=[Rot.from_rotvec([0,0,np.pi/2]).as_matrix(), Rot.from_rotvec(np.array([1,1,1])/np.sqrt(3)*2*np.pi/3).as_matrix()]
G=[np.eye(3)]
changed=True
while changed:
    changed=False
    for g in list(G):
        for h in gens:
            p=g@h
            if not any(np.allclose(p,x,atol=1e-9) for x in G):
                G.append(p); changed=True
print("group order",len(G))
def cls(R):
    rv=Rot.from_matrix(R).as_rotvec(); th=np.linalg.norm(rv)
    if th<1e-8: return 'E',rv
    tr=np.trace(R)
    if abs(tr-0)<1e-6: return 'C3',rv
    if abs(tr-1)<1e-6: return 'C4',rv
    ax=np.abs(rv/th)
    if np.allclose(sorted(ax),[0,0,1],atol=1e-6): return 'C2',rv
    return "C2'",rv
def Gam(R):
    c,rv=cls(R)
    return expm(-1j*(rv[0]*Ls[0]+rv[1]*Ls[1]+rv[2]*Ls[2]))
Gs=[Gam(R) for R in G]
# homomorphism test
err=0
for i,R1 in enumerate(G):
    for j,R2 in enumerate(G):
        P=R1@R2
        k=[t for t,x in enumerate(G) if np.allclose(x,P,atol=1e-9)][0]
        err=max(err,np.abs(Gs[i]@Gs[j]-Gs[k]).max())
print("hom err",err)
from collections import Counter
print(Counter(cls(R)[0] for R in G))
# characters
chtab={'A1':{'E':1,'C3':1,'C2':1,'C4':1,"C2'":1},
       'A2':{'E':1,'C3':1,'C2':1,'C4':-1,"C2'":-1},
       'E':{'E':2,'C3':-1,'C2':2,'C4':0,"C2'":0},
       'T1':{'E':3,'C3':0,'C2':-1,'C4':1,"C2'":-1},
       'T2':{'E':3,'C3':0,'C2':-1,'C4':-1,"C2'":1}}
dimr={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
# check orthogonality of chars sums
cc=[cls(R)[0] for R in G]
csize=Counter(cc)
for a in chtab:
    for b in chtab:
        s=sum(chtab[a][c]*chtab[b][c]*csize[c] for c in csize)
        assert s==(24 if a==b else 0),(a,b,s)
# S projectors
def proj_eig(M,val):
    w,v=eigh((M+M.conj().T)/2)
    return v[:,np.abs(w-val)<1e-6]
def run(Dq):
    H=H2+Dq*Hcf
    out=[]
    # S=3/2, M=3/2 ; S=1/2, M=1/2
    for S,M,mult in [(1.5,1.5,4),(0.5,0.5,2)]:
        # spin subspace S^2 and Sz=M
        Pspin=np.eye(len(H))
        # projector onto S2 eigen and Sz=M
        w,v=eigh((S2+S2.conj().T)/2)
        Vs=v[:,np.abs(w-S*(S+1))<1e-6]
        Hs=Vs.conj().T@(Sz)@Vs
        wz,vz=eigh((Hs+Hs.conj().T)/2)
        Vsm=Vs@vz[:,np.abs(wz-M)<1e-6]
        # Now Vsm basis of S,M sector
        Hsec=Vsm.conj().T@H@Vsm
        for Gname,ch in chtab.items():
            Pg=sum(ch[cls(R)[0]]*Gs[i] for i,R in enumerate(G))*dimr[Gname]/24
            Pm=Vsm.conj().T@Pg@Vsm   # restricted to sector (Pg commutes with Sz,S2)
            wp,vp=eigh((Pm+Pm.conj().T)/2)
            Vg=Vsm@vp[:,np.abs(wp-1)<1e-6]
            if Vg.shape[1]==0: continue
            Hb=Vg.conj().T@H@Vg
            ev=np.linalg.eigvalsh((Hb+Hb.conj().T)/2)
            # group eigenvalues
            vals=[]
            for e in np.sort(ev):
                if vals and abs(e-vals[-1][0])<1e-7: vals[-1][1]+=1
                else: vals.append([e,1])
            for e,mu in vals:
                cnt=mu/dimr[Gname]
                assert abs(cnt-round(cnt))<1e-6,(Gname,S,mu)
                for _ in range(int(round(cnt))):
                    out.append((e,f"{int(2*S+1)}{Gname}g"))
    return sorted(out,key=lambda x:x[0])
if __name__=="__main__":
    print("Dq=0 check:")
    for e,l in run(0.0): print(f"  {e:12.6f} {l}")
