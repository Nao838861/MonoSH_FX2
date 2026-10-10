; 優先度0..2の全キーを一度で安定bucketソートする。
; 7F:F800..FDFFはCODE上限をassertして専用領域にする。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys, __CODE_SIZE__
.importzp packet_work
.export sa1_key_buckets
.assert __CODE_SIZE__ <= $f800, lderror, "code overlaps key bucket scratch"
.segment "COLORBSS"
key_links: .res 128
key_initialized: .res 2
key_minmax: .res 12
key_group: .res 2
.segment "CODE"
sa1_key_buckets:
  rep #$30
  lda key_initialized
  bne key_prepare
  inc key_initialized
  ldx #1534
  lda #0
key_initialize:
  sta f:$7ff800,x
  dex
  dex
  bpl key_initialize
key_prepare:
  ldx #8
key_reset_ranges:
  lda #$ffff
  sta key_minmax,x
  stz key_minmax+2,x
  dex
  dex
  dex
  dex
  bpl key_reset_ranges
  ldy #0
key_validate:
  lda keys,y
  cmp #768
  jcs key_fallback
  sta packet_work+12
  xba
  and #255
  asl
  asl
  tax
  lda packet_work+12
  cmp key_minmax,x
  bcs :+
  sta key_minmax,x
:
  cmp key_minmax+2,x
  bcc :+
  sta key_minmax+2,x
:
  asl
  tax
  lda #0
  sta f:$7ff800,x
  iny
  iny
  cpy packet_work+8
  bcc key_validate
  ldy packet_work+8
  dey
  dey
key_link:
  lda keys,y
  asl
  tax
  lda f:$7ff800,x
  sta key_links,y
  tya
  inc
  inc
  sta f:$7ff800,x
  dey
  dey
  bpl key_link
  stz packet_work+16
  stz key_group
key_choose_group:
  ldx key_group
  lda key_minmax+2,x
  cmp key_minmax,x
  bcc key_next_group
  inc
  asl
  sta packet_work+18
  lda key_minmax,x
  asl
  tax
key_scan:
  lda f:$7ff800,x
  beq key_scan_next
  pha
  lda #0
  sta f:$7ff800,x
  pla
key_walk:
  dec
  dec
  tay
  lda order,y
  phy
  ldy packet_work+16
  sta keys,y
  iny
  iny
  sty packet_work+16
  ply
  lda key_links,y
  bne key_walk
key_scan_next:
  inx
  inx
  cpx packet_work+18
  bcc key_scan
key_next_group:
  lda key_group
  clc
  adc #4
  sta key_group
  cmp #12
  bcc key_choose_group
  ldx #0
key_copy:
  lda keys,x
  sta order,x
  inx
  inx
  cpx packet_work+8
  bcc key_copy
  sec
  rts
key_fallback:
  clc
  rts
