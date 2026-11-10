import re
s=open('<SANDBOX_TMP>/a.py').read()
s=s.split("# S^2")[0]
s+='''
alld=[d for d in itertools.combinations(range(10),7) if sum(1 if i%2==0 else -1 for i in d)==-1]
id2={d:i for i,d in enumerate(alld)}
Sm=np.zeros((len(alld),n))
for j,dt in enumerate(dets):
    for o in range(5):
        sg,nd=apply([('c',2*o+1),('a',2*o)],dt)
        if sg: Sm[id2[nd],j]+=sg
S2=Sm.T@Sm+0.25*np.eye(n)-0.5*np.eye(n)
def lv(Dq):
    H=H2+Dq*HL
    w,v=np.linalg.eigh((H+H.conj().T)/2)
    s2=np.real(np.einsum('ij,ik,kj->j',v.conj(),S2,v))
    q=w[abs(s2-3.75)<.1].min(); d=w[abs(s2-.75)<.1].min()
    return q-d
for D in (500,1000,1500,2000,3000): print(D,lv(D))
print(brentq(lv,500,3000))
'''
open('<SANDBOX_TMP>/b.py','w').write(s)
