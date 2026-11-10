cat > scan.py << 'EOF'
import d5, numpy as np, itertools, time
from fit import doublets
def levels(Dq,B):
    E=doublets(Dq,B)  # per-state list with multiplicity
    vals=[]
    for e in E:
        if vals and abs(e-vals[-1][0])<1e-6: vals[-1][1]+=1
        else: vals.append([e,1])
    return [(v,m) for v,m in vals]
if __name__=="__main__":
    t=time.time()
    for r in [1.5,2.0,2.5]:
        L=levels(r,1.0)
        print(r,[(round(v,4),m) for v,m in L[:10]])
    print(time.time()-t)
EOF
python3 scan.py