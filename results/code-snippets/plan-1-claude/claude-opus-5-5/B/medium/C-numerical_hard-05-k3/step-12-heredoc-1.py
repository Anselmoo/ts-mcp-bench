import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,S2=np.load('mats.npy')
def lv(Dq,B):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]; w-=w.min()
    out=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)
ob=np.array([13960,22740])
r=least_squares(lambda p: lv(*p)[1:3]-ob,[1700,550],bounds=([1000,200],[2500,1000]))
print(r.x, r.fun, lv(*r.x)[1:6])
