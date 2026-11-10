cd ts && cat > run_d6.py << 'EOF'
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
Hee=Hee.real if np.allclose(Hee.imag,0) else Hee

# ---- one-electron cubic field projectors in m-basis (l=2)
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

# ---- rotation group O (24 elements) on l=2 and vector reps
def Lops(j):
    ms_=np.arange(-j,j+1)
    Lz=np.diag(ms_).astype(complex)
    Lp=np.zeros((2*j+1,2*j+1),complex)
    for i,m in enumerate(ms_[:-1]):
        Lp[i+1,i]=np.sqrt(j*(j+1)-m*(m+1))
    Lm=Lp.conj().T
    Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
    return Lx,Ly,Lz
Lx2,Ly2,Lz2=Lops(2); Lx1,Ly1,Lz1=Lops(1)
def rot(axis,theta,Lx,Ly,Lz):
    n=np.array(axis,float); n/=np.linalg.norm(n)
    return expm(-1j*theta*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
gens=[(rot([0,0,1],np.pi/2,Lx1,Ly1,Lz1),rot([0,0,1],np.pi/2,Lx2,Ly2,Lz2)),
      (rot([1,1,1],2*np.pi/3,Lx1,Ly1,Lz1),rot([1,1,1],2*np.pi/3,Lx2,Ly2,Lz2))]
key=lambda M: tuple(np.round(M,6).flatten().view(float).round(6))  # not used
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
    if abs(tr)<1e-6: return 1          # C3
    if abs(tr-1)<1e-6: return 2        # C4
    if abs(tr+1)<1e-6:
        return 3 if np.all(np.abs(np.diag(R))>1e-6) else 4  # C2 (face) / C2' (edge)
classes=[classify(R) for R,_ in G24]
csize=[classes.count(c) for c in range(5)]
assert csize==[1,8,6,3,6], csize
chars={'A1':[1,1,1,1,1],'A2':[1,1,-1,1,-1],'E':[2,-1,0,2,0],
       'T1':[3,0,1,-1,-1],'T2':[3,0,-1,-1,1]}
# ---- many-body unitaries
Ug=[]
for R,D in G24:
    u=spin_diag(D)
    Ug.append(compound(u,states))
# check symmetry of Hamiltonian under group (with cubic field)
def build_Hcf(Dq):
    h=np.zeros((5,5),complex)
    h+=6*Dq*P_eg -4*Dq*P_t2
    h1=np.zeros((NO,NO),complex)
    for s in range(2): h1[s*5:s*5+5,s*5:s*5+5]=h
    _,_,Hc=build_H(N,h1,np.zeros((NO,)*4))
    return Hc

def levels(Dq, verbose=False):
    Hcf=build_Hcf(Dq)
    H=Hee+Hcf
    assert np.allclose(H,H.conj().T,atol=1e-9)
    if verbose:
        comm=max(np.abs(H@U-U@H).max() for U in Ug)
        print("max commutator with O:",comm,file=sys.stderr)
    M=H+100*S2
    w,v=np.linalg.eigh(M)
    # spin-resolved energies
    Ss=np.array([np.real(v[:,i].conj()@S2@v[:,i]) for i in range(v.shape[1])])
    Sval=np.round((-1+np.sqrt(1+4*Ss))/2).astype(int)
    EH=w-100*Sval*(Sval+1)
    out=[]
    for S in sorted(set(Sval)):
        ids=np.where(Sval==S)[0]
        Es=EH[ids]; order=np.argsort(Es)
        ids=ids[order]; Es=Es[order]
        # cluster
        clusters=[]; cur=[ids[0]]
        for a,b in zip(ids[:-1],ids[1:]):
            pass
        cl=[[ids[0]]]
        for i in range(1,len(ids)):
            if abs(EH[ids[i]]-EH[cl[-1][-1]])<1e-6: cl[-1].append(ids[i])
            else: cl.append([ids[i]])
        for c in cl:
            Q=v[:,c]
            Eav=np.mean(EH[c])
            chis=[]
            for U in Ug:
                chis.append(np.trace(Q.conj().T@U@Q))
            chis=np.array(chis)
            # class char averages
            chi_cls=[np.mean(chis[[i for i in range(24) if classes[i]==cc]]) for cc in range(5)]
            dec={}
            for name,ch in chars.items():
                n=sum(csize[cc]*chi_cls[cc].real*ch[cc] for cc in range(5))/24
                if n>0.5: dec[name]=int(round(n))
            dims={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
            assert sum(dims[k]*n for k,n in dec.items())==len(c), (dec,len(c),chi_cls)
            for name,n in dec.items():
                for _ in range(n):
                    out.append((Eav,S,name))
    out.sort(key=lambda x:x[0])
    return out

if __name__=="__main__":
    lv=levels(0.0, verbose=True)
    print(len(lv))
    for e,S,n in lv: print(round(e,6),S,n)
EOF
python3 run_d6.py 2>&1 | grep -v -i matplotlib | head -80