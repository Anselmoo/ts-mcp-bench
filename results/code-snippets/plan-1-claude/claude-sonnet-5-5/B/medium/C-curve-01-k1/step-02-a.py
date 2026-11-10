import numpy as np, itertools, sympy
from sympy.physics.wigner import wigner_3j
B=821.;C=3657.
Fk={2:49*B+7*C,4:63*C/5}
def ck(k,m1,m3):
    q=m1-m3
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m3))
cc={(k,a,b):ck(k,a,b) for k in(2,4) for a in range(-2,3) for b in range(-2,3)}
def Vee(a,b,c,d): # <ab|1/r|cd>
    if a+b!=c+d: return 0.0
    return sum(Fk[k]*cc[(k,a,c)]*cc[(k,d,b)] for k in(2,4))
so=[(m,s) for m in range(-2,3) for s in (1,-1)]
def run(Dq):
    dets=[c for c in itertools.combinations(range(10),4) if sum(so[i][1] for i in c)==0]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets);H=np.zeros((n,n));S2=np.zeros((n,n))
    h=np.zeros((5,5)) # m index m+2
    for m,v in zip(range(-2,3),[Dq,-4*Dq,6*Dq,-4*Dq,Dq]): h[m+2,m+2]=v
    h[0,4]=h[4,0]=5*Dq
    def apply(ops,d): # ops list of (create?,i) applied right to left; return (sign,newdet)
        occ=list(d);sign=1
        for cr,i in reversed(ops):
            if cr:
                if i in occ: return 0,None
                p=sum(1 for o in occ if o<i);sign*=(-1)**p;occ.append(i);occ.sort()
            else:
                if i not in occ: return 0,None
                p=sum(1 for o in occ if o<i);sign*=(-1)**p;occ.remove(i)
        return sign,tuple(occ)
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                if so[p][1]==so[q][1] and h[so[p][0]+2,so[q][0]+2]!=0:
                    s,nd=apply([(1,p),(0,q)],d)
                    if s: H[idx[nd],j]+=s*h[so[p][0]+2,so[q][0]+2]
        for p in range(10):
         for q in range(10):
          for r in range(10):
           for t in range(10):
            # 1/2 sum <pq|rt> a+p a+q a t a r
            if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
            v=Vee(so[p][0],so[q][0],so[r][0],so[t][0])
            if v==0: continue
            s,nd=apply([(1,p),(1,q),(0,t),(0,r)],d)
            if s: H[idx[nd],j]+=0.5*s*v
        # S^2 = S-S+ + Sz^2+Sz ; Sz=0 -> S-S+
        for a in range(0,10,1):
            pass
        for a in range(10):
            for b in range(10):
                if so[a][0]==so[b][0] and so[a][1]==-1 and so[b][1]==1:
                    pass
        # S+S- form: S2 = S-S+ ; S+=sum a+_up a_down
        for dm in range(-2,3):
            u=so.index((dm,1));dn=so.index((dm,-1))
            s1,d1=apply([(1,u),(0,dn)],d)
            if not s1: continue
            for em in range(-2,3):
                u2=so.index((em,1));dn2=so.index((em,-1))
                s2,d2=apply([(1,dn2),(0,u2)],d1)
                if s2: S2[idx[d2],j]+=s1*s2
    H=(H+H.T)/2
    w,v=np.linalg.eigh(H+1e-3*S2)
    out=[]
    for k in range(n):
        s2=v[:,k]@S2@v[:,k]; S=(-1+np.sqrt(1+4*s2))/2
        out.append((v[:,k]@H@v[:,k],round(S)))
    return out
import sys
for x in [0,0.9,2.15,3.35]:
    o=run(x*B)
    o.sort()
    e0=o[0][0]
    lv=[];
    for e,S in o:
        if lv and abs(e-lv[-1][0])<1 and lv[-1][1]==S: lv[-1][2]+=1
        else: lv.append([e,S,1])
    print(x,[(round((e-e0)/B,3),2*S+1,d) for e,S,d in lv][:8])
