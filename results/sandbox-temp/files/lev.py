import numpy as np
m=np.load('mats.npz')
def levels(Dq,B,r=4.6):
    Cc=r*B
    H=Dq*m['HV']+((49*B+7*Cc)*m['HF2']+12.6*Cc*m['HF4'])/25
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,m['S'],v)
    w=w-w[0];res=[]
    for e,ss in zip(w,s):
        if res and abs(e-res[-1][0])<1e-3: res[-1][2]+=1
        else: res.append([e,ss,1])
    return res
if __name__=='__main__':
    for x in levels(0,1000)[:4]: print(np.round(x,2))
    for x in levels(2500,600)[:12]: print(np.round(x,2))
