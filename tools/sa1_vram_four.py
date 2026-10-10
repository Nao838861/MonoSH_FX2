"""4面のCHRと表示直前に更新する共有マップ。画像を落とさず転送を先行する。"""
import json,struct


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def ppu_layout(ppu,build):
    packing=build/'native_near_packing.json'
    d=json.loads(packing.read_text())
    old_far=d['farChrAddresses'];far=list(range(0x8c00,0x9000,32))+list(range(0xbc00,0xc000,32))
    assert len(old_far)==len(far)==64
    remap=dict(zip(old_far,far))
    saved=[bytes(ppu[a:a+32]) for a in old_far]
    for address in (0xc600,0xce00):
        for i in range(64):
            value=struct.unpack_from('<H',ppu,address+i*2)[0]
            old=(value&1023)*32
            struct.pack_into('<H',ppu,address+i*2,(value&~1023)|((remap[old]-0x8000)//32))
    ppu[:0xc000]=bytes(0xc000)
    for a,data in zip(far,saved):ppu[a:a+32]=data
    ppu[0xc000:0xc600]=struct.pack('<H',0x2400)*768
    d['farChrAddresses']=far;d['farChrBase']=0x8000
    packing.write_text(json.dumps(d,indent=2)+'\n')
    (build/'vram_four_layout.json').write_text(json.dumps({
        'pages':[0,0x3000,0x6000,0x9000],'dynamicCapacity':351,
        'sharedMap':0xc000,'farChrBase':0x8000,'farChrAddresses':far},indent=2)+'\n')
    return ppu


def sparse_map(text):
    text=text.replace('$2480','$2400').replace('$2481','$2401')
    # 12KiB単位の奇数面は8KiB境界から4KiBずれるためtile番号へ128を足す。
    text=change(text,'  lda #.loword(sm_empty_map)\n', '''  lda $0188
  and #1
  beq :+
  lda #.loword(sm_empty_map_odd)
  bra :++
:
  lda #.loword(sm_empty_map)
:
''')
    for value in ('$2400','$2401'):
        text=change(text,'  lda #'+value+'\n','  lda $0188\n  and #1\n  .repeat 7\n    asl\n  .endrepeat\n  ora #'+value+'\n')
    text+='\nsm_empty_map_odd:\n.repeat 736\n  .word $2480\n.endrepeat\n'
    text+='\n.assert ^sm_empty_map=^sm_empty_map_odd,error,"map parity templates crossed banks"\n'
    return text


def direct(text):
    text=change(text,'  lda #2064\n','  lda #16\n')
    return change(text,'  cmp #8193\n','  cmp #5633\n')


def prefix(text):
    if 'pfHigh' in text:
        # collectはfour_map_collectより先なので旧末尾mapを除外する。
        # plan時にはmap除去済みのCHR記述子数をそのまま使う。
        return change(text,'  and #255\n  dec\n  sta pfHigh','  and #255\n  sta pfHigh')
    return change(text,'  lda pipe_records+2,x\n  sec\n  sbc #6\n','  lda pipe_records+2,x\n')


def pipeline(text,build,sa1):
    text='.import four_map_collect: far, four_map_flip: far\n'+text
    text=change(text,'p3Queue: .res 4','p3Queue: .res 6')
    text=change(text,'  lda #$2000\n  sta p3NextPage','  lda #$1800\n  sta p3NextPage')
    text=change(text,'  lda p3Count\n  cmp #2\n','  lda p3Count\n  cmp #3\n')
    text=change(text,'pipe_collect_adaptive:\n','  jsl four_map_collect\npipe_collect_adaptive:\n')
    # 共有マップの転送をflip費用に含める。転送済みの画像を3枚まで保持する。
    text=text.replace('sbc #3300','sbc #5300').replace('sbc #2200','sbc #4200').replace('sbc #2300','sbc #4300')
    # すべての記述子がCHRになるため、途中でCCを止めない。
    setup='''  lda pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne :+
  sep #$20
  lda #$95
  sta f:$002231
:
'''
    text=change(text,setup,'')
    after='''  sta pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne :+
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
:
  jmp pipe_descriptor'''
    text=change(text,after,'  sta pipe_records+4,x\n  jmp pipe_descriptor')
    begin=text.index('pipe_fast_groups_done:\n')
    end=text.index('  .else\npipe_fast_loop:',begin)
    text=text[:begin]+'''pipe_fast_groups_done:
  lda pfPartial
  jne pipe_fast_partial_done
'''+text[end:]
    text=change(text,'''pf_unroll_full:
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x
  sec
  sbc #6''','''pf_unroll_full:
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x''')
    begin=text.index('pipe_fast_partial_done:\n')
    end=text.index('  lda pipe_records+34,x\n',begin)
    text=text[:begin]+'''pipe_fast_partial_done:
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc pfDesc
  sta pipe_records+4,x
'''+text[end:]
    text=change(text,'  sta fx4_page\n  txa\n','  sta fx4_page\n  jsl four_map_flip\n  txa\n')
    old='''  lda fx4_page+1
  .repeat 4
    lsr
  .endrepeat'''
    new='''  lda fx4_page+1
  .repeat 4
    lsr
  .endrepeat
  ora #$40'''
    text=change(text,old,new)
    text=change(text,'  lda fx4_page+1\n  ora #4\n  sta f:$002107','  lda #$60\n  sta f:$002107')
    ring=(sa1/'vram_prefetch_cpu.inc').read_text(encoding='utf-8')
    for name in ('p3Tail','p3Head'):
        ring=change(ring,'  lda '+name+'\n  eor #1\n  sta '+name,
                    '  lda '+name+'\n  inc\n  cmp #3\n  bcc :+\n  lda #0\n:\n  sta '+name)
    ring=change(ring,'  adc #$2000\n','  adc #$1800\n')
    (build/'vram_four_cpu.inc').write_text(ring,encoding='utf-8')
    return change(text,'.include "vram_prefetch_cpu.inc"','.include "vram_four_cpu.inc"')
