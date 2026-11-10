import numpy as np
H1,HB,HC,S2=np.load('mats.npy')
def lv(Dq,B):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]; w-=w.min()
    out=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)
for Dq,B in [(1660,549),(2000,600)]:
    print(Dq,B,np.round(lv(Dq,B)[:6]))
    w,v=np.linalg.eigh(Dq*H1+B*(HB+4.5*HC)); print(np.round(w[:20]-w[0]))
