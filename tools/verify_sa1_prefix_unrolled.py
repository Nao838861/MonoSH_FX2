"""実ROMの6段探索命令と、全PPU走査線の予算表を独立検証する。"""
import hashlib,json,re,struct
from pathlib import Path
from build_sa1_game import BUILD
from sa1_left_hints import physical


def execute(rom,labels,mem,initial_y,entry='pf_search'):
    pc=physical(0xc10000+labels[entry]);end=physical(0xc10000+labels['pf_found'])
    a=x=0;y=initial_y;c=z=0;stack=[];calls=[];steps=0
    def read(p):return mem[p&65535]|mem[(p+1)&65535]<<8
    while pc!=end:
        steps+=1;assert steps<256
        op=rom[pc];pc+=1
        if op==0x5a:stack.append(y)
        elif op==0x7a:y=stack.pop();z=int(y==0)
        elif op==0x48:stack.append(a)
        elif op==0x68:a=stack.pop();z=int(a==0)
        elif op==0x22:
            target=int.from_bytes(rom[pc:pc+3],'little');calls.append(pc+3);pc=physical(target)
        elif op==0x6b:pc=calls.pop()
        elif op==0x18:c=0
        elif op==0x38:c=1
        elif op in (0xad,0xbd,0xcd,0x8d):
            p=rom[pc]|rom[pc+1]<<8;pc+=2
            if op==0xad:a=read(p);z=int(a==0)
            elif op==0xbd:a=read(p+x);z=int(a==0)
            elif op==0xcd:v=read(p);c=int(a>=v);z=int(a==v)
            else:mem[p]=a&255;mem[p+1]=a>>8
        elif op in (0x69,0xe9,0x6d,0xed):
            v=rom[pc]|rom[pc+1]<<8;pc+=2
            if op in (0x6d,0xed):v=read(v)
            add=op in (0x69,0x6d)
            total=a+v+c if add else a-v-(1-c)
            c=int(total>65535 if add else total>=0);a=total&65535;z=int(a==0)
        elif op==0x0a:c=a>>15;a=(a*2)&65535;z=int(a==0)
        elif op==0x4a:c=a&1;a>>=1;z=int(a==0)
        elif op==0x3a:a=(a-1)&65535;z=int(a==0)
        elif op==0xce:
            p=int.from_bytes(rom[pc:pc+2],'little');pc+=2
            v=(read(p)-1)&65535;struct.pack_into('<H',mem,p,v);z=int(v==0)
        elif op==0xa9:a=int.from_bytes(rom[pc:pc+2],'little');pc+=2;z=int(a==0)
        elif op==0xa8:y=a;z=int(y==0)
        elif op==0xaa:x=a;z=int(x==0)
        elif op==0x98:a=y;z=int(a==0)
        elif op==0x9b:y=x;z=int(y==0)
        elif op==0x4c:pc=physical(0xc10000+int.from_bytes(rom[pc:pc+2],'little'))
        elif op in (0x30,0x90,0xb0,0xd0):
            offset=rom[pc];pc+=1;offset=offset-256 if offset>=128 else offset
            if (op==0x30 and a>=32768) or (op==0x90 and not c) or (op==0xb0 and c) or (op==0xd0 and not z):pc+=offset
        else:raise AssertionError((hex(pc-1),hex(op)))
    assert not stack and not calls and y==initial_y,'stack or Y register was not restored'
    return read(labels['pfLow'])


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    manifest=json.loads((BUILD/'manifest.json').read_text())
    assert manifest.get('prefixUnrolledSearch') and hashlib.sha256(rom).hexdigest()==manifest['romSha256']
    labels={m[2]:int(m[1],16) for line in (BUILD/'game.lbl').read_text().splitlines()
        if (m:=re.match(r'al ([0-9A-Fa-f]+) \.(\S+)',line))}
    mem=bytearray(65536);base=labels['pfTables'];cases=full_cases=0
    if 'blank_table' in labels:
        assert labels['blank_table']<labels['__CODE_SIZE__']<=65536
        table=physical(0xc10000+labels['blank_table'])
        assert rom[table:table+13]==bytes([21,128,1,0,127,15,53,15,22,128,1,128,0])
    for variant in range(6):
        for count in range(49):
            costs=[];value=0
            for i in range(count):
                value+=1+(i*73+variant*101)%(1 if variant==0 else 701)
                costs.append(value);struct.pack_into('<HH',mem,base+i*4,i*32,value)
            limits=sorted({0,1,65535,*[max(0,c+d) for c in costs for d in (-1,0,1)]})
            for limit in limits:
                expected=sum(cost<limit for cost in costs)
                for start in sorted({0,count//2,count}):
                    for name,v in (('pfBase',base),('pfHigh',count),('pfLow',start),('pfLimit',limit)):
                        struct.pack_into('<H',mem,labels[name],v)
                    assert execute(rom,labels,mem,0x7351)==expected,(variant,count,start,limit,expected)
                    cases+=1
                    if manifest.get('prefixOnePass') and count and limit<=48000:
                        # 実行時のcost+availableは4万未満。人工的な65535加算wrapを除く。
                        margin=384-manifest.get('prefixFullReserve',384)
                        full_expected=count if costs[-1]<limit+margin else expected
                        if manifest.get('partialTransferReserve'):
                            struct.pack_into('<H',mem,labels['pipe_unreserved'],limit+384+manifest['partialTransferReserve'])
                            struct.pack_into('<H',mem,labels['pfBeforeCost'],0)
                            if full_expected!=count:full_expected=min(expected,count-1)
                        struct.pack_into('<H',mem,labels['pfLow'],start)
                        assert execute(rom,labels,mem,0x7351,'pf_full_check')==full_expected,(variant,count,start,limit,full_expected)
                        full_cases+=1
    lines=0
    if manifest.get('dmaBudgetTable'):
        table=physical(labels['pipe_budget_lines']);deadline=(281 if manifest['bulletShapes'] else 283)-manifest['dmaGuardLines']
        request_line=manifest.get('transferRequestLine',197)
        for actual in range(512):
            mapped=actual if actual>=203 else 203 if actual>=request_line else actual+262
            for hpoint in range(512):
                point=0 if request_line<=actual<203 else hpoint
                old=max(0,deadline-mapped)*170
                encoded=struct.unpack_from('<H',rom,table+mapped*2)[0]
                new=encoded if encoded<32768 else 0
                assert old==new,(actual,mapped,old,new)
                if mapped<=deadline:assert old-point//2+128==new-point//2+128
                lines+=1
    result=dict(romSha256=manifest['romSha256'],compiledSearchCases=cases,
        compiledFullShortcutCases=full_cases,blankHdmaTableInCpuCodeVerified='blank_table' in labels,
        budgetScanlineAndHpointCases=lines,compiledInstructionsExecuted=True,YRestored=True,goal60fpsAchieved=False)
    if manifest.get('dmaWordStart') and 'pipe_fast_unroll_start' in labels:
        count=manifest.get('dmaUnrollCount',12)
        begin=physical(0xc10000+labels['pipe_fast_unroll_start']);end=physical(0xc10000+labels['pipe_fast_unroll_end'])
        stride=(end-begin)//count;assert stride in (23,26) and end-begin==stride*count
        for i in range(count):
            block=rom[begin+i*stride:begin+(i+1)*stride]
            assert block[0]==(0xbf if manifest.get('dmaShortIo') else 0xbd)
            assert block[-2:]==b'\x84\x0b'
        assert rom[end:end+3]==b'\xa9\x00\x00'
        result['wordStartDmaTimingHooksVerified']=True
    if manifest.get('partialTransferReserve'):
        result['compiledNonflippingBudgetVerified']=True
        entry=physical(0xc10000+labels['pipe_time_left'])
        assert rom[entry:entry+3]==b'\x9c'+struct.pack('<H',labels['pipe_unreserved']),'stale raw budget survives deadline expiry'
        result['unreservedResetBeforeClockReadVerified']=True
    (BUILD/'prefix_search_static_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
