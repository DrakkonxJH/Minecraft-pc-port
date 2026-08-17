package net.kdt.pojavlaunch.mods;

import androidx.annotation.NonNull;

import java.io.File;
import java.util.Locale;

/**
 * Um arquivo de mod dentro da pasta {@code mods} de um perfil.
 * <p>
 * Representa tanto os mods ativos ({@code .jar}) quanto os desativados
 * ({@code .jar.disabled}). A convencao do sufixo {@code .disabled} e a mesma
 * usada pelo Fabric, pelo Forge e pelo Mod Menu: o carregador ignora arquivos
 * que nao terminam em {@code .jar}, entao renomear e a forma padrao de
 * desligar um mod sem perde-lo.
 */
public class ModEntry {
    /** Sufixo que marca um mod desativado. */
    public static final String DISABLED_SUFFIX = ".disabled";

    private File file;

    public ModEntry(File file) {
        this.file = file;
    }

    public File getFile() {
        return file;
    }

    /** Se o mod sera carregado pelo jogo. */
    public boolean isEnabled() {
        return file.getName().toLowerCase(Locale.ROOT).endsWith(".jar");
    }

    /** Nome do arquivo sem o sufixo {@code .disabled}, para exibicao. */
    public String getFileName() {
        String name = file.getName();
        if (name.toLowerCase(Locale.ROOT).endsWith(DISABLED_SUFFIX)) {
            return name.substring(0, name.length() - DISABLED_SUFFIX.length());
        }
        return name;
    }

    /**
     * Nome legivel, sem a extensao e sem a versao no final.
     * <p>
     * Nomes de mod costumam vir como {@code sodium-fabric-0.5.8+mc1.20.1.jar}.
     * Mostrar isso inteiro numa lista fica ilegivel, entao cortamos a extensao
     * e o que vem depois do primeiro numero de versao.
     */
    public String getDisplayName() {
        String name = getFileName();
        if (name.toLowerCase(Locale.ROOT).endsWith(".jar")) {
            name = name.substring(0, name.length() - 4);
        }
        // Corta a partir de "-<digito>" ou "_<digito>", que costuma iniciar a versao
        int cut = -1;
        for (int i = 1; i < name.length() - 1; i++) {
            char c = name.charAt(i);
            if ((c == '-' || c == '_' || c == '+') && Character.isDigit(name.charAt(i + 1))) {
                cut = i;
                break;
            }
        }
        if (cut > 0) name = name.substring(0, cut);
        return name.replace('_', ' ').trim();
    }

    /** Versao deduzida do nome do arquivo, ou string vazia se nao houver. */
    public String getVersionHint() {
        String name = getFileName();
        if (name.toLowerCase(Locale.ROOT).endsWith(".jar")) {
            name = name.substring(0, name.length() - 4);
        }
        for (int i = 1; i < name.length() - 1; i++) {
            char c = name.charAt(i);
            if ((c == '-' || c == '_' || c == '+') && Character.isDigit(name.charAt(i + 1))) {
                return name.substring(i + 1);
            }
        }
        return "";
    }

    public long getSizeBytes() {
        return file.length();
    }

    /**
     * Liga ou desliga o mod, renomeando o arquivo.
     *
     * @return {@code true} se a operacao foi concluida
     */
    public boolean setEnabled(boolean enabled) {
        if (enabled == isEnabled()) return true;
        File target = enabled
                ? new File(file.getParentFile(), getFileName())
                : new File(file.getParentFile(), getFileName() + DISABLED_SUFFIX);
        if (target.exists()) return false;
        if (!file.renameTo(target)) return false;
        file = target;
        return true;
    }

    /** Apaga o arquivo do mod. */
    public boolean delete() {
        return file.delete();
    }

    @NonNull
    @Override
    public String toString() {
        return getFileName();
    }
}
