from a import *
t=[13960,22740,29700]
def err(B,Dq):
    lv=bands(B,Dq)[1:4]
    return sum((l[0]-x)**2 for l,x in zip(lv,t)),lv
best=None
for B in range(300,700,50):
  for Dq in range(1500,3500,100):
    e,lv=err(B,Dq)
    if best is None or e<best[0]: best=(e,B,Dq,lv)
print(best)
e,B,Dq,_=best
step=[25,50]
x=[B,Dq];fx=e
for it in range(40):
    imp=False
    for i in (0,1):
        for s in (-1,1):
            y=x[:];y[i]+=s*step[i]
            fy=err(*y)[0]
            if fy<fx:x,fx,imp=y,fy,True
    if not imp:
        step=[s/2 for s in step]
        if step[0]<0.2:break
print(x,fx,err(*x)[1])
