/* Valida a logica corrigida de convert_to_char_array/free_char_array
 * AUDITORIA 5.6 (malloc sem verificacao) e 5.7 (vazamento do array). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int freed_arrays = 0, released_strings = 0;

char** convert(int num_rows) {
    char **cArray = (char **) malloc(num_rows * sizeof(char*));
    if (cArray == NULL) { printf("OOM guard OK\n"); return NULL; }
    for (int i = 0; i < num_rows; i++) {
        cArray[i] = malloc(16);
        snprintf(cArray[i], 16, "arg%d", i);
    }
    return cArray;
}

void freeArr(int num_rows, const char **charArray) {
    if (charArray == NULL) return;                 /* guarda nova */
    for (int i = 0; i < num_rows; i++) {
        free((void*) charArray[i]);
        released_strings++;
    }
    free((void*) charArray);                       /* AUDITORIA 5.7 */
    freed_arrays++;
}

int main(void) {
    char** a = convert(5);
    printf("array alocado: %s %s\n", a[0], a[4]);
    freeArr(5, (const char**) a);
    printf("strings liberadas=%d arrays liberados=%d\n", released_strings, freed_arrays);
    freeArr(3, NULL);
    printf("NULL guard OK\n");
    return (freed_arrays == 1 && released_strings == 5) ? 0 : 1;
}
