cd <SANDBOX_TMP>/ts && cat > run.py << 'EOF'
exec(open('ts.py').read())
import numpy as np
Ms = np.array([[0]])
Qidx = np.where(np.isclose(np.diag(Sz),1.5))[0]
Didx = np.where(np.isclose(np.diag(Sz),0.5))[0]
# quartet block
Bq = np.eye(ND)[:,Qidx]
# doublet block: S2 = 3/4 subspace within Sz=1/2 sector
S2d = S2[np.ix_(Didx,Didx)]
w, v = np.linalg.eigh(S2d)
Bd = np.eye(ND)[:,Didx] @ v[:, np.isclose(w,0.75)]
print('doublet block dim', Bd.shape[1], 'quartet dim', Bq.shape[1])
dimsB = {'4':Bq, '2':Bd}
Lett = {0:'S',1:'P',2:'D',3:'F',4:'G',5:'H',6:'I'}
def proj_basis(Bm, name):
    Ub = [Bm.T @ U @ Bm for U in Us]
    P = np.zeros_like(Ub[0])
    d = dimI[name]
    for g in range(24):
        P += irreps[name][order.index(classes[g])] * Ub[g]
    P *= d/24
    w, v = np.linalg.eigh((P+P.T)/2)
    Qm = v[:, w>0.5]
    return Qm
blocks = {}
for sname, Bm in dimsB.items():
    for name in dimI:
        Qm = proj_basis(Bm, name)
        if Qm.shape[1]==0: continue
        blocks[(sname,name)] = (Bm @ Qm, dimI[name])
# Dq=0 analysis
H0 = Hee
levels0 = {}
for key,(Bfull,d) in blocks.items():
    Hb = Bfull.T @ H0 @ Bfull
    Lb = Bfull.T @ L2 @ Bfull
    w, v = np.linalg.eigh(Hb)
    lst = []
    for k in range(0, len(w), d):
        Lval = v[:,k] @ Lb @ v[:,k]
        # check
        lst.append((w[k], Lval, k))
    levels0[key] = lst
    print(key, [(round(e,4), round(L,3)) for e,L,_ in lst])
EOF
python3 run.py