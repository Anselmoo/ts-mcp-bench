
cd /tmp/tsbench-run-me24kyq4 && python3 -c "
exec(open('ts.py').read())
V=Vtab(1.0,3699/784)
for Dq in [1e-4,1e-3]:
  P=proj(Dq); S,H=build(7,V,P)
  nup=np.array([sum(1 for i in s if so[i][1]>0) for s in S])
  sel=np.where(nup==5)[0]
  print(Dq, np.round(np.linalg.eigvalsh(H[np.ix_(sel,sel)])/Dq,4))
# Coulomb only check
S,H=build(7,V,np.zeros((5,5),complex))
nup=np.array([sum(1 for i in s if so[i][1]>0) for s in S]); sel=np.where(nup==5)[0]
print('coul', np.round(np.linalg.eigvalsh(H[np.ix_(sel,sel)]),4))
"