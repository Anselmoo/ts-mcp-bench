cat > fit.py << 'EOF'
import d3, numpy as np
S2=d3.spin2().real
ws,vs=np.linalg.eigh(S2)
def sector(S):
    return vs[:, np.abs(ws-S*(S+1))<1e-6]
Q=sector(1.5); D=sector(0.5)
def levels(Dq,B,Cc):
    H=d3.build_H(Dq,B,Cc)
    res={}
    for lab,U in [('Q',Q),('D',D)]:
        res[lab]=np.linalg.eigvalsh(U.conj().T@H@U)
    return res
if __name__=="__main__":
    print(Q.shape,D.shape)
    L=levels(0,780,3500)
    print(np.unique(np.round(L['Q'],2),return_counts=True))
    print(np.unique(np.round(L['D'],2),return_counts=True))
    L=levels(1743,780,3500)
    print(np.unique(np.round(L['Q'],2),return_counts=True))
    print(np.unique(np.round(L['D'],2),return_counts=True))
EOF
python3 fit.py