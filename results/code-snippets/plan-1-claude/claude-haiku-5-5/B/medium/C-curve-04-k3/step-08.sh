mkdir -p /dev/shm/d5 && cd /dev/shm/d5 && cat << 'EOF' > d5.py
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
from collections import Counter

nt, nph = 60, 120
x, w = leggauss(nt)
ph = np.arange(nph)*2*np.pi/nph
ct, PH = np.meshgrid(x, ph, indexing='ij')
st = np.sqrt(1-ct**2)
P = np.stack([st*np.cos(PH), st*np.sin(PH), ct], -1).reshape(-1,3)
W = (np.repeat(w[:,None], nph, 1)*(2*np.pi/nph)).reshape(-1)

def forb(p):
    X,Y,Z = p[:,0],p[:,1],p[:,2]
    return np.stack([X*Y, Y*Z, Z*X, X**2-Y**2, 3*Z**2-(X**2+Y**2+Z**2)],1)
F = forb(P)
F = F/np.sqrt(np.einsum('k,ki->i', W, F**2))
h1 = np.array([-4,-4,-4,6,6],float)

def Rz(t):
    c,s=np.cos(t),np.sin(t); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
C4 = Rz(np.pi/2)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]],float)
def key(R): return tuple(np.round(R,8).reshape(-1))
G = {key(np.eye(3)):np.eye(3)}
frontier=[np.eye(3)]
while frontier:
    new=[]
    for A in frontier:
        for g in (C4,C3):
            B = g@A
            if key(B) not in G:
                G[key(B)]=B; new.append(B)
    frontier=new
print("group order", len(G))
G = list(G.values())
EOF
python3 -c "
exec(open('d5.py').read())
print(np.linalg.det(C3), np.linalg.det(C4))
"