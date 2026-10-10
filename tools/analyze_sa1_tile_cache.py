"""採取済み画面のタイル再利用率を、速度費用を含まない楽観的LRUで測る。"""
import argparse,json
from collections import OrderedDict
from pathlib import Path
import numpy as np


def analyze(directory,flip_normalize=False):
    frames=[]
    for path in sorted(directory.glob('present*_fb.bin')):
        generation=int(path.name[7:12])
        if not 530<=generation<=570:continue
        pixels=np.frombuffer(path.read_bytes(),np.uint8).reshape(192,128)
        tiles=pixels.reshape(24,8,32,4).transpose(0,2,1,3).reshape(768,32)
        keys=[]
        for tile in tiles[32:]:
            if not tile.any():continue
            if flip_normalize:
                a=tile.reshape(8,4)
                b=((a>>4)|(a<<4))[:,::-1]
                keys.append(min(a.tobytes(),a[::-1].tobytes(),b.tobytes(),b[::-1].tobytes()))
            else:keys.append(bytes(tile))
        frames.append((generation,keys))
    assert len(frames)==41,'負荷集中期間の連続41画面が必要'
    results=[]
    for capacity in (384,512,768,1024,1536):
        cache=OrderedDict();rows=[]
        for generation,keys in frames:
            misses=0
            for key in dict.fromkeys(keys):
                if key in cache:cache.move_to_end(key)
                else:
                    misses+=1;cache[key]=None
                    if len(cache)>capacity:cache.popitem(last=False)
            rows.append(dict(generation=generation,nonemptyTiles=len(keys),
                             uniqueTiles=len(set(keys)),misses=misses))
        results.append(dict(capacity=capacity,frames=rows,
                            uniqueTileRequests=sum(row['uniqueTiles'] for row in rows),
                            misses=sum(row['misses'] for row in rows)))
    return dict(source=str(directory),flipNormalize=flip_normalize,costModel='ideal LRU; front/queued tiles not protected; hashing/copy/DMA setup costs excluded',results=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--flip-normalize',action='store_true');args=parser.parse_args()
    result=analyze(args.directory,args.flip_normalize);text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
