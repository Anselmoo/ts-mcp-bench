exec(open('d7.py').read().split('def build')[0])
from scipy.optimize import least_squares
def build(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    V=(F2*A2+F4*A4).reshape(25,25)
    I5=np.eye(5)
    H=np.kron(Dq*h_dq,I5)+np.kron(I5,Dq*h_dq)+V
    Hs=Bm.conj().T@H@Bm
    return np.sort(np.linalg.eigvalsh((Hs+Hs.conj().T)/2)).real
# free-ion check: spectrum with Dq=0 relative
print("Dq=0,B=1,C=4.5:", build(0,1,4.5).round(3))
def levels(p):
    e=build(*p); return e
def sorted_levels(p):
    e=levels(p)
    # group: singleton(A2) and triplets
    return e
obs=np.array([7150,15200,19200.])
# levels: eigen list. Candidate assignment: find ground T1 = lowest triplet; T2, A2, T1P
def resid(p):
    Dq,B,C=p
    e=build(Dq,B,C)
    # unique energies with multiplicity
    vals=[]; mult=[]
    for x in e:
        if vals and abs(x-vals[-1])<1e-6: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    vals=np.array(vals); mult=np.array(mult)
    return vals,mult
print(resid([700,800,3500]))
