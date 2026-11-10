pwd && ls && cat > test2.py << 'EOF'
from ts import *
for F2,F4 in [(1.0,0.0),(1.0,0.6),(1.0,1.2)]:
    G=coulomb_tensor({0:0.0,2:F2,4:F4})
    states,idx,H=build_H(2,np.zeros((10,10)),G)
    S2=spin_S2(2)
    w,v=np.linalg.eigh(H+100*S2)
    out={}
    for e,vec in zip(w,v.T):
        S=round((-1+np.sqrt(1+4*np.real(vec.conj()@S2@vec)))/2)
        key=(round(e-100*S*(S+1),6),S)
        out[key]=out.get(key,0)+1
    base=min(out, key=lambda k:k[0])
    B=(9*F2-5*F4)/441; C=35*F4/441
    print("F4=",F4, "trace/45",np.trace(H).real/45, {k:(round((k[0]-base[0])/B,3)) for k in out})
EOF
python3 test2.py 2>&1 | grep -v -i matplotlib