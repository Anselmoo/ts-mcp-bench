from ts import *
F2,F4=1.0,0.6
F={0:0.0,2:F2,4:F4}
G=coulomb_tensor(F)
states,idx,H=build_ops(2,np.zeros((10,10)),G)
w=np.linalg.eigvalsh(H)
B=(9*F2-5*F4)/441; C=35*F4/441
print("B,C",B,C)
vals=np.unique(np.round(w,6))
print(vals, len(w))
print("expected 3F ~ ",vals[0],"3P-3F/B:",(vals[np.argmin(abs(vals-vals[0]-15*B))] if False else None))
