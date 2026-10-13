"""初回ROMのbank末尾のrun読出しと、修正版の同じ表の余白を確認する。"""
import hashlib,json,struct
from pathlib import Path
from build_sa1_game import BUILD
from sa1_left_hints import physical


def main():
    old=(BUILD/'reverse_tree_v1_build/MonoSHSA1_4bpp_game.sfc').read_bytes()
    fixed=(BUILD/'reverse_tree_v2_build/MonoSHSA1_4bpp_game.sfc').read_bytes()
    trace=json.loads((BUILD/'reversetree_v1_failure_trace_v3/diagnostic.jsonl').read_text().splitlines()[-1])
    dp={0x20+i*2:v for i,v in enumerate(trace['dp'])}
    pointer=dp[0xc8]+65536*(dp[0xca]&255)
    assert trace['event']=='invalid_read'and trace['field']==265
    assert pointer==0x95fffd and pointer+trace['state']['cart.coprocessor.cpu.y']==0x95ffff
    bad=physical(0x95fffd);examples=[]
    for asset in range(44):
        for width in range(32,256):
            a=struct.unpack_from('<H',old,0x7f0000+asset*512+width*2)[0]
            b=struct.unpack_from('<H',fixed,0x7f0000+asset*512+width*2)[0]
            if not a:continue
            for i in range(old[0x7f0000+a]):
                ea=0x7f0000+a+1+i*10;eb=0x7f0000+b+1+i*10;h=old[ea]
                if h<24:continue
                pa=physical(int.from_bytes(old[ea+7:ea+10],'little'));pb=physical(int.from_bytes(fixed[eb+7:eb+10],'little'))
                for phase in range(8):
                    data=physical(int.from_bytes(old[pa+phase*3:pa+phase*3+3],'little'))
                    end=data;remaining=(h+phase+7)//8
                    while remaining:
                        run=old[end+2];assert 0<run<=remaining
                        remaining-=run;end+=3
                    if not data<=bad<end:continue
                    new=physical(int.from_bytes(fixed[pb+phase*3:pb+phase*3+3],'little'))
                    assert old[data:end]==fixed[new:new+end-data]
                    assert fixed[new+end-data]==0
                    boundary=0x8000 if new<0x400000 else 0x10000
                    assert new//boundary==(new+end-data)//boundary
                    examples.append(dict(asset=asset,width=width,height=h,phase=phase,oldData=data,oldEnd=end,
                        fixedData=new,fixedGuardByte=new+end-data,logicalRunDataIdentical=True))
    assert examples and bad+3==0x2b0000
    result=dict(oldRomSha256=hashlib.sha256(old).hexdigest(),fixedRomSha256=hashlib.sha256(fixed).hexdigest(),
        oldRunPointer=0x95fffd,oldWordRead=0x95ffff,oldExtraHighByte=0x960000,oldRecordHex=old[bad:bad+3].hex(),
        examples=examples,sourceAndSavedRuntimeTraceAgree=True,gameIntegrated=False,performanceEvidence=False)
    result.update(traceField=trace['field'],traceClock=trace['state']['masterClock'],tracePc=trace['state']['cart.coprocessor.cpu.pc'])
    path=Path(__file__).resolve().parents[1]/'game/sa1/v001/results/20261013_reverse_tree'
    path.mkdir(parents=True,exist_ok=True);(path/'dirty_read_guard.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
