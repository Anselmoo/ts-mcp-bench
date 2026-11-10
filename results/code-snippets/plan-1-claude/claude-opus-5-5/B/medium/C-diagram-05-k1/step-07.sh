cd $TMPDIR && python3 -c "
exec(open('ts.py').read())
for dq in np.arange(0,4.01,0.5):
    L=levels(max(dq,1e-4))
    print(dq,[(f'{m}{lab}',round((e-L[0][0])/B,3)) for e,m,lab in L[:8]])
"