"""v001のGSU出力2枚から、差分DMAのデータ量を比較する。転送時間の実測ではない。"""

import hashlib
import json

from run_probe import BUILD, PROBE
from run_scene_probe import command


def intervals(indices):
    return sum(i-1 not in indices for i in indices)


def main():
    scenes=json.loads((BUILD/'scene_results.json').read_text())
    items=[]
    tile_sets=[]
    for scene in scenes:
        name=scene['scene']
        data=(BUILD/name/(name+'.bin')).read_bytes()
        assert len(data)==12288
        tiles=[data[i:i+16] for i in range(0,len(data),16)]
        nonzero={i for i,tile in enumerate(tiles) if any(tile)}
        rectangles=set()
        for i,width in enumerate(scene['widths']):
            c=command(width,i)
            x,y=c['regs'][1:3]
            w,h=c['width'],c['regs'][6]
            assert 0<=x and x+w<=256 and 0<=y and y+h<=192
            rectangles.update(tx*24+ty for tx in range(x//8,(x+w-1)//8+1)
                              for ty in range(y//8,(y+h-1)//8+1))
        assert nonzero<=rectangles
        items.append(dict(scene=name,framebuffer_sha256=hashlib.sha256(data).hexdigest(),
                          nonzero_tiles=len(nonzero),nonzero_bytes=len(nonzero)*16,
                          rectangle_tiles=len(rectangles),rectangle_bytes=len(rectangles)*16))
        tile_sets.append((tiles,nonzero,rectangles))
    a,b=tile_sets
    sets={
        'actual_changed':{i for i in range(768) if a[0][i]!=b[0][i]},
        'nonzero_union':a[1]|b[1],
        'rectangle_union':a[2]|b[2],
    }
    result=dict(cases=items,transition={name:dict(tiles=len(s),bytes=len(s)*16,
                                                contiguous_intervals=intervals(s)) for name,s in sets.items()},
                scope='offline analysis of two artificial GSU scenes, excludes scan/setup/DMA time',
                selection_code_sha256=hashlib.sha256((PROBE.parent.parent/'tools/run_scene_probe.py').read_bytes()).hexdigest())
    dest=PROBE/'results/tile_analysis.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
