#ifndef MSXSH_MONOSH_ENEMY_DATA_H
#define MSXSH_MONOSH_ENEMY_DATA_H

typedef struct MonoshEnemyPath {
    /* Interleaved sx,bottom,wz triplets keep the 60 Hz renderer
       to one pointer calculation and sequential ROM reads per enemy. */
    const unsigned char *samples;
    unsigned char frames;
    unsigned char fire_frame;
} MonoshEnemyPath;

typedef struct MonoshEnemySpawn {
    unsigned int wait;
    unsigned char type;
    unsigned char pattern;
} MonoshEnemySpawn;

extern const MonoshEnemyPath monosh_enemy_paths[9];
extern const unsigned char monosh_enemy_path_frames[9];
extern const unsigned char monosh_enemy_path_fire_frames[9];
extern const MonoshEnemySpawn monosh_enemy_spawns[];
/* Interleaved output width,height pairs indexed by depth or animation. */
extern const unsigned char monosh_enemy_geometry[222];
extern const unsigned char monosh_bom_geometry[222];
extern const unsigned char monosh_em1_closed_geometry[222];
extern const unsigned char monosh_em1_open_geometry[30];
extern const unsigned char monosh_enemy_ground_bottom[111];
extern const unsigned char * const monosh_ebullet_geometry[5];
extern const unsigned char monosh_ebullet_velocity[3328];

#endif
