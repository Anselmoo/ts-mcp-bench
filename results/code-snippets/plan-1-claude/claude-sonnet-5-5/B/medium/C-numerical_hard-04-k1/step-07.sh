cd /dev/shm && cat > b.py <<'E'
from a import *
def lv(Dq,B):
    w=levels(Dq,B,4.4*B); w=w[w<5e5]; w=w-w[0]
    gr=[]
    for x in w:
        if gr and abs(x-gr[-1])<0.5: continue
        gr.append(x)
    return gr[1:4]
t=np.array([29360,29620,31640])
best=[]
for Dq in range(1500,4001,100):
    for B in range(200,1000,25):
        l=np.array(lv(Dq,B));best.append((np.sum((l-t)**2),Dq,B,l))
best.sort(key=lambda x:x[0])
for b in best[:6]:print(b)
E
python3 b.py