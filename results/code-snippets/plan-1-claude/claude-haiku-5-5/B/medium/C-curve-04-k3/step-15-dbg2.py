exec(open('d5.py').read().split('for Dq in')[0])
for Dq in [0.0,2.55]:
    H=hd_op(Dq)+H2
    e=np.linalg.eigvalsh(H)
    print("Dq",Dq, np.round(np.unique(np.round(e,4)),3))
    print("ev2 sectors", np.unique(np.round(np.linalg.eigvalsh(S2),3),return_counts=True))
    res=levels(Dq)
    for r in res: print(r)
