"""同一packetを二つの256px面へ描き、中央128pxずつを直接CC1へ渡す。"""


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def renderer(text):
    text='.setcpu "65816"\n.import sa1_split_clear: far\n'+text
    a=text.index('  jsl sa1_stack_clear_prepare\n',text.index('sa1_dirty_done:'))
    b=text.index('  .endif\nsa1_clear_done:',a)
    text=text[:a]+'  jsl sa1_split_clear\n'+text[b:]
    text=change(text,'sa1_draw_start:\n','split_packet_ready:\n')
    text=change(text,'sa1_clear_done:\n  jsl background\n  stz index',
        'sa1_clear_done:\n  jsl background\n  stz $01b0\nsa1_draw_start:\n  rep #$30\nsplit_reset_packet:\n  stz index')
    text=change(text,'  sbc tmp\n  sta left\n  cmp #$8000', '''  sbc tmp
  sta left
  lda $01b0
  bne split_right_sprite
  lda left
  sec
  sbc #128
  jpl skip
  lda left
  clc
  adc width
  jmi skip
  jeq skip
  lda left
  clc
  adc #64
  bra split_sprite_shifted
split_right_sprite:
  lda left
  sec
  sbc #256
  jpl skip
  lda left
  clc
  adc width
  sec
  sbc #128
  jmi skip
  jeq skip
  lda left
  sec
  sbc #64
split_sprite_shifted:
  sta left
  cmp #$8000''')
    text=change(text,'finished:\nsa1_native_done:', '''finished:
  lda $01b0
  bne split_both_done
  inc $01b0
  lda #$8400
  sta $019a
  sta $10
  jmp split_reset_packet
split_both_done:
  lda #$0400
  sta $019a
  sta $10
sa1_native_done:''')
    return text


def pipeline(text):
    return change(text,'  .ifdef SA1_DEEP_BW\n  cmp #14\n','  .ifdef SA1_DEEP_BW\n  cmp #6\n')


def occupancy(text):
    assert text.count('cmp #7')==2 and text.count('sbc #7')==1
    return text.replace('cmp #7','cmp #3').replace('sbc #7','sbc #3').replace('adc #5\n  cmp #3','adc #1\n  cmp #3')


def idle(text):
    text=change(text,'  lda #7\n  sta icRemaining','  lda #3\n  sta icRemaining')
    text=change(text,'  cmp #14\n','  cmp #6\n')
    text=change(text,'ic_nonempty:\n  jsl sa1_dma_try_begin','ic_nonempty:\n  sta $ae\n  jsl sa1_dma_try_begin')
    a=text.index('  lda #$f000\n',text.index('idle_clear_dma:'))
    b=text.index('  lda #0\n  sta [icHistory],y\n',a)
    text=text[:a]+'''  lda $ae
  cmp #64
  bcs split_idle_right
  lda #$f000
  sta $2232
  lda #1024
  sta $2238
  lda icDest
  sta $2235
  sep #$20
  lda icBank
  sta $2237
  rep #$20
split_idle_right:
  lda [icHistory],y
  cmp #65
  bcc split_idle_empty
  lda #$f000
  sta $2232
  lda #1024
  sta $2238
  lda icDest
  clc
  adc #$8000
  sta $2235
  sep #$20
  lda icBank
  sta $2237
  rep #$20
split_idle_empty:
'''+text[b:]
    return text


def transfer_mask(text):
    # 一つのdescriptorが左右・band境界を跨がないようにする。
    # mask byteのrunは最大256Bなので、mergeだけ止めれば各runはhalf内に収まる。
    return change(text,'  lda tmCount\n  beq tm_new\n  lda tmStart\n', '''  lda tmCount
  beq tm_new
  lda tmEnd
  dec
  eor tmStart
  and #$fe00
  bne tm_new
  lda tmStart
''')


REBASE='''.setcpu "65816"
.smart
.export sa1_deep_rebase: far
.segment "BOOT"
sa1_deep_rebase:
  rep #$30
  lda $011a
  beq split_rebase_done
  sta $f0
  ldx #0
split_rebase_loop:
  lda f:$430802,x
  sta $f2
  and #$fc00
  sta $f4
  lda $f2
  and #$01ff
  clc
  adc $f4
  adc #$0500
  sta $f4
  lda $f2
  and #$0200
  beq :+
  lda #$8000
:
  clc
  adc $f4
  sta f:$430802,x
  txa
  clc
  adc #6
  tax
  dec $f0
  bne split_rebase_loop
split_rebase_done:
  rtl
'''


