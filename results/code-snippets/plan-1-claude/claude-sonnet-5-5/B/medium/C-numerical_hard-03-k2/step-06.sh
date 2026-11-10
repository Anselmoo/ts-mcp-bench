cd $TMPDIR && cat > b.py <<'E'
from a import *
n=len(dets)
def op(ops_list):
    M=np.zeros((n,n))
    for j,det in enumerate(dets):
        for ops,c in ops_list:
            r=apply(det,ops)
            if r and r[0] in di: M[di[r[0]],j]+=c*r[1]
    return M
# S+ maps Ms=1/2 -> 3/2 out of sector; use S-S+ = S^2 - Sz - Sz^2 ; instead use S+S- : goes to Ms=-1/2 sector. Use S^2 = S+S- + Sz^2 - Sz via two-step with full dets
import itertools
def S2():
    M=np.zeros((n,n))
    for j,det in enumerate(dets):
        # S- then S+ : S+S- = sum_{m,m'} a†_{mα}a_{mβ} a†_{m'β}a_{m'α}
        for m in range(5):
            for mp in range(5):
                ops=[(mp,0),(5+mp,1),(5+m,0),(m,1)]  # alpha idx 0..4 ; beta 5..9 (so spin 0 = first 5)
                r=apply(det,ops)
                if r: M[di[r[0]],j]+=r[1]
    return M+0.25*np.eye(n)-0.5*np.eye(n)
S=S2()
def levels(Dq,B,C):
    F2=49*B+7*C;F4=63*C/5
    H1=h1(Dq);H=np.zeros((n,n),complex)
    for i,j,p,q,s in one: H[i,j]+=H1[p,q]*s
    for i,j,a,s in two: H[i,j]+=0.5*s*(F2*A[2][a]/49+F4*A[4][a]/441)
    # add penalty for S>1/2: S2 - 0.75
    H=H+1e6*(S-0.75*np.eye(n))
    return np.linalg.eigvalsh(H)
def fit(Dq,B,C):
    e=levels(Dq,B,C); return e
if __name__=="__main__":
    e=levels(0,800,3680);print(np.round(e[:5]))
    e=levels(3000,600,2760);e=e[e<1e5];print(len(e),np.round(e-e[0])[:20])
E
python3 b.py