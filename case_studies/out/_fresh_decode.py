import sys, os, numpy as np
sys.path.insert(0, sys.argv[1])
import imcodec as ic
for p in sys.argv[2:]:
    data = open(p, 'rb').read()
    img = ic.decode(data)
    np.save(p + '.npy', img)
    print(f'  {os.path.basename(p)}: {len(data)} bytes in -> {img.shape} {img.dtype} out, mean {img.mean():.3f}')
