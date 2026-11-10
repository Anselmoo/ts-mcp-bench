import numpy as np
d=np.load('mats.npz'); Hcf,H2,H4,S2=d['Hcf'],d['H2'],d['H4'],d['S2']
def levels(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    H=Dq*Hcf+F2*H2+F4*H4
    w,v=np.linalg.eigh(H+1000*S2)   # separate by S
    out=[]
    for i in range(len(w)):
        s2=v[:,i]@S2@v[:,i]
        E=w[i]-1000*s2
        out.append((round(s2,3),E))
    # unique
    res={}
    for s2,E in out:
        res.setdefault(s2,[]).append(E)
    return res
if __name__=='__main__':
    r=levels(0,1,0)
    for s2 in sorted(r):
        vals=np.round(np.array(sorted(r[s2])),4)
        # group
        g=[]
        for x in vals:
            if g and abs(g[-1][0]-x)<1e-3: g[-1][1]+=1
            else: g.append([x,1])
        print('S2=',s2, g)
