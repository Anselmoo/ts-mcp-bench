
cd /tmp/tsbench-run-uqj8uf3b && cat << 'EOF' > fast.py
import numpy as np, itertools
from scipy.optimize import least_squares
from many import sec, sec5
P=np.load('pre.npz'); LF=P['LF'];V2=P['V2'];V4=P['V4']
LFs=LF[np.ix_(sec,sec)]; V2s=V2[np.ix_(sec,sec)]; V4s=V4[np.ix_(sec,sec)]
LF5=LF[np.ix_(sec5,sec5)]; V25=V2[np.ix_(sec5,sec5)]; V45=V4[np.ix_(sec5,sec5)]
def Hs(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    return Dq*LFs+F2*V2s+F4*V4s
def e6(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    return np.linalg.eigvalsh(Dq*LF5+F2*V25+F4*V45)[0]
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(Hs(Dq,B,C))-e6(Dq,B,C)
    vals=[]
    for x in np.sort(e):
        if vals and abs(x-vals[-1][0])<1e-6: vals[-1][1]+=1
        else: vals.append([x,1])
    return vals
if __name__=="__main__":
    print(levels(800,800,3200))
EOF
python3 fast.py