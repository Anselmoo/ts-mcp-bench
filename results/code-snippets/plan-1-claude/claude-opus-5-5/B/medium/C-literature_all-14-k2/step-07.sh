
D=$TMPDIR/co7q; mkdir -p $D; cd $D && cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms if abs(a-b)<=k}
def R(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(F[k]*CK.get((k,a,c),0)*CK.get((k,d,b),0) for k in (0,2,4))
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    F={0:0,2:(B+C/7)*49,4:C/35*441}
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets); H=np.zeros((N,N))
    for d in dets:
        I=idx[d]
        for p in range(10):
            for q in d:
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[p][0]+2,orbs[q][0]+2]
                if v==0: continue
                l=list(d); i=l.index(q); sg=(-1)**i; l.pop(i)
                if p in l: continue
                j=sum(1 for x in l if x<p); l.insert(j,p); sg*=(-1)**j
                H[idx[tuple(l)],I]+=sg*v
        for r_ in d:
          for s_ in d:
            if r_==s_: continue
            for p in range(10):
              for q in range(10):
                if p==q: continue
                if orbs[p][1]!=orbs[r_][1] or orbs[q][1]!=orbs[s_][1]: continue
                v=R(orbs[p][0],orbs[q][0],orbs[r_][0],orbs[s_][0],F)
                if v==0: continue
                l=list(d); sg=1
                i=l.index(s_); sg*=(-1)**i; l.pop(i)
                i=l.index(r_); sg*=(-1)**i; l.pop(i)
                if q in l: continue
                j=sum(1 for x in l if x<q); l.insert(j,q); sg*=(-1)**j
                if p in l: continue
                j=sum(1 for x in l if x<p); l.insert(j,p); sg*=(-1)**j
                H[idx[tuple(l)],I]+=0.5*sg*v
    return H
Ms=np.array([sum(0.5 if orbs[o][1]==0 else -0.5 for o in d) for d in dets])
ML=np.array([sum(orbs[o][0] for o in d) for d in dets])
c4=np.exp(1j*np.pi/2*ML)
HD=build(1,0,0); HB=build(0,1,0); HC=build(0,0,1)
def names(Dq,B,C):
    Ht=Dq*HD+B*HB+C*HC
    s1=Ms==0.5; s3=Ms==1.5
    q=np.linalg.eigvalsh(Ht[np.ix_(s3,s3)])
    w,v=np.linalg.eigh(Ht[np.ix_(s1,s1)]); c=c4[s1]
    out=[];i=0
    sym={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-6: j+=1
        tr=round(float(np.real(np.sum(np.abs(v[:,i:j])**2*c[:,None]))))
        S='4' if np.any(abs(q-w[i])<1e-6) else '2'
        out.append((w[i],S+sym.get(j-i,{}).get(tr,'?%d_%d'%(j-i,tr)))); i=j
    g=out[0][0]
    return [(e-g,n) for e,n in out]
EOF
sed -i 's/\*(-1)\*\*m1\*np.sqrt/*np.sqrt/' d7.py
cat << 'EOF' > fit.py
exec(open('d7.py').read())
for e,n in names(900,800,3500)[:14]: print(round(e),n)
print(names(0,1000,4000)[:8])
EOF
python3 fit.py
