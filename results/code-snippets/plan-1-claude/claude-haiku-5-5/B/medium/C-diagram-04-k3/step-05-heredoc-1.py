src = open('ts.py').read()
src = src.replace("mult = sum(chars[g]*tab[cls[g]] for g in range(24))/24",
                  "mult = sum(chars[g]*tab[cls[g]] for g in range(24))/24/round(2*S+1)")
src = src.replace("for _ in range(int(round(mult.real))):", "for _ in range(int(round(mult.real))):")
open('ts.py','w').write(src)
