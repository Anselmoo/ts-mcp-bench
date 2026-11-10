
cd /tmp/tsbench-run-me24kyq4 && python3 -c "
exec(open('ts.py').read())
P=proj(1.0); print(np.round(np.linalg.eigvalsh(P),6)); print(np.round(P,3))
# check test: free electrons, 1 electron
S,H=build(1,{},P); print(np.round(np.linalg.eigvalsh(H),6))
"