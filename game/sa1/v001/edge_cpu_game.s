; PPUが変換DMAを使用している間だけ、端の退避・復元をMVNで代行する。
; 退避先0300..06ffはCC buffer02e0と重ならない。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_edge_cpu_save: far, sa1_edge_cpu_restore: far
.segment "BOOT"
sa1_edge_cpu_save:
  rep #$30
  phb
  sep #$20
  lda #$54
  sta $07ec
  stz $07ed
  lda $0102
  sta $07ee
  lda #$6b
  sta $07ef
  rep #$30
edge_cpu_save_line:
  ldx $cc
  ldy $d8
  lda $c4
  dec
  jsl $0007ec
  jsr edge_cpu_next
  bne edge_cpu_save_line
  plb
  rtl
sa1_edge_cpu_restore:
  rep #$30
  phb
  sep #$20
  lda #$54
  sta $07ec
  lda $0102
  sta $07ed
  stz $07ee
  lda #$6b
  sta $07ef
  rep #$30
edge_cpu_restore_line:
  ldx $d8
  ldy $cc
  lda $c4
  dec
  jsl $0007ec
  ; MVNのDBRはBW-RAMなので、共有状態はbank0で更新する。
  sep #$20
  lda #0
  pha
  plb
  rep #$30
  jsr edge_cpu_next
  bne edge_cpu_restore_line
  plb
  rtl
edge_cpu_next:
  lda $d8
  clc
  adc $c4
  sta $d8
  lda $cc
  clc
  adc #128
  sta $cc
  dec $ce
  rts
