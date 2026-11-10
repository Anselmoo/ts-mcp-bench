exec(open('run3.py').read().split('def levels_sym')[0])
import time
t=time.time()
def build_parts():
    dim=2**nm
    parts={}
    def assemble(kind):
        H=np.zeros((dim,dim))
        if isinstance(kind,str):
            M=h_dq
            for o1 in range(5):
                for o2 in range(5):
                    if abs(M[o1,o2])<1e-12: continue
                    for s in (0,1): H+=M[o1,o2].real*(C[so(o1,s)]@Ann[so(o2,s)])
        else:
            V=kind
            for a in range(5):
             for b in range(5):
              for c in range(5):
               for d in range(5):
                v=V[a,b,c,d].real
                if abs(v)<1e-12: continue
                for s1 in (0,1):
                 for s2 in (0,1):
                    H+=0.5*v*(C[so(a,s1)]@C[so(b,s2)]@Ann[so(d,s2)]@Ann[so(c,s1)])
        return H[np.ix_(idx,idx)]
    parts['h']=assemble('h'); parts['A2']=assemble(A2); parts['A4']=assemble(A4)
    return parts
PARTS=build_parts()
print("built",time.time()-t)
def Hm(Dq,B,C_):
    F4=12.6*C_; F2=49*B+7*C_
    return Dq*PARTS['h']+F2*PARTS['A2']+F4*PARTS['A4']
def levels_fast(Dq,B,C_):
    H=Hm(Dq,B,C_)
    res={}
    for S in [1.5,0.5]:
        sel=np.abs(ws-S*(S+1))<1e-6
        U=Us[:,sel]
        Hsub=U.T@H@U; Hsub=(Hsub+Hsub.T)/2
        w,V=np.linalg.eigh(Hsub)
        W=U@V
        groups=[];i=0
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
            Vg=W[:,i:j+1]
            groups.append((w[i],j-i+1,np.round(np.trace(Vg.conj().T@C4@Vg).real,3)))
            i=j+1
        res[S]=groups
    return res
