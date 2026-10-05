SECTION code_compiler

PUBLIC _monosh_far_background_fast_scroll

EXTERN _monosh_far_u_scroll_acc
EXTERN _monosh_far_d_scroll_acc
EXTERN _monosh_far_u_offset
EXTERN _monosh_far_d_offset
EXTERN _monosh_far_u_scroll_high
EXTERN _monosh_far_u_scroll_low
EXTERN _monosh_far_d_scroll_high
EXTERN _monosh_far_d_scroll_low
EXTERN _monosh_far_scroll_active

; void monosh_far_background_fast_scroll(signed int player_x)
;     __z88dk_fastcall
;
; The original 128-pixel background advances by playerX*4 and *8 at 30 Hz.
; Its pixels are doubled for SCREEN 5, so bit 7 of each accumulator is the
; first visible fractional bit.  BC keeps the signed upper-layer step.
_monosh_far_background_fast_scroll:
    ; The normal forward path keeps the player centred.  Avoid touching all
    ; eight parallax variables until horizontal input actually displaces it.
    ld a,h
    or a
    jr nz,far_scroll_displaced
    ld a,l
    cp 128
    ret z
far_scroll_displaced:
    ld de,-128
    add hl,de
    add hl,hl
    ld b,h
    ld c,l

    ld de,(_monosh_far_u_scroll_acc)
    add hl,de
    ld (_monosh_far_u_scroll_acc),hl

    ; A = accumulator >> 7 (modulo 256).
    ld a,l
    rlca
    and 1
    ld e,a
    ld a,h
    add a,a
    or e
    ld (_monosh_far_u_offset),a
    ld e,a

    ; R#27 fine scroll leaves an undefined 1..7-pixel strip at the physical
    ; left edge.  Keep it at zero and let the page builder select one of the
    ; eight cyclically shifted upper-ridge masters.  R#26 supplies only the
    ; safe wrapped eight-pixel component.
    srl a
    srl a
    srl a
    ld (_monosh_far_u_scroll_high),a
    xor a
    ld (_monosh_far_u_scroll_low),a

    ld h,b
    ld l,c
    add hl,hl
    ld de,(_monosh_far_d_scroll_acc)
    add hl,de
    ld (_monosh_far_d_scroll_acc),hl

    ld a,l
    rlca
    and 1
    ld e,a
    ld a,h
    add a,a
    or e
    ld (_monosh_far_d_offset),a
    ld e,a
    srl a
    srl a
    srl a
    ld d,a
    ld a,e
    and 7
    jr z,far_lower_high_ready
    inc d
far_lower_high_ready:
    ld a,d
    ld (_monosh_far_d_scroll_high),a
    ld a,e
    neg
    and 7
    ld (_monosh_far_d_scroll_low),a
    ld a,(_monosh_far_u_scroll_high)
    ld e,a
    ld a,(_monosh_far_u_scroll_low)
    or e
    ld e,a
    ld a,(_monosh_far_d_scroll_high)
    or e
    ld e,a
    ld a,(_monosh_far_d_scroll_low)
    or e
    ld (_monosh_far_scroll_active),a
    ret