def near_patch(text):
    a=text.index('sa1_near_patch:\n')
    return text[:a]+'''sa1_near_patch:
  rep #$30
  lda $010c
  clc
  adc #82
  cmp #192
  bcs patch_done
  .repeat 7
    asl
  .endrepeat
  clc
  adc #$0400
  sta $01b8
  jsr patch_geometry
  lda $d0
  sta $01b4
  lda $d2
  sta $01b6
  lda $010a
  and #$1fc
  sta $e8
  stz $e4
patch_row:
  ; source用のglobal xを保ち、destinationだけ左+32B・右-32Bへ写す。
  lda $01b4
  sta $d0
  lda #64
  sta $d2
  lda $01b8
  clc
  adc #32
  sta $e6
  jsl sa1_near_row
  lda #64
  sta $d0
  lda $01b6
  sta $d2
  lda $01b8
  clc
  adc #$8000-32
  sta $e6
  jsl sa1_near_row
  lda $01b8
  clc
  adc #128
  sta $01b8
  cmp #$0400+192*128
  bcs patch_done
  inc $e4
  lda $e4
  cmp #9
  bcc patch_row
patch_done:
  rtl
'''


def packed_near_data(raw):
    import numpy as np
    source=np.frombuffer(raw[0x8000:0x8000+9*512],np.uint8).reshape(9,512)
    data=bytearray()
    for phase in range(2):
        for row in source:
            pixels=row[(np.arange(1024)+phase)&511]
            data.extend(bytes(pixels[::2]|pixels[1::2]<<4))
    assert len(data)==9216
    # 全512scroll・9行・左右について、透明0を含めて元の画素と同じ。
    for scroll in range(512):
        left=((112-(scroll&7))&~3)//2;right=((163-(scroll&7))&~3)//2
        for y,row in enumerate(source):
            for lo,hi in ((left,64),(64,right)):
                start=(scroll&1)*4608+y*512+((scroll//2+lo)&255)
                part=np.frombuffer(data[start:start+hi-lo],np.uint8)
                pixels=np.empty(len(part)*2,np.uint8);pixels[::2]=part&15;pixels[1::2]=part>>4
                assert np.array_equal(pixels,row[(np.arange(lo*2,hi*2)+scroll)&511])
    return data


def near_packed(text,split=True):
    a=text.index('sa1_near_patch:\n')
    text=text[:a]+'''sa1_near_patch:
  rep #$30
  lda $010c
  clc
  adc #82
  cmp #192
  jcs patch_done
  .repeat 7
    asl
  .endrepeat
  clc
  adc #$0400
  sta $e2
  jsr patch_geometry
  lda $d0
  sta $ea
  lda $d2
  sta $ec
  lda $010a
  and #1
  beq :+
  lda #4608
:
  sta $e0
  stz $e4
  ; MVN destination bankだけを設定する。0700..0703はnear専用の一時worker。
  lda $0102
  and #255
  xba
  ora #$54
  sta $0700
  lda #$6bfe
  sta $0702
patch_row:
  lda $010a
  lsr
  clc
  adc $ea
  and #255
  clc
  adc $e0
  tax
  lda $e2
  clc
  adc #32
  adc $ea
  tay
  lda #63
  sec
  sbc $ea
  phb
  jsl $000700
  plb
  lda $010a
  lsr
  clc
  adc #64
  and #255
  clc
  adc $e0
  tax
  lda $e2
  clc
  adc #$8000+32
  tay
  lda $ec
  sec
  sbc #65
  phb
  jsl $000700
  plb
  lda $e0
  clc
  adc #512
  sta $e0
  lda $e2
  clc
  adc #128
  sta $e2
  cmp #$0400+192*128
  bcs patch_done
  inc $e4
  lda $e4
  cmp #9
  jcc patch_row
patch_done:
  rtl
'''
    if not split:
        text=change(text,'  adc #$0400\n  sta $e2','  adc $019a\n  sta $e2')
        text=change(text,'  adc #32\n  adc $ea\n','  adc $ea\n')
        text=change(text,'  lda #63\n  sec\n  sbc $ea','  lda $ec\n  sec\n  sbc $ea\n  dec')
        start=text.index('  lda $010a\n  lsr\n',text.index('  jsl $000700\n'))
        end=text.index('  lda $e0\n  clc\n  adc #512\n',start)
        text=text[:start]+text[end:]
        text=change(text,'  cmp #$0400+192*128\n','  sec\n  sbc $019a\n  cmp #192*128\n')
    return text
