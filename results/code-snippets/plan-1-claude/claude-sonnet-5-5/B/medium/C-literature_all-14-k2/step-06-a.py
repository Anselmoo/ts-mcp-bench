def levels(B,C,Dq):
    F4=C/35;F2=B+5*F4
    e=np.linalg.eigvalsh(49*F2*H2+441*F4*H4+Dq*H1);e=e-e[0]
    u=[]
    for x in e:
        if not u or abs(x-u[-1][0])>1: u.append([round(x),1])
        else: u[-1][1]+=1
    return u
