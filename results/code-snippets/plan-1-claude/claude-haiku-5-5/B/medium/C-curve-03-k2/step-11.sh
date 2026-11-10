
cd /tmp/tsbench-run-me24kyq4 && python3 -c "
exec(open('ts.py').read())
P=proj(1.0)
S,H=build(7,{},P)
nup=np.array([sum(1 for i in s if so[i][1]>0) for s in S])
for n in (5,4):
  sel=np.where(nup==n)[0]; print(n, np.round(np.linalg.eigvalsh(H[np.ix_(sel,sel)]),4))
"