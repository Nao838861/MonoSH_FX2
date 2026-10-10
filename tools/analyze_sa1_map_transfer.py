"""保存した実VRAMから、マップの高byte更新を省ける量を調べる。"""
import argparse
import json
from pathlib import Path
import struct


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('scenario')
    args=parser.parse_args()
    folder=Path(__file__).resolve().parents[1]/'build/sa1_game'/args.scenario
    pages={page:(True,None) for page in (0,0x2000,0x4000)}
    previous_generation=0
    rows=[]
    for path in sorted(folder.glob('present*_meta.bin')):
        generation=int(path.name[7:12])
        raw=path.read_bytes()
        page=struct.unpack_from('<H',raw,8)[0]
        vram=(folder/(path.name[:-9]+'_vram.bin')).read_bytes()
        tilemap=struct.unpack_from('<736H',vram,page*2+0x800+64)
        assert all((tile&0xfe00)==0x2400 for tile in tilemap)
        positions=[i for i,tile in enumerate(tilemap) if tile&0x100]
        current=(min(positions),max(positions)+1) if positions else None
        # 120枚以降は捕捉を60世代ごとへ間引くため、旧ページの範囲は不明。
        if generation!=previous_generation+1:
            pages={page:(False,None) for page in pages}
        known,old=pages[page]
        ranges=[r for r in (old,current) if r]
        high_bytes=max(r[1] for r in ranges)-min(r[0] for r in ranges) if ranges else 0
        rows.append({'generation':generation,'pageWord':page,
                     'nonzeroTiles':sum((tile&1023)!=128 for tile in tilemap),
                     'currentHighRange':current,
                     'highRangeBytes':current[1]-current[0] if current else 0,
                     'previousPageKnown':known,
                     'proposedMapBytes':736+high_bytes if known else None,
                     'oldMapBytes':1472})
        pages[page]=(True,current)
        previous_generation=generation
    exact=[r for r in rows if r['previousPageKnown']]
    print(json.dumps({'scenario':args.scenario,'capturedMaps':len(rows),
                      'exactComparisons':len(exact),
                      'meanSavedBytes':sum(1472-r['proposedMapBytes'] for r in exact)/max(1,len(exact)),
                      'maxCurrentHighRange':max((r['highRangeBytes'] for r in rows),default=0),
                      'heavyCaptures':sorted(rows,key=lambda r:r['nonzeroTiles'],reverse=True)[:10]},indent=2))


if __name__=='__main__':main()
