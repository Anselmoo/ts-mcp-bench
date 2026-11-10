
cd $TMPDIR && cat << 'EOF' > grid.py
exec(open('d5.py').read())
obs=np.array([22640,22930,25080])
res=[]
for Dq in np.arange(1000,6001,100):
  for B in np.arange(100,1501,50):
    L=levels(Dq,B,4.6*B)
    D=[x[0] for x in L if x[2]<1]; g=D[0]
    d=np.array([x-g for x in D[1:4]])
    res.append((np.sqrt(np.mean((d-obs)**2)),Dq,B,L[0][2],d))
res.sort(key=lambda r:r[0])
for r in res[:8]: print(r)
print('low-spin only:')
for r in [r for r in res if r[3]<1][:8]: print(r)
EOF
python3 grid.py
