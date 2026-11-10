import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
def ck(k,a,b): return float((-1)**a*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-a,a-b,b))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in range(-2,3) for b in range(-2,3)}
orbs=[(m,s) for s in (1,-1) for m in range(-2,3)]
def sgn_apply(st,ops):
    st=list(st); sign=1
    for typ,o in ops:
        if typ=='a':
            if o not in st: return None,0
            i=st.index(o); sign*=(-1)**i; st.pop(i)
        else:
            if o in st: return None,0
            st.insert(0,o)
            for i in range(len(st)-1):
                if st[i]>st[i+1]: st[i],st[i+1]=st[i+1],st[i]; sign=-sign
    return tuple(st),sign
def basis(Ms2): return [d for d in itertools.combinations(range(10),7) if sum(orbs[o][1] for o in d)==Ms2]
def Vm(Dq):
    V=np.zeros((5,5)); V[2,2]=6*Dq; V[1,1]=V[3,3]=-4*Dq; V[0,0]=V[4,4]=Dq; V[0,4]=V[4,0]=5*Dq; return V
def mats(Ms2):
    bs=basis(Ms2); ix={d:i for i,d in enumerate(bs)}; N=len(bs)
    MV=np.zeros((N,N)); M2=np.zeros((N,N)); M4=np.zeros((N,N)); V=Vm(1)
    for d in bs:
        i=ix[d]
        for p in range(10):
            for r in range(10):
                if orbs[p][1]!=orbs[r][1]: continue
                v=V[orbs[p][0]+2,orbs[r][0]+2]
                if v==0: continue
                nd,s=sgn_apply(d,[('a',r),('c',p)])
                if nd: MV[ix[nd],i]+=v*s
        for p,q in itertools.permutations(range(10),2):
            for r,s_ in itertools.permutations(range(10),2):
                if orbs[p][1]!=orbs[r][1] or orbs[q][1]!=orbs[s_][1]: continue
                m1,m2,m3,m4=orbs[p][0],orbs[q][0],orbs[r][0],orbs[s_][0]
                if m1+m2!=m3+m4: continue
                nd,s=sgn_apply(d,[('a',r),('a',s_),('c',q),('c',p)])
                if not nd: continue
                M2[ix[nd],i]+=0.5*s*CK[(2,m1,m3)]*CK[(2,m4,m2)]
                M4[ix[nd],i]+=0.5*s*CK[(4,m1,m3)]*CK[(4,m4,m2)]
    ML=np.array([sum(orbs[o][0] for o in d) for d in bs])
    return MV,M2,M4,ML
A=mats(1); Q=mats(3)
def levels(Dq,B,C):
    F2=49*B+7*C; F4=441*C/35
    out={}
    for key,(MV,M2,M4,ML) in (('1',A),('3',Q)):
        H=Dq*MV+F2*M2+F4*M4
        w,U=np.linalg.eigh(H); grp=[];i=0
        while i<len(w):
            j=i
            while j<len(w) and abs(w[j]-w[i])<1e-5: j+=1
            P=U[:,i:j]; ch=np.real(np.sum(np.conj(P)*(np.exp(1j*np.pi/2*ML)[:,None]*P)))
            grp.append((w[i],j-i,round(ch))); i=j
        out[key]=grp
    E0=out['3'][0][0]
    quart=[(round(e-E0,2),n,c) for e,n,c in out['3']]
    qE=[e for e,_,_ in quart]
    doub=[(round(e-E0,2),n,c) for e,n,c in out['1'] if all(abs(e-E0-x)>1e-3 for x in qE)]
    return quart,doub
q,d=levels(800,800,3500); print(q); print(d[:10])
def name(n,c): return {1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[n][c]
def model(p):
    Dq,B,C=p; q,d=levels(Dq,B,C)
    T2=[e for e,n,c in q if name(n,c)=='T2'][0]
    A2=[e for e,n,c in q if name(n,c)=='A2'][0]
    T1p=[e for e,n,c in q if name(n,c)=='T1'][1]
    dT1=[e for e,n,c in d if name(n,c)=='T1'][1]
    return np.array([T2,A2,T1p,dT1])
obs=np.array([6150,12400,16850,19000])
r=least_squares(lambda p:model(p)-obs,[650,800,3200]); print(r.x, model(r.x), model(r.x)-obs)
q,d=levels(*r.x); print(q); print([(e,name(n,c)) for e,n,c in d][:12])
r2=least_squares(lambda p:(model(p)-obs)[:3],[650,800]+[3200] ) 
