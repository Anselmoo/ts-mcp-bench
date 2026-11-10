import numpy as np
from math import pi
exec(open("d5.py").read().split("def restrict")[0])
def R(M): return M[np.ix_(sel,sel)]
D=len(sel)
H1 = np.zeros((dim,dim),dtype=complex)
for a in range(N):
  for b in range(N):
    if a%2!=b%2: continue
    H1 += h1[a//2,b//2]*(Cd[a]@C_[b])
H2 = np.zeros((dim,dim))
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    if a%2!=c%2 or b%2!=d%2: continue
    v=V2(ms[a//2],ms[b//2],ms[c//2],ms[d//2])
    if abs(v)<1e-12: continue
    H2 += 0.5*v*(Cd[a]@Cd[b]@C_[d]@C_[c])
Sp = sum(Cd[2*o]@C_[2*o+1] for o in range(5))
Sz = 0.5*sum(Cd[2*o]@C_[2*o]-Cd[2*o+1]@C_[2*o+1] for o in range(5))
S2 = Sz@Sz + 0.5*(Sp@Sp.T+Sp.T@Sp)
H1=np.real(R(H1)); H2=R(H2); S2=R(S2)
print("H1 sym", np.allclose(H1,H1.T), "H2 sym", np.allclose(H2,H2.T), "S2 eig", np.unique(np.round(np.linalg.eigvalsh(S2),3)))
np.save("H1.npy",H1); np.save("H2.npy",H2); np.save("S2.npy",S2)
