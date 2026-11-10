import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,S2=np.load('mats.npy')
obs=np.array([13960,22740,29700])
def lv(Dq,B):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]; w-=w.min()
    out=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)
sols=set()
for Dq in np.arange(1000,5001,250):
  for B in np.arange(200,1801,100):
    try:
      r=least_squares(lambda p: lv(*p)[1:4]-obs,[Dq,B],bounds=([500,50],[8000,3000]))
      sols.add((round(r.x[0]),round(r.x[1]),round(np.sqrt(np.mean(r.fun**2)))))
    except Exception as e: pass
for s in sorted(sols,key=lambda s:s[2])[:10]: print(s)
