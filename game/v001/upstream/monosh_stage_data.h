#ifndef MSXSH_MONOSH_STAGE_DATA_H
#define MSXSH_MONOSH_STAGE_DATA_H

typedef struct MonoshSpawnEntry {
    unsigned int frame;
    unsigned char type;
    signed int world_x;
    unsigned char data;
} MonoshSpawnEntry;

extern const MonoshSpawnEntry monosh_stage1_spawns[];
extern const unsigned int monosh_stage1_spawn_count;
/* Per asset/depth records: width, height, base bottom Y, half width. */
extern const unsigned char * const monosh_stage_geometry[6];
extern const unsigned char * const monosh_stage_lift[7];

#endif
