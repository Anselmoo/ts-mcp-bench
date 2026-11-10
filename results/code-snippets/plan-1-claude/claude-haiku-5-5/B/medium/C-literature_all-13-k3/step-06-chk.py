exec(open('d7.py').read().split('A2=ang')[0])
A0=ang(0); print(A0[2,2,2,2], A0[0,1,0,1], A0[0,1,1,0])
A2=ang(2); print(np.round(A2[2,2,2,2].real,4), np.round(A2[0,0,0,0].real,4), np.round(A2[2,1,2,1].real,4))
print(np.round(ang(2)[2,0,0,2].real,4), np.round(ang(2)[0,2,2,0].real,4))
