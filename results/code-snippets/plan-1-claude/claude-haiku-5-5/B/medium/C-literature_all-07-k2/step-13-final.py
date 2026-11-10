import numpy as np
from scipy.optimize import least_squares
from model import model
def res(x):
    Dq,B=x; C=(23000-17*B)/5
    T,E=model([Dq,B,C])
    return [T[0]-19240, T[1]-21890]
for g in [(700,700),(900,600),(600,800)]:
    s=least_squares(res,g,diff_step=1e-4,x_scale=[100,100])
    Dq,B=s.x; C=(23000-17*B)/5
    print(s.x, C, s.fun, model([Dq,B,C]))
