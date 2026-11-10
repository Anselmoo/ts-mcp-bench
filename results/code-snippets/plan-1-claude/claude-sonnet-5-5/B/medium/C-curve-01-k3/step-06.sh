cd <SANDBOX_TMP>; python3 -c "
exec(open('a.py').read().split('\nfor x in (0.9')[0])
print(C_[(2,0,0)],C_[(4,0,0)],C_[(2,1,1)],V(0,0,0,0),F)"