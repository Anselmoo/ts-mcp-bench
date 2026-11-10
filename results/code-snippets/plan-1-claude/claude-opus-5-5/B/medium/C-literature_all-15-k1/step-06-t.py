exec(open('d7.py').read().split("print(names")[0])
H=1000*HB+4000*HC
w,U=np.linalg.eigh(H)
vals=np.round(w-w[0]).astype(int)
u,c=np.unique(vals,return_counts=True)
for a,b in zip(u,c):
    P=U[:,np.abs(w-w[0]-a)<1]; S=np.trace(P.T@S2@P)/b
    print(a,b,round(S,3))
