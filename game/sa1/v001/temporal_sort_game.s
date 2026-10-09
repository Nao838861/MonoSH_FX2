; 前画像の順序を初期値にする。現在の元indexを同一キーの比較に使い安定順を保つ。
.setcpu "65816"
.smart
.import order, keys, fx_is_obj
.importzp packet_work
.export sa1_temporal_prepare, sa1_temporal_save
.segment "COLORBSS"
temporal_keys: .res 640
temporal_order: .res 128
temporal_count: .res 2
.segment "CODE"
sa1_temporal_prepare:
  rep #$30
  lda packet_work+8
  cmp #24
  bcc temporal_return
  cmp temporal_count
  bne temporal_return
  ldy #0
temporal_map:
  lda order,y
  tax
  lda keys,y
  sta temporal_keys,x
  iny
  iny
  cpy packet_work+8
  bcc temporal_map
  ldy #0
temporal_validate:
  lda temporal_order,y
  tax
  cpx packet_work+2
  bcs temporal_return
  jsr fx_is_obj
  bne temporal_return
  iny
  iny
  cpy packet_work+8
  bcc temporal_validate
  ldy #0
temporal_reuse:
  lda temporal_order,y
  sta order,y
  tax
  lda temporal_keys,x
  sta keys,y
  iny
  iny
  cpy packet_work+8
  bcc temporal_reuse
temporal_return:
  rts
sa1_temporal_save:
  rep #$30
  lda packet_work+8
  sta temporal_count
  cmp #24
  bcc temporal_return
  ldx #0
temporal_save_loop:
  lda order,x
  sta temporal_order,x
  inx
  inx
  cpx temporal_count
  bcc temporal_save_loop
  rts
