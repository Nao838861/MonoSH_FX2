"""マップのlow/highを分け、高byteの変更範囲だけを送る試作。"""


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def source(text, mvn=False):
    text=change(text,'smPointer=$ac\n','''smPointer=$ac
smHigh=$b0
smMeta=$b4
smFirst=$b8
smLast=$ba
''')
    text=change(text,'  sta smPointer\n  jsl sa1_dma_try_begin','''  sta smPointer
  clc
  adc #736
  sta smHigh
  lda smBank
  sta smHigh+2
  sta smMeta+2
  lda $019a
  clc
  adc #$66c0
  sta smMeta
  lda #736
  sta smFirst
  stz smLast
  jsl sa1_dma_try_begin''')
    start=text.index('sm_fill_cpu:\n');end=text.index('sm_map_ready:\n',start)
    text=text[:start]+'''sm_fill_cpu:
  ldy #0
  lda #$8080
sm_fill_word:
  sta [smPointer],y
  pha
  lda #$2424
  sta [smHigh],y
  pla
  iny
  iny
  cpy #736
  bcc sm_fill_word
'''+text[end:]
    text=change(text,'  sbc #64\n  tay\n  lda smTile\nsm_tile:', '''  sbc #64
  lsr
  tay
  lda smTile
  clc
  adc smCount
  cmp #$2501
  bcc sm_bounds_done
  tya
  clc
  adc smCount
  cmp smLast
  bcc :+
  sta smLast
:
  lda smTile
  cmp #$2500
  bcs sm_high_first
  lda #$2500
  sec
  sbc smTile
  sta smEndHigh
  tya
  clc
  adc smEndHigh
  bra sm_high_start
sm_high_first:
  tya
sm_high_start:
  cmp smFirst
  bcs sm_bounds_done
  sta smFirst
sm_bounds_done:
  lda smTile
sm_tile:''')
    text=change(text,'smLast=$ba\n','smLast=$ba\nsmEndHigh=$bc\n')
    text=change(text,'  sta [smPointer],y\n  inc\n  iny\n  iny\n  dec smCount', '''  sep #$20
  sta [smPointer],y
  xba
  sta [smHigh],y
  xba
  rep #$20
  inc
  iny
  dec smCount''')
    text=change(text,'sm_done:\n  rtl','''sm_done:
  ldy #0
  lda smFirst
  sta [smMeta],y
  iny
  iny
  lda smLast
  sta [smMeta],y
  rtl''')
    text=change(text,'.repeat 736\n  .word $2480\n.endrepeat', '''.repeat 736
  .byte $80
.endrepeat
.repeat 736
  .byte $24
.endrepeat''')
    if mvn:
        text=change(text,'  bcs sm_done\n','  jcs sm_done\n')
        text=change(text,'  bra sm_descriptor\n','  jmp sm_descriptor\n')
        text=change(text,'smEndHigh=$bc\n','smEndHigh=$bc\nsmThisHigh=$be\nsmHighCount=$c0\n')
        text=change(text,'sm_map_ready:\n', '''sm_map_ready:
  sep #$20
  lda #$54
  sta $07ec
  lda smBank
  sta $07ed
  lda #^sm_low_table
  sta $07ee
  lda #$6b
  sta $07ef
  rep #$30
''')
        text=change(text,'  lda smTile\n  clc\n  adc smCount\n  cmp #$2501', '  stz smHighCount\n  lda smTile\n  clc\n  adc smCount\n  cmp #$2501')
        text=change(text,'sm_high_start:\n  cmp smFirst', '''sm_high_start:
  sta smThisHigh
  tya
  clc
  adc smCount
  sec
  sbc smThisHigh
  sta smHighCount
  lda smThisHigh
  cmp smFirst''')
        begin=text.index('sm_bounds_done:\n')
        end=text.index('  sta smTile\n',begin)+len('  sta smTile\n')
        text=text[:begin]+'''sm_bounds_done:
  tya
  clc
  adc smMap
  tay
  lda smTile
  sec
  sbc #$2481
  clc
  adc #.loword(sm_low_table)
  tax
  lda smCount
  dec
  phb
  jsl $0007ec
  plb
  lda smHighCount
  beq sm_mvn_done
  dec
  pha
  lda smThisHigh
  clc
  adc smHigh
  tay
  ldx #.loword(sm_high_table)
  pla
  phb
  jsl $0007ec
  plb
sm_mvn_done:
  lda smTile
  clc
  adc smCount
  sta smTile
'''+text[end:]
        text+='''
sm_low_table:
.repeat 383, I
  .byte <(129+I)
.endrepeat
sm_high_table:
.repeat 736
  .byte $25
.endrepeat
'''
    return text


def pipeline(text):
    text='.setcpu "65816"\n.import split_map_collect: far, split_map_prepare: far, split_map_transfer: far, split_map_try: far\n'+text
    text=change(text,'pipe_collect_adaptive:\n','  jsl split_map_collect\npipe_collect_adaptive:\n')
    text=change(text,'pipe_setup_transfer:\n  lda pipe_target_slot', 'pipe_setup_transfer:\n  lda pipe_target_slot')
    start=text.index('pipe_setup_transfer:\n')
    pos=text.index('  tax\n',start)+len('  tax\n')
    text=text[:pos]+'  jsl split_map_prepare\n'+text[pos:]
    old='''  jsr pipe_time_left
  lda pipe_records+208,x'''
    new='''  jsr pipe_time_left
  phx
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne split_map_chr_descriptor
  plx
  jsl split_map_try
  jcc pipe_transfer_pause
  jmp pipe_transfer_complete
split_map_chr_descriptor:
  plx
  lda pipe_records+208,x'''
    text=change(text,old,new)
    start=text.index('pipe_fast_groups_done:\n')
    begin=text.index('  sep #$20\n  lda #$95\n',start)
    end=text.index('  .else\npipe_fast_loop:',begin)
    text=text[:begin]+'  jsl split_map_transfer\n  rep #$30\n'+text[end:]
    text=change(text,'  lda pipe_dma_chunk\n  cmp pipe_available\n  bcc pf_full_frame', '  lda pipe_dma_chunk\n  clc\n  adc #384\n  cmp pipe_available\n  bcc pf_full_frame')
    return text
