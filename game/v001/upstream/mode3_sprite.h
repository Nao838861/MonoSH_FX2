#ifndef MSXSH_MODE3_SPRITE_H
#define MSXSH_MODE3_SPRITE_H

#define MODE3_SPRITE_PLANES 64u

#define MODE3_FLIP_X        0x10u
#define MODE3_FLIP_Y        0x20u
#define MODE3_BLEND_25       0x40u
#define MODE3_BLEND_50       0x80u
#define MODE3_BLEND_75       0xc0u

typedef struct Mode3PatternRef {
    unsigned char pattern;
    unsigned char page;
    unsigned char size_shift;
    unsigned char palette_set;
} Mode3PatternRef;

typedef struct Mode3SpriteStats {
    unsigned char planes_emitted;
    unsigned char objects_dropped;
} Mode3SpriteStats;

void mode3_sprite_begin(void);
void mode3_depth_begin(void);
void mode3_depth_end(void);
void mode3_fast_emit_player_direct(void);
void mode3_fast_emit_player_shadow_direct(void);
unsigned char mode3_sprite_emit_plane(signed int x,
                                      signed int y,
                                      unsigned char width,
                                      unsigned char height,
                                      const Mode3PatternRef *pattern,
                                      unsigned char flags);
unsigned char mode3_sprite_emit_scaled(signed int center_x,
                                       signed int bottom_y,
                                       unsigned char width,
                                       unsigned char height,
                                       const Mode3PatternRef *small,
                                       const Mode3PatternRef *wide_left,
                                       const Mode3PatternRef *wide_right,
                                       unsigned char flags);
void mode3_sprite_commit(void);
const Mode3SpriteStats *mode3_sprite_get_stats(void);

#endif
