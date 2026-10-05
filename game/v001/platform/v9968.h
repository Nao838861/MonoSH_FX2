/* 移植元Cのアップロード関数はSNES側で起動時にまとめて代替する。 */
void v9968_copy_to_vram_linear(unsigned long address,
                             const unsigned char *data, unsigned int size);
