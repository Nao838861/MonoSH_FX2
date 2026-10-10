"""16KiBずつのVRAM三面で、完成画像と次画像の部分転送を保持する。"""
import json,struct


def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def ppu_layout(ppu,build):
    # BG2が使う二枚目の固定CHRだけを6000から4000へ移す。
    ppu[0x4000:0x4400]=ppu[0x6000:0x6400]
    for address in (0xc600,0xce00):
        for i in range(64):
            value=struct.unpack_from('<H',ppu,address+i*2)[0]
            tile=value&1023
            if 768<=tile<800:struct.pack_into('<H',ppu,address+i*2,(value&~1023)|(tile-256))
    packing=build/'native_near_packing.json';d=json.loads(packing.read_text())
    d['farChrAddresses']=[x-0x2000 if 0x6000<=x<0x6400 else x for x in d['farChrAddresses']]
    packing.write_text(json.dumps(d,indent=2)+'\n')
    for page in (0,0x4000,0x8000):
        ppu[page+0x800:page+0x1000]=struct.pack('<H',0x2480)*1024
        ppu[page+0x1000:page+0x1020]=bytes(32)
    return ppu


def dense(text):
    text=replace(text,'  lda #32\n  sta dOut\n  sta dTile','  lda #32\n  sta dOut\n  lda #128\n  sta dTile')
    text=text.replace('.word $2420','.word $2480').replace('adc #$6020','adc #$0420')
    text=replace(text,'  lda #512\n  sta f:$430804','  lda #2048\n  sta f:$430804')
    # 三面は三世代前のmapを持つ。直前世代のband履歴では消し残しになる。
    text=replace(text,'  ora dCurrent\n  sta dSend','  ora dCurrent\n  lda #1\n  sta dSend')
    text=replace(text,'  inc\n  sta dTile\n  ora #$2400','  inc\n  cmp #512\n  jcs dense_vram_overflow\n  sta dTile\n  ora #$2400')
    text+='\n.segment "GSU"\n.export dense_vram_overflow: far\ndense_vram_overflow:\n  stp\n'
    return text


def sparse_map(text):
    return text.replace('$2420','$2480').replace('$2421','$2481')


def cpu_stage(text,pump=False):
    text=text.replace('cmp #$34e1','cmp #12257')
    text=replace(text,'  lda #512\n  sta pipe_records+212,x','  lda #2048\n  sta pipe_records+212,x')
    text=replace(text,'  lda #$6020\n  sta pipe_records+218,x','  lda #$0420\n  sta pipe_records+218,x')
    if pump:text=replace(text,'  sta stage_read_slot\npipe_stage_done:','  sta stage_read_slot\n  jsr p3Pump\npipe_stage_done:')
    return text


