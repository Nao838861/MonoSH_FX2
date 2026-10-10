; 変わった連続tileをDMA記述子へまとめ、ROMの自然番号列/透明列から送る。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_map_prepare: far, fd_show: far
.segment "GSU"
fdWord=$a0
fdMask=$a2
fdDiff=$a4
fdPos=$a6
fdOffset=$a8
fdCount=$aa
fdBits=$ac
fdMode=$ae
fdWant=$b0
fdCost=$b2
sa1_sparse_map_prepare:
  rep #$30
  lda $0116
  cmp #2
  bcs fd_init_done
  ldx #94
  lda #0
fd_init:
  sta f:$434600,x
  dex
  dex
  bpl fd_init
fd_init_done:
  stz fdCount
  stz fdOffset
  stz fdMode
  lda #300
  sta fdCost
  lda #32
  sta fdPos
  lda #4
  sta fdWord
fd_word:
  ldx fdWord
  lda f:$432800,x
  sta fdMask
  eor f:$434600,x
  sta fdDiff
  lda fdMask
  sta f:$434600,x
  lda fdDiff
  bne fd_bits
  stz fdMode
  lda fdPos
  clc
  adc #16
  sta fdPos
  jmp fd_next
fd_bits:
  lda #16
  sta fdBits
fd_bit:
  lsr fdMask
  bcc :+
  lda #1
  bra :++
:
  lda #2
:
  sta fdWant
  lsr fdDiff
  bcs fd_changed
  stz fdMode
  jmp fd_skip
fd_changed:
  lda fdWant
  cmp fdMode
  beq fd_extend
  sta fdMode
  inc fdCount
  lda fdCount
  cmp #49
  bcs fd_skip
  cmp #1
  beq :+
  lda fdOffset
  clc
  adc #6
  sta fdOffset
:
  ldx fdOffset
  lda #2
  sta f:$434000,x
  lda fdPos
  sec
  sbc #32
  asl
  clc
  adc #.loword(fd_show)
  ldy fdMode
  cpy #1
  beq :+
  clc
  adc #1472
:
  sta f:$434002,x
  lda fdPos
  clc
  adc #$5e00
  sta f:$434004,x
  lda fdCost
  clc
  adc #112
  sta fdCost
  bra fd_skip
fd_extend:
  lda fdCount
  cmp #49
  bcs fd_skip
  ldx fdOffset
  lda f:$434000,x
  inc
  inc
  sta f:$434000,x
  inc fdCost
  inc fdCost
fd_skip:
  inc fdPos
  dec fdBits
  jne fd_bit
fd_next:
  inc fdWord
  inc fdWord
  lda fdWord
  cmp #96
  jcc fd_word
  lda fdCount
  cmp #49
  bcs fd_full
  sta f:$434660
  lda fdCost
  sta f:$434662
  rtl
fd_full:
  lda #$ffff
  sta f:$434660
  lda #$2401
  sta fdPos
  lda #4
  sta fdWord
fd_full_word:
  ldx fdWord
  lda f:$434600,x
  sta fdMask
  lda fdPos
  sec
  sbc #$2401
  asl
  tax
  lda #16
  sta fdBits
fd_full_bit:
  lsr fdMask
  bcc :+
  lda fdPos
  bra :++
:
  lda #$2400
:
  sta f:$434000,x
  inx
  inx
  inc fdPos
  dec fdBits
  bne fd_full_bit
  inc fdWord
  inc fdWord
  lda fdWord
  cmp #96
  bcc fd_full_word
  rtl
fd_show:
  .repeat 736,I
    .word $2401+I
  .endrepeat
fd_hide:
  .repeat 736
    .word $2400
  .endrepeat
.assert ^fd_show=^(*-1),error,"map templates crossed ROM bank"
