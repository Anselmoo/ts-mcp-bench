def q(p):
    Dq,B=p
    M=np.array([[-6*Dq,6*B],[6*B,15*B]]);e=np.linalg.eigvalsh(M)
    return [2*Dq-e[0],12*Dq-e[0],e[1]-e[0]]
r=least_squares(lambda p:np.array(q(p))-[6150,12400,16850],[800,800]);print(r.x,q(r.x))
Dq,B=r.x
for Cc in np.arange(2000,4001,500):
    print(Cc,[(round(x),n) for x,n in lev(Dq,B,Cc) if x<24000])