def pipeline(text,pump=False,defer=False,late_flip=False):
    # 完了queueの操作とmapレジスタ更新も含めたflip費用を残す。
    text=text.replace('sbc #1300','sbc #2200').replace('sbc #1700','sbc #2200')
    text=text.replace('sbc #2400','sbc #3300').replace('sbc #2800','sbc #3300')
    text=text.replace('sbc #700','sbc #900')
    # 残量の切り下げが0Bになった場合、65536B DMAとして発火させない。
    assert '  jeq pipe_transfer_pause\n  bra pipe_set_chunk' in text
    text=replace(text,'pipe_records: .res 512*SA1_PIPELINE_DEPTH','pipe_records: .res 512*SA1_PIPELINE_DEPTH\np3Queue: .res 4\np3Head: .res 2\np3Tail: .res 2\np3Count: .res 2\np3NextPage: .res 2')
    text=replace(text,'  inc pipe_initialized\n','  inc pipe_initialized\n  stz p3Head\n  stz p3Tail\n  stz p3Count\n  lda #$2000\n  sta p3NextPage\n')
    text=replace(text,'  lda pipe_complete\n  beq pipe_choose_target\n  jsr pipe_flip','  lda p3Count\n  beq pipe_choose_target\n  jsr p3Flip')
    text=replace(text,'  .ifdef SA1_FRONT_MASK\n  lda pipe_presented_irq\n  jne pipe_irq_done\n  .endif','  lda p3Count\n  cmp #2\n  jcs pipe_irq_done')
    text=replace(text,'  lda fx4_page\n  eor #$3000\n  .ifndef SA1_FRONT_MASK','  lda p3NextPage\n  .ifndef SA1_FRONT_MASK')
    text=replace(text,'  sta pipe_fast_page\n  lda pipe_records+4,x\n  beq :+\n  stz pipe_fast_page\n:\n','  sta pipe_fast_page\n')
    start=text.index('pipe_descriptor:\n');end=text.index('dense_descriptor_ready:\n',start)
    text=text[:start]+'pipe_descriptor:\n'+text[end:]
    old='  lda pipe_records+212,x\n  ldx pipe_record_offset\n  pha\n  lda pipe_records+4,x\n  bne :+\n  pla\n  clc\n  adc pipe_records+6,x\n  bra :++\n:\n  pla\n:\n'
    text=replace(text,old,'  lda pipe_records+212,x\n  ldx pipe_record_offset\n  clc\n  adc pipe_records+6,x\n')
    text=replace(text,'  cpx pipe_desc_offset\n  bne :+\n  clc\n  adc pipe_fast_page\n:\n','  clc\n  adc pipe_fast_page\n')
    start=text.index('  lda #1\n  sta pipe_complete\nprefetch_finished:');end=text.index('pipe_transfer_pause:',start)
    text=text[:start]+'''  jsr p3Complete
prefetch_finished:
  lda pipe_presented_irq
  bne p3_keep_prefetching
  jsr p3Flip
p3_keep_prefetching:
  jmp pipe_choose_target
'''+text[end:]
    # 読み取りcursorは転送完了時に進める。表示cursorは完成queueが持つ。
    old='  lda pipe_read_slot\n  inc\n  cmp #SA1_PIPELINE_DEPTH\n  bcc :+\n  lda #0\n:\n  sta pipe_read_slot\ndma_finished:'
    text=replace(text,old,'dma_finished:')
    # BG1のCHRとmapを同時に世代対応させる。
    text=replace(text,'  sta f:$00210b\n  rep #$30','  sta f:$00210b\n  lda fx4_page+1\n  ora #4\n  sta f:$002107\n  rep #$30')
    if pump:
        text=replace(text,'p3NextPage: .res 2','p3NextPage: .res 2\np3Manual: .res 2')
        text=replace(text,'  stz p3Head\n','  stz p3Manual\n  stz p3Head\n')
        text=replace(text,'  stz pipe_presented_irq\n  lda #3000','  lda p3Manual\n  sta pipe_presented_irq\n  lda #3000')
        text=replace(text,'  lda p3Count\n  beq pipe_choose_target\n  jsr p3Flip','  lda p3Manual\n  bne pipe_choose_target\n  lda p3Count\n  beq pipe_choose_target\n  jsr p3Flip')
        text=replace(text,'pipe_irq_exit:\n  rep #$30\n','pipe_irq_exit:\n  rep #$30\n  lda p3Manual\n  beq p3RealIrqExit\n  stz p3Manual\n  plb\n  pld\n  ply\n  plx\n  pla\n  plp\n  rts\np3RealIrqExit:\n')
    if defer:
        text=replace(text,'  .ifdef SA1_STAGED\n  jsl $c10000+pipe_stage_convert\n  .endif\n  plb','  plb')
        text=replace(text,'  sep #$30\n  jsr _fx_frame','  php\n  sei\n  jsl $c10000+pipe_stage_convert\n  plp\n  sep #$30\n  jsr _fx_frame')
        text=replace(text,'pipe_slot_sleep:\n','pipe_slot_sleep:\n  lda stage_read_slot\n  pha\n  jsl $c10000+pipe_stage_convert\n  pla\n  cmp stage_read_slot\n  jne pipe_wait_bw\n')
        text=replace(text,'  lda pipe_status,x\n  beq pipe_ground_free','  lda pipe_status,x\n  beq pipe_ground_free\n  phx\n  jsl $c10000+pipe_stage_convert\n  plx\n  lda pipe_status,x\n  beq pipe_ground_free')
    if late_flip:
        text=replace(text,'p3Manual: .res 2','p3Manual: .res 2\np3Serial: .res 2\np3LastFlip: .res 2')
        text=replace(text,'  stz p3Manual\n  stz p3Head','  stz p3Manual\n  stz p3Serial\n  lda #$ffff\n  sta p3LastFlip\n  stz p3Head')
        text=replace(text,'  lda p3Manual\n  sta pipe_presented_irq\n  lda #3000','''  lda p3Manual
  beq p3NewField
  lda p3Serial
  cmp p3LastFlip
  beq p3AlreadyPresented
  stz pipe_presented_irq
  bra p3FieldReady
p3AlreadyPresented:
  lda #1
  sta pipe_presented_irq
  bra p3FieldReady
p3NewField:
  inc p3Serial
  stz pipe_presented_irq
p3FieldReady:
  lda #3000''')
        text=replace(text,'  lda p3Manual\n  bne pipe_choose_target\n  lda p3Count\n  beq pipe_choose_target\n  jsr p3Flip','''  lda pipe_presented_irq
  bne pipe_choose_target
  lda p3Count
  beq pipe_choose_target
  jsr pipe_time_left
  lda pipe_available
  beq pipe_choose_target
  jsr p3Flip''')
    text+='\n.segment "CODE"\n.include "vram_prefetch_cpu.inc"\n'
    return text
