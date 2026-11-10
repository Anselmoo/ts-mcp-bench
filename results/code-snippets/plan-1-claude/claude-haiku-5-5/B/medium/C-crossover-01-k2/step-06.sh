python3 -c "
import d4,numpy as np
from scipy.optimize import brentq
Hee,Hf,S2=d4.build_parts(706,2734)
w,v=np.linalg.eigh(S2)
Tb=v[:,np.abs(w-2)<1e-6]; Qb=v[:,np.abs(w-6)<1e-6]
print('dims triplet, quintet', Tb.shape[1], Qb.shape[1])
Ht=Tb.T@(Hee)@Tb; Ft=Tb.T@Hf@Tb
Hq=Qb.T@Hee@Qb; Fq=Qb.T@Hf@Qb
print('quintet ee eig', np.round(np.linalg.eigvalsh(Hq),2))
print('quintet field eig', np.round(np.linalg.eigvalsh(Fq),2))
def trip_low(Dq): return np.linalg.eigvalsh(Ht+Dq*Ft)[0]
def quint_low(Dq): return np.linalg.eigvalsh(Hq+Dq*Fq)[0]
def diff(Dq): return trip_low(Dq)-quint_low(Dq)
for D in [0,500,1000,2000,2500,3000,3500,4000]:
    print(D, round(trip_low(D),1), round(quint_low(D),1))
D=brentq(diff,1000,4000); print('crossover Dq',D, 'Dq/B',D/706)
"