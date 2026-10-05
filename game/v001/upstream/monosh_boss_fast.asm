SECTION code_compiler

PUBLIC _monosh_boss_render_only

EXTERN _boss_attribute_cache
EXTERN _boss_attribute_cache_count
EXTERN _boss_render_camera_delta
EXTERN _monosh_ground_screen_delta
EXTERN _mode3_attributes
EXTERN _mode3_attribute_count

; Append the mode-3 attributes built by this field's 60 Hz boss update.
_monosh_boss_render_only:
    ld a,(_boss_attribute_cache_count)
    or a
    ret z
    ; NES refresh_frozen_actor_camera translates cached boss positions when
    ; player-death camera motion continues while boss logic is frozen.  The
    ; MSX cache contains final 10-bit V9968 Y coordinates, so translate those
    ; coordinates in place without rebuilding paths, sorting or attributes.
    ld b,a
    ld a,(_monosh_ground_screen_delta)
    ld e,a
    ld a,(_boss_render_camera_delta)
    cp e
    jr z,monosh_boss_camera_ready
    ld d,a
    ld a,e
    ld (_boss_render_camera_delta),a
    sub d
    ld c,a                         ; signed camera delta, low byte
    ld d,0
    bit 7,c
    jr z,monosh_boss_camera_sign_ready
    dec d                          ; signed camera delta, high byte
monosh_boss_camera_sign_ready:
    push ix
    ld ix,_boss_attribute_cache
monosh_boss_camera_shift_loop:
    ld a,(ix+0)
    add a,c
    ld (ix+0),a
    ld a,0
    adc a,d                        ; signed high delta plus low carry
    ld e,a
    ld a,(ix+1)
    ld l,a
    and 3
    add a,e
    and 3
    ld e,a
    ld a,l
    and $fc                        ; preserve size/flag bits
    or e
    ld (ix+1),a
    inc ix
    inc ix
    inc ix
    inc ix
    inc ix
    inc ix
    inc ix
    inc ix
    djnz monosh_boss_camera_shift_loop
    pop ix
monosh_boss_camera_ready:
    ld a,(_boss_attribute_cache_count)
    ld c,a
    ld a,(_mode3_attribute_count)
    ld e,a
    add a,c
    cp 65
    jr c,monosh_boss_cache_count_ready
    ld a,64
    sub e
    ld c,a
monosh_boss_cache_count_ready:
    ld a,c
    or a
    ret z
    add a,e
    ld (_mode3_attribute_count),a
    ld l,e
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,_mode3_attributes
    add hl,de
    ex de,hl
    ld hl,_boss_attribute_cache

    ; Plane count is at most eighteen.  Eight unrolled LDI operations avoid
    ; LDIR's five-cycle repeat penalty on every one of the 144 cache bytes.
    ld a,c
    ld bc,0
monosh_boss_cache_copy_loop:
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi
    ldi
    dec a
    jr nz,monosh_boss_cache_copy_loop
    ret
