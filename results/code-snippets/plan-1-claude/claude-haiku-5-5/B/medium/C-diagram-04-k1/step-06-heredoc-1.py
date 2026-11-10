import re
src = open('ts.py').read()
src = src.replace("""    chi = {cl:0 for cl in classes}
    for cls,U in group:
        chi[cls] += np.trace(V.conj().T @ U @ V)""","""    chi = {cl:[] for cl in classes}
    for cls,U in group:
        chi[cls].append(np.trace(V.conj().T @ U @ V))
    chi = {cl: np.mean(chi[cl]) for cl in classes}""")
open('ts.py','w').write(src)
