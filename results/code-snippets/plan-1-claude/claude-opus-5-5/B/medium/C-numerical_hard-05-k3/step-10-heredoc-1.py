import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,S2=np.load('mats.npy')
def lv(Dq,B):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]; w-=w.min()
    out=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)
for pair in [(1,2),(1,3),(2,3)]:
  ob=np.array([13960,22740,29700])
  for g in [[1800,500],[2500,700],[3300,1500]]:
    r=least_squares(lambda p: lv(*p)[list(pair)]-ob[[i-1 for i in pair]],g,bounds=([500,50],[8000,3000]))
    print(pair,np.round(r.x),np.round(lv(*r.x)[1:5]))
