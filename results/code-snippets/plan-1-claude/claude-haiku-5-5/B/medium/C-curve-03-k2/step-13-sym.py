exec(open('ts.py').read())
import numpy as np, scipy.linalg as sl
# l=2 angular momentum matrices in basis m=-2..2
Lz=np.diag(np.array(ms,complex))
Lp=np.zeros((5,5),complex)
for i,m in enumerate(ms[:-1]):
    Lp[i+1,i]=np.sqrt(6-m*(m+1))
Lm=Lp.conj().T; Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
def Rot(n,th):
    n=np.array(n,float); n/=np.linalg.norm(n)
    return sl.expm(-1j*th*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
gens=[Rot([0,0,1],np.pi/2), Rot([1,1,1],2*np.pi/3)]
# closure on 5x5 with 3x3 tags
def R3(n,th):
    n=np.array(n,float); n/=np.linalg.norm(n)
    K=np.array([[0,-n[2],n[1]],[n[2],0,-n[0]],[-n[1],n[0],0]])
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K
g3=[R3([0,0,1],np.pi/2), R3([1,1,1],2*np.pi/3)]
els=[(np.eye(5,dtype=complex),np.eye(3))]
def key(D,R): return tuple(np.round(D.flatten(),6))+tuple(np.round(R.flatten(),6))
seen={key(*els[0])}
i=0
while i<len(els):
    D,R=els[i]; i+=1
    for g,h in zip(gens,g3):
        for D2,R2 in [(g@D,h@R)]:
            k=key(D2,R2)
            if k not in seen:
                seen.add(k); els.append((D2,R2))
print('group order',len(els))
def classify(R):
    t=np.trace(R)
    if abs(t-3)<1e-6: return 'E'
    if abs(t)<1e-6: return 'C3'
    if abs(t-1)<1e-6: return 'C4'
    # t=-1
    diag=np.allclose(R,np.diag(np.diag(R)))
    return 'C2' if diag else "C2'"
from collections import Counter
print(Counter(classify(R) for D,R in els))
# characters
classes=['E','C3','C2','C4',"C2'"]
csize={'E':1,'C3':8,'C2':3,'C4':6,"C2'":6}
irreps={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
order=[ 'E','C3','C2','C4',"C2'"]
# many-body rep on Ms=1/2 block (nup=4)
V=Vtab(1.0,3699/784)
def mb_matrix(U,S):
    n=len(S); M=np.zeros((n,n),complex)
    for j,J in enumerate(S):
        for i,I in enumerate(S):
            M[i,j]=np.linalg.det(U[np.ix_(I,J)])
    return M
def U_of(D):
    # spin-orbital index: so[i]=(m,s)
    U=np.zeros((NS,NS),complex)
    for a,(ma,sa) in enumerate(so):
        for b,(mb,sb) in enumerate(so):
            if sa==sb: U[a,b]=D[ma+2,mb+2]
    return U
def run(Dq):
    P=proj(Dq)
    S,H=build(7,V,P)
    nup=np.array([sum(1 for i in s if so[i][1]>0) for s in S])
    sel=[i for i in range(len(S)) if nup[i]==4]
    Ssub=[S[i] for i in sel]
    Hs=H[np.ix_(sel,sel)]
    # random-combo generic symmetric operator to split degeneracies is not needed; cluster by eigenvalue
    w,v=np.linalg.eigh(Hs)
    # group matrices
    Gs=[(c, mb_matrix(U_of(D),Ssub)) for (D,R),c in [((D,R),classify(R)) for D,R in els]]
    # class-avg characters per cluster
    clusters=[]
    for k in range(len(w)):
        if clusters and abs(w[k]-clusters[-1][0])<1e-6: clusters[-1][1].append(k)
        else: clusters.append([w[k],[k]])
    out=[]
    for e,ks in clusters:
        vecs=v[:,ks]
        chi={}
        for (D,R),c in [((D,R),classify(R)) for D,R in els]:
            pass
        ch={c:[] for c in classes}
        for (D,R),c in [((D,R),classify(R)) for D,R in els]:
            G=mb_matrix(U_of(D),Ssub)
            ch[c].append(np.trace(vecs.conj().T@G@vecs))
        avg=[np.mean(ch[c]).real for c in classes]
        # decompose
        dec={}
        for name,irr in irreps.items():
            m=sum(csize[c]*avg[i]*irr[i] for i,c in enumerate(classes))/24
            if abs(m)>1e-6: dec[name]=round(m,3)
        out.append((e,len(ks),dec))
    return out
for Dq in [1.45,2.45,3.00]:
    print('Dq',Dq)
    for e,n,dec in run(Dq)[:12]:
        print('  E=%.4f n=%d %s'%(e,n,dec))
