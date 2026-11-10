from ts import *
B=806.;Cc=3570.
def lab(d,S,c4,c2):
    mult=int(round(2*S+1)); 
    # character per orbital irreps: dim from d/(mult)?? deg counts spin comps? 
    return mult
for x in [0,1,2,3,4]:
    o=levels(B,Cc,x)
    print(x)
    for w,deg,S,c4,c2 in o[:14]: print(round(w/B,3),deg,round(S,2),c4,c2)
