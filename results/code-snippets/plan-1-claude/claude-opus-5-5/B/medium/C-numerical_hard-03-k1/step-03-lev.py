import numpy as np
m=np.load('mats.npz')
def levels(Dq,B,r=4.6):
    Cc=r*B
    H=Dq*m['HV']+(49*B+7*Cc)*m['HF2']/49*49/49*1+0*m['HF4']
    H=Dq*m['HV']+(49*B+7*Cc)/49*m['HF2']*1+ (441*Cc/35)/441*m['HF4']
    # F2 here is F^2 (unnormalized); F_2=F^2/49, F_4=F^4/441: F^2=49B+7C, F^4=63C
    H=Dq*m['HV']+(49*B+7*Cc)*m['HF2']+63*Cc*m['HF4']
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,m['S'],v)
    w=w-w[0];res=[]
    for e,ss in zip(w,s):
        if res and abs(e-res[-1][0])<1e-3: res[-1][2]+=1
        else: res.append([e,ss,1])
    return res
if __name__=='__main__':
    for x in levels(0,1000)[:4]: print(x)  # free ion check: 6S ground, 4G at 10B+5C
    for x in levels(2500,600)[:12]: print(np.round(x,2))
