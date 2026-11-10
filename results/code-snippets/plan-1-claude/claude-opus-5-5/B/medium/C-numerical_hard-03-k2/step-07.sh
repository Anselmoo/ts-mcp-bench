
cd $TMPDIR && cat << 'EOF' > grid.py
exec(open('d5.py').read())
H0=build(0,0,0);Hd=build(1,0,0)-H0;Hb=build(0,1,0)-H0;Hc=build(0,0,1)-H0
def lev(Dq,B):
    w,v=np.linalg.eigh(Dq*Hd+B*Hb+4.6*B*Hc)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    return w,s
obs=np.array([22640,22930,25080])
res=[]
for Dq in np.arange(1000,6001,50):
  for B in np.arange(100,1501,25):
    w,s=lev(Dq,B)
    D=np.unique(np.round(w[s<1],2)); g=D[0]
    d=D[1:4]-g
    res.append((round(np.sqrt(np.mean((d-obs)**2))),Dq,B,round(s[0],2),np.round(d)))
res.sort(key=lambda r:r[0])
for r in res[:6]: print(r)
print('low-spin only:')
for r in [r for r in res if r[3]<1][:8]: print(r)
EOF
timeout 110 python3 grid.py
