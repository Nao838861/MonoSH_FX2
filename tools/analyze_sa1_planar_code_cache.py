"""画面タイルでなく、位置に依存しないplanar行コードのRAM再利用を試算する。"""
import argparse,json,struct
from collections import OrderedDict
from functools import lru_cache
import numpy as np
from build_sa1_probe import assets,ROOT
from sa1_planar_feasibility import kernel
from report_sa1_compact_game import packets


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scenario',default='movestress_detinput_captureburst_fixedtable_v1_tracepalette');args=ap.parse_args()
    variants=assets();trace=packets(args.scenario);capacities=[32768,65536,98304,131072]
    caches={n:OrderedDict() for n in capacities};used={n:0 for n in capacities};result=[]
    @lru_cache(maxsize=None)
    def compiled(asset,hue,width,sy,flip,first,last,phase):
        source=variants.get((asset,hue),variants[asset,0])[1];ah,aw=source.shape
        xs=np.arange(width)*(aw*256//width)
        if flip:xs=aw*256-1-xs
        row=source[sy,xs>>8][first:last]
        return kernel(row,phase)
    for gen,packet in enumerate(trace,1):
        requests=[]
        for center,bottom,w,h,asset,flags,*_ in struct.iter_unpack('<hh6B',packet[8:]):
            if not w or not h:continue
            left=center-w//2;top=bottom-h-20;x0=max(0,left);x1=min(256,left+w)
            if x0>=x1:continue
            source=variants.get((asset,flags&3),variants[asset,0])[1];ah=source.shape[0]
            ys=np.arange(h)*(ah*256//h)
            if flags&32:ys=ah*256-1-ys
            for dy,sy in enumerate(ys>>8):
                if not 0<=top+dy<192:continue
                requests.append(compiled(asset,flags&3,w,int(sy),bool(flags&16),x0-left,x1-left,x0&7))
        entry=dict(generation=gen,rowCalls=len(requests),caches={})
        for capacity in capacities:
            cache=caches[capacity];misses=0;new_bytes=0
            for code in requests:
                if code in cache:cache.move_to_end(code);continue
                misses+=1;size=len(code)+6;new_bytes+=size
                assert size<=capacity
                while used[capacity]+size>capacity:
                    _,old=cache.popitem(last=False);used[capacity]-=old
                cache[code]=size;used[capacity]+=size
            entry['caches'][str(capacity)]=dict(misses=misses,newCodeBytes=new_bytes)
        result.append(entry)
        if gen%100==0:print(gen,len(requests),flush=True)
    burst=[r for r in result if 530<=r['generation']<=570]
    totals={str(n):dict(rowCalls=sum(r['rowCalls'] for r in burst),
        misses=sum(r['caches'][str(n)]['misses'] for r in burst),
        newCodeBytes=sum(r['caches'][str(n)]['newCodeBytes'] for r in burst),
        maxNewCodeBytes=max(r['caches'][str(n)]['newCodeBytes'] for r in burst)) for n in capacities}
    output=dict(scenario=args.scenario,generations=len(result),burstTotals=totals,
                allocationHeadersBytes=6,includesCompilationTime=False,includesBwRamRepartition=False,
                frames=result)
    path=ROOT/'build/sa1_game/planar_code_cache.json';path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(totals),flush=True)


if __name__=='__main__':main()
