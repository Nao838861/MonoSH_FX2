; 768種類の奥行き・優先度キーをbit集合で走査する安定ソート。
; 同じキーは入力の逆順で連結し、出力順を元の安定ソートと一致させる。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys
.importzp packet_work
.export sa1_key_buckets
.segment "COLORBSS"
bit_heads: .res 1536
bit_links: .res 128
bit_map: .res 96
bit_block: .res 2
bit_key: .res 2
bit_bits: .res 2
bit_value: .res 2
bit_next: .res 2
.segment "CODE"
sa1_key_buckets:
  rep #$30
  ldx #94
bit_reset:
  stz bit_map,x
  dex
  dex
  bpl bit_reset
  ldy #0
bit_validate:
  lda keys,y
  cmp #768
  jcs bit_fallback
  sta bit_key
  and #7
  tax
  sep #$20
  lda f:$7f0000+bit_masks,x
  sta bit_value
  rep #$20
  lda bit_key
  lsr
  lsr
  lsr
  tax
  sep #$20
  lda bit_map,x
  ora bit_value
  sta bit_map,x
  rep #$20
  lda bit_key
  asl
  tax
  stz bit_heads,x
  iny
  iny
  cpy packet_work+8
  bcc bit_validate
  ldy packet_work+8
  dey
  dey
bit_link:
  lda keys,y
  asl
  tax
  lda bit_heads,x
  sta bit_links,y
  tya
  inc
  inc
  sta bit_heads,x
  dey
  dey
  bpl bit_link
  stz bit_block
  stz packet_work+16
bit_scan:
  ldx bit_block
  lda bit_map,x
  and #255
  beq bit_scan_next
  sta bit_bits
  txa
  asl
  asl
  asl
  asl
  sta bit_key
bit_scan_key:
  lsr bit_bits
  bcc bit_key_next
  ldx bit_key
  lda bit_heads,x
bit_walk:
  dec
  dec
  tay
  lda bit_links,y
  sta bit_next
  lda order,y
  ldx packet_work+16
  sta keys,x
  inx
  inx
  stx packet_work+16
  lda bit_next
  bne bit_walk
bit_key_next:
  inc bit_key
  inc bit_key
  lda bit_bits
  bne bit_scan_key
bit_scan_next:
  inc bit_block
  lda bit_block
  cmp #96
  bcc bit_scan
  ldx #0
bit_copy:
  lda keys,x
  sta order,x
  inx
  inx
  cpx packet_work+8
  bcc bit_copy
  sec
  rts
bit_fallback:
  clc
  rts
bit_masks:
  .byte 1,2,4,8,16,32,64,128
