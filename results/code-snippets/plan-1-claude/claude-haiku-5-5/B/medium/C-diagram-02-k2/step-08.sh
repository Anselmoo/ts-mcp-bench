cat << 'EOF' > group.py
import numpy as np
from scipy.spatial.transform import Rotation as Rot_
def octa_group():
    g1 = Rot_.from_rotvec(np.pi/2*np.array([0,0,1.])).as_matrix()
    g2 = Rot_.from_rotvec(2*np.pi/3*np.array([1,1,1.])/np.sqrt(3)).as_matrix()
    els = [np.eye(3)]
    changed = True
    while changed:
        changed = False
        for M in list(els):
            for g in (g1,g2):
                N = g@M
                if not any(np.allclose(N,X,atol=1e-8) for X in els):
                    els.append(N); changed = True
    assert len(els)==24, len(els)
    out=[]
    for M in els:
        t = np.trace(M)
        if np.isclose(t,3): cls='E'
        elif np.isclose(t,0): cls='C3'
        elif np.isclose(t,-1):
            cls = 'C2' if np.sum(np.abs(np.diag(M)))>2 else 'C2p'
        else: cls='C4'
        rv = Rot_.from_matrix(M).as_rotvec()
        ang = np.linalg.norm(rv)
        if ang<1e-12: ax=np.array([0,0,1.]); ang=0.0
        else: ax = rv/ang
        out.append((cls, ax, ang))
    return out
if __name__=="__main__":
    from collections import Counter
    print(Counter(c for c,_,_ in octa_group()))
EOF
python3 group.py