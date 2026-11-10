from ts import *
import hashlib, sys
from scipy.linalg import expm

B=1.0
Cc=2511/551
F4=441*Cc/35
F2=(441*B+5*F4)/9
G=coulomb_tensor({0:0.0,2:F2,4:F4})
N=6
states,idx=fock_basis(N)
S2=spin_S2(N)
_,_,Hee=build_H(N,np.zeros((NO,NO)),G)

r2=np.sqrt(2)
v_z2=np.array([0,0,1,0,0],complex)
v_x2y2=np.array([1,0,0,0,1],complex)/r2
v_xy=np.array([1,0,0,0,-1],complex)/(1j*r2)
v_xz=np.array([0,1,0,-1,0],complex)/r2
v_yz=np.array([0,1j,0,1j,0],complex)/r2
eg=[v_z2,v_x2y2]; t2g=[v_xy,v_xz,v_yz]
P_eg=sum(np.outer(v,v.conj()) for v in eg)
P_t2=sum(np.outer(v,v.conj()) for v in t2g)
assert np.allclose(P_eg+P_t2,np.eye(5))

def Lops(j):
    ms_=np.arange(-j,j+1)
    Lz=np.diag(ms_).astype(complex)
    Lp=np.zeros((2*j+1,2*j+1),complex)
    for i,m in enumerate(ms_[:-1]):
        Lp[i+1,i]=np.sqrt(j*(j+1)-m*(m+1))
    Lm=Lp.conj().T
    return (Lp+Lm)/2,(Lp-Lm)/(2j),Lz
Lx2,Ly2,Lz2=Lops(2); Lx1,Ly1,Lz1=Lops(1)
def rot(axis,theta,Lx,Ly,Lz):
    n=np.array(axis,float); n/=np.linalg.norm(n)
    return expm(-1j*theta*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
gens=[(rot([0,0,1],np.pi/2,Lx1,Ly1,Lz1),rot([0,0,1],np.pi/2,Lx2,Ly2,Lz2)),
      (rot([1,1,1],2*np.pi/3,Lx1,Ly1,Lz1),rot([1,1,1],2*np.pi/3,Lx2,Ly2,Lz2))]
def k3(M): return tuple(np.round(M.real,5).flatten())+tuple(np.round(M.imag,5).flatten())
els={k3(np.eye(3)):(np.eye(3,dtype=complex),np.eye(5,dtype=complex))}
frontier=[(np.eye(3,dtype=complex),np.eye(5,dtype=complex))]
while frontier:
    new=[]
    for R3,D5 in frontier:
        for g3,g5 in gens:
            R=g3@R3; D=g5@D5
            kk=k3(R)
            if kk not in els:
                els[kk]=(R,D); new.append((R,D))
    frontier=new
G24=list(els.values())
assert len(G24)==24, len(G24)
def classify(R):
    tr=np.trace(R).real
    if abs(tr-3)<1e-6: return 0
    if abs(tr)<1e-6: return 1
    if abs(tr-1)<1e-6: return 2
    if abs(tr+1)<1e-6:
        return 3 if np.all(np.abs(np.diag(R))>1e-6) else 4
classes=[classify(R) for R,_ in G24]
csize=[classes.count(c) for c in range(5)]
assert csize==[1,8,6,3,6], csize
chars={'A1':[1,1,1,1,1],'A2':[1,1,-1,1,-1],'E':[2,-1,0,2,0],
       'T1':[3,0,1,-1,-1],'T2':[3,0,-1,-1,1]}
dims={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
Ug=[compound(spin_diag(D),states) for R,D in G24]

def build_Hcf(Dq):
    h=6*Dq*P_eg-4*Dq*P_t2
    h1=np.zeros((NO,NO),complex)
    for s in range(2): h1[s*5:s*5+5,s*5:s*5+5]=h
    _,_,Hc=build_H(N,h1,np.zeros((NO,)*4))
    return Hc

def levels(Dq, verbose=False):
    H=Hee+build_Hcf(Dq)
    if verbose:
        print("herm",np.abs(H-H.conj().T).max(),"max commutator with O:",max(np.abs(H@U-U@H).max() for U in Ug),file=sys.stderr)
    M=H+100*S2
    w,v=np.linalg.eigh(M)
    Ss=np.array([np.real(v[:,i].conj()@S2@v[:,i]) for i in range(v.shape[1])])
    Sval=np.round((-1+np.sqrt(1+4*Ss))/2).astype(int)
    EH=w-100*Sval*(Sval+1)
    out=[]
    for S in sorted(set(Sval)):
        ids=np.where(Sval==S)[0]
        ids=ids[np.argsort(EH[ids])]
        cl=[[ids[0]]]
        for i in ids[1:]:
            if abs(EH[i]-EH[cl[-1][-1]])<1e-6: cl[-1].append(i)
            else: cl.append([i])
        for c in cl:
            Q=v[:,c]
            chis=np.array([np.trace(Q.conj().T@U@Q) for U in Ug])
            chi_cls=[np.mean(chis[[i for i in range(24) if classes[i]==cc]]) for cc in range(5)]
            dec={}
            for name,ch in chars.items():
                n=sum(csize[cc]*chi_cls[cc].real*ch[cc] for cc in range(5))/24
                if n>0.5: dec[name]=int(round(n))
            assert sum(dims[k]*n for k,n in dec.items())==len(c), (dec,len(c))
            for name,n in dec.items():
                for _ in range(n):
                    out.append((np.mean(EH[c]),S,name))
    out.sort(key=lambda x:x[0])
    return out

if __name__=="__main__":
    lv=levels(0.0, verbose=True)
    print(len(lv))
    for e,S,n in lv: print(round(e,6),S,n)
