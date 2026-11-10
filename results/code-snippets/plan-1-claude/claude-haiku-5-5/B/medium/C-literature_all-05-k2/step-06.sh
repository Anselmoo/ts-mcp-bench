cd /tmp/tsbench-run-7__jfl5e; cat > fit.py << 'EOF'
from run import *
import numpy as np
def build_parts():
    # returns H_ob (Dq=1), H_F2 (F2=1), H_F4 (F4=1) and S2 matrix
    P_t=np.zeros((5,5)); P_e=np.zeros((5,5))
    id_={m:i for i,m in enumerate(ms)}
    P_t[id_[1],id_[1]]=1; P_t[id_[-1],id_[-1]]=1
    va=np.zeros(5); va[id_[2]]=1/np.sqrt(2); va[id_[-2]]=-1/np.sqrt(2)
    vb=np.zeros(5); vb[id_[2]]=1/np.sqrt(2); vb[id_[-2]]=1/np.sqrt(2)
    P_t+=np.outer(va,va); P_e[id_[0],id_[0]]=1; P_e+=np.outer(vb,vb)
    Vf=-4*P_t+6*P_e
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s==s2: h[i,j]=Vf[id_[m],id_[m2]]
    D=len(dets)
    Hob=np.zeros((D,D)); H2=np.zeros((D,D)); H4=np.zeros((D,D))
    V2=Vtensor(1.0,0.0); V4=Vtensor(0.0,1.0)
    for x,occ in enumerate(dets):
        for y,ket in enumerate(dets):
            for i in range(n):
                for j in range(n):
                    if abs(h[i,j])<1e-14: continue
                    st,sg=apply_ops([('c',i),('a',j)],ket)
                    if st==occ: Hob[x,y]+=h[i,j]*sg
            for i in range(n):
             for j in range(n):
              for k in range(n):
               for l in range(n):
                if abs(V2[i,j,k,l])<1e-14 and abs(V4[i,j,k,l])<1e-14: continue
                st,sg=apply_ops([('c',i),('c',j),('a',l),('a',k)],ket)
                if st==occ:
                    H2[x,y]+=0.5*V2[i,j,k,l]*sg
                    H4[x,y]+=0.5*V4[i,j,k,l]*sg
    # S^2
    def spin_ops():
        Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
        for x,occ in enumerate(dets):
            for y,ket in enumerate(dets):
                for mi in range(5):
                    up=2*mi; dn=2*mi+1
                    st,sg=apply_ops([('c',up),('a',up)],ket)
                    if st==occ: Sz[x,y]+=0.5*sg
                    st,sg=apply_ops([('c',dn),('a',dn)],ket)
                    if st==occ: Sz[x,y]-=0.5*sg
                    # S+ = sum c†_up c_dn
                    st,sg=apply_ops([('c',up),('a',dn)],ket)
                    if st==occ: Sp[x,y]+=sg
        return Sz,Sp
    Sz,Sp=spin_ops()
    S2=Sz@Sz+0.5*(Sp.T@Sp+Sp@Sp.T)
    return Hob,H2,H4,S2
if __name__=="__main__":
    Hob,H2,H4,S2=build_parts()
    np.savez('parts.npz',Hob=Hob,H2=H2,H4=H4,S2=S2)
    print("done")
EOF
time python3 fit.py