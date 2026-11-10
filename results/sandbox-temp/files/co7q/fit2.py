exec(open('d7.py').read())
from scipy.optimize import least_squares
def pick(L,lab,n):
    c=0
    for e,l in L:
        if l==lab:
            c+=1
            if c==n: return e
def res(x):
    L=names(*x)
    assert L[0][1]=='4T1'
    return [pick(L,'4T2',1)-8100,pick(L,'4T1',2)-19400,pick(L,'2T1',2)-21600]
r=least_squares(res,[900,800,3500],diff_step=1e-4,xtol=1e-12)
print(r.x,r.fun)
for e,n in names(*r.x)[:12]: print(round(e),n)
