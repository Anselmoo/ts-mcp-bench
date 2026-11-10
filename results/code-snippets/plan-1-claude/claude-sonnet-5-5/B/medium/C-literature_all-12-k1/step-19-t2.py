exec(open('/dev/shm/t.py').read())
A=H-H.T
ij=np.argwhere(abs(A)>0.5)
print(len(ij))
for i,j in ij[:6]:
    print(dets[i],dets[j],H[i,j],H[j,i])
