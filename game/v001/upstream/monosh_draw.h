#ifndef MSXSH_MONOSH_DRAW_H
#define MSXSH_MONOSH_DRAW_H

#define MONOSH_DRAW_MAX 40u

#define MONOSH_DRAW_BUSH0    0u
#define MONOSH_DRAW_BUSH1    1u
#define MONOSH_DRAW_FLYSTONE 2u
#define MONOSH_DRAW_EM0      3u
#define MONOSH_DRAW_TREE0    4u
#define MONOSH_DRAW_BOM0     5u
#define MONOSH_DRAW_EBULLET0 6u
#define MONOSH_DRAW_EBULLET1 7u
#define MONOSH_DRAW_EBULLET2 8u
#define MONOSH_DRAW_PLAYER   9u
#define MONOSH_DRAW_PBULLET  10u
#define MONOSH_DRAW_EM1_CLOSED 11u
#define MONOSH_DRAW_EM1_OPEN   12u
#define MONOSH_DRAW_BOSS_BODY  13u
#define MONOSH_DRAW_BOSS_FACE  14u
#define MONOSH_DRAW_PLAYER_RUN0 15u
#define MONOSH_DRAW_PLAYER_RUN1 16u
#define MONOSH_DRAW_PLAYER_RUN2 17u
#define MONOSH_DRAW_PLAYER_RUN3 18u
#define MONOSH_DRAW_PLAYER_STUMBLE0 19u
#define MONOSH_DRAW_PLAYER_STUMBLE1 20u
#define MONOSH_DRAW_PLAYER_STUMBLE2 21u
#define MONOSH_DRAW_PLAYER_DEATH1 22u
#define MONOSH_DRAW_PLAYER_DEATH2 23u
#define MONOSH_DRAW_PLAYER_DEATH3 24u
#define MONOSH_DRAW_PLAYER_DEATH4 25u
#define MONOSH_DRAW_PLAYER_DEATH5 26u
#define MONOSH_DRAW_PLAYER_DEATH6 27u
#define MONOSH_DRAW_PLAYER_FLIGHT1 28u
#define MONOSH_DRAW_PLAYER_FLIGHT2 29u
#define MONOSH_DRAW_PLAYER_FLIGHT3 30u
#define MONOSH_DRAW_BOSS_BULLET 31u
#define MONOSH_DRAW_EM1_OPEN1 32u
#define MONOSH_DRAW_EM1_OPEN2 33u
#define MONOSH_DRAW_EM1_OPEN3 34u
#define MONOSH_DRAW_EM1_OPEN4 35u
#define MONOSH_DRAW_EM1_OPEN5 36u

typedef struct MonoshDrawCommand {
    signed int center_x;
    signed int bottom_y;
    unsigned char width;
    unsigned char height;
    unsigned char asset;
    unsigned char flags;
} MonoshDrawCommand;

extern MonoshDrawCommand monosh_draw_commands[MONOSH_DRAW_MAX];
extern unsigned char monosh_draw_count;

void monosh_draw_begin(void);
void monosh_draw_emit_all(void);

#endif
