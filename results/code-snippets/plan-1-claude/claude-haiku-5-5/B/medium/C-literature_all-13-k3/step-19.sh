
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > pre.py
exec(open('run3.py').read().split('def levels_sym')[0])
import time
t=time.time()
def build_parts():
    dim=2**nm
    parts={}
    def assemble(kind):
        H=np.zeros((dim,dim))
        if kind=='h':
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
EOF
cat << 'EOF' > fit4.py
exec(open('pre.py').read())
from scipy.optimize import least_squares
obs=np.array([7150,15200,19200,21130.])
def pred(p):
    r=levels_fast(*p)
    q=r[1.5]; d=r[0.5]
    g=q[0][0]
    t2=[x for x in q if x[2]==-4 and x[1]==12][0][0]
    a2=[x for x in q if x[1]==4][0][0]
    t1p=q[3][0]
    dt1=[x[0] for x in d if x[2]==2 and x[1]==6]
    return np.array([t2-g,a2-g,t1p-g,dt1[1]-g])
def res(p): return pred(p)-obs
print(pred([715,900,3500]))
s=least_squares(res,[800,900,3000],bounds=([300,300,500],[1500,1500,7000]),x_scale=[50,50,300])
print("fit",s.x.round(1),"pred",pred(s.x).round(1),"res",s.fun.round(1))
EOF
timeout 500 python3 fit4.py 2>&1 | tail -4
