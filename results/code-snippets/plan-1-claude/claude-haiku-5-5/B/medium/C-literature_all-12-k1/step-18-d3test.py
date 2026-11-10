import ts, numpy as np
b=ts.occ_states(3,3)
Mcf,M=ts.build(b)
Dq,B,C=1740,918,3500
F2=49*B+7*C; F4=63*C/5
H=Dq*Mcf+F2*M[2]+F4*M[4]
print("d3 quartets rel to ground:", np.round(np.linalg.eigvalsh(H)-np.linalg.eigvalsh(H)[0],0))
