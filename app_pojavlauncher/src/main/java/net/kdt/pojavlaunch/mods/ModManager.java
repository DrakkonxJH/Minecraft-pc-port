package net.kdt.pojavlaunch.mods;

import android.content.ContentResolver;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.util.Log;

import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.utils.FileUtils;
import net.kdt.pojavlaunch.value.launcherprofiles.MinecraftProfile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Operacoes sobre a pasta {@code mods} de um perfil.
 * <p>
 * <b>O problema que isto resolve.</b> Cada perfil pode ter seu proprio
 * diretorio de jogo ({@code gameDir}): perfis criados a partir de um modpack
 * apontam para {@code custom_instances/<nome>}, enquanto um perfil Fabric
 * criado a mao usa o {@code .minecraft} padrao. Nao havia nada na interface que
 * mostrasse isso -- entao era facil colocar os mods numa pasta e o jogo carregar
 * de outra, e o resultado era o jogo abrir "sem os mods" sem nenhuma mensagem
 * de erro.
 */
public final class ModManager {
    private static final String TAG = "ModManager";

    private ModManager() {}

    /**
     * Pasta {@code mods} do perfil informado.
     * <p>
     * Respeita o {@code gameDir} do perfil, que e justamente a origem da
     * confusao quando ignorado.
     */
    public static File getModsFolder(MinecraftProfile profile) {
        return new File(Tools.getGameDirPath(profile), "mods");
    }

    /**
     * Caminho relativo e legivel da pasta de mods, para mostrar na interface.
     * Ver a pasta real evita o erro de colocar mods no lugar errado.
     */
    public static String describeModsFolder(MinecraftProfile profile) {
        File folder = getModsFolder(profile);
        String home = Tools.DIR_GAME_HOME;
        String path = folder.getAbsolutePath();
        if (home != null && path.startsWith(home)) {
            String relative = path.substring(home.length());
            return relative.startsWith("/") ? relative.substring(1) : relative;
        }
        return path;
    }

    /**
     * Lista os mods do perfil, ativos e desativados.
     * <p>
     * Ordenados por nome, sem diferenciar maiusculas, para que a lista fique
     * estavel entre aberturas da tela.
     */
    public static List<ModEntry> listMods(MinecraftProfile profile) {
        File modsDir = getModsFolder(profile);
        File[] files = modsDir.listFiles(f -> {
            if (!f.isFile()) return false;
            String name = f.getName().toLowerCase(Locale.ROOT);
            return name.endsWith(".jar") || name.endsWith(".jar" + ModEntry.DISABLED_SUFFIX);
        });
        List<ModEntry> mods = new ArrayList<>();
        if (files == null) return mods;
        for (File f : files) mods.add(new ModEntry(f));
        Collections.sort(mods, Comparator.comparing(
                m -> m.getFileName().toLowerCase(Locale.ROOT)));
        return mods;
    }

    /** Quantos mods estao ativos (serao carregados pelo jogo). */
    public static int countEnabled(List<ModEntry> mods) {
        int n = 0;
        for (ModEntry m : mods) if (m.isEnabled()) n++;
        return n;
    }

    /**
     * Copia um {@code .jar} escolhido pelo usuario para a pasta de mods do perfil.
     *
     * @return o arquivo criado
     * @throws IOException se a copia falhar, ou se o arquivo nao for um .jar
     */
    public static File importMod(Context context, MinecraftProfile profile, Uri uri)
            throws IOException {
        String name = queryDisplayName(context.getContentResolver(), uri);
        if (name == null || !name.toLowerCase(Locale.ROOT).endsWith(".jar")) {
            throw new IOException("O arquivo selecionado nao e um .jar");
        }

        File modsDir = getModsFolder(profile);
        if (!FileUtils.ensureDirectorySilently(modsDir)) {
            throw new IOException("Nao foi possivel criar a pasta de mods");
        }

        File target = new File(modsDir, name);
        // Ja existe um mod com este nome: numeramos para nao sobrescrever em
        // silencio o que o usuario ja tinha.
        if (target.exists()) {
            String base = name.substring(0, name.length() - 4);
            int i = 2;
            do {
                target = new File(modsDir, base + " (" + i + ").jar");
                i++;
            } while (target.exists() && i < 100);
        }

        try (InputStream in = context.getContentResolver().openInputStream(uri);
             OutputStream out = new FileOutputStream(target)) {
            if (in == null) throw new IOException("Nao foi possivel ler o arquivo escolhido");
            byte[] buffer = new byte[65536];
            int read;
            while ((read = in.read(buffer)) != -1) out.write(buffer, 0, read);
            out.flush();
        } catch (IOException e) {
            //noinspection ResultOfMethodCallIgnored
            target.delete();
            throw e;
        }
        return target;
    }

    /**
     * Substitui um mod por outro arquivo, preservando o estado ligado/desligado.
     * Usado para atualizar um mod para uma versao nova.
     */
    public static File replaceMod(Context context, MinecraftProfile profile,
                                  ModEntry existing, Uri uri) throws IOException {
        boolean wasEnabled = existing.isEnabled();
        File imported = importMod(context, profile, uri);
        if (!existing.delete()) {
            Log.w(TAG, "Nao foi possivel remover o mod antigo: " + existing.getFileName());
        }
        if (!wasEnabled) {
            new ModEntry(imported).setEnabled(false);
        }
        return imported;
    }

    private static String queryDisplayName(ContentResolver resolver, Uri uri) {
        try (Cursor cursor = resolver.query(uri, new String[]{OpenableColumns.DISPLAY_NAME},
                null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) return cursor.getString(index);
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "Nao foi possivel ler o nome do arquivo", e);
        }
        // Alguns provedores nao respondem a consulta; caimos para o ultimo
        // segmento do caminho.
        String last = uri.getLastPathSegment();
        if (last != null) {
            int slash = last.lastIndexOf('/');
            return slash >= 0 ? last.substring(slash + 1) : last;
        }
        return null;
    }

    /** Tamanho legivel, para a lista. */
    public static String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format(Locale.US, "%.0f KB", bytes / 1024.0);
        return String.format(Locale.US, "%.1f MB", bytes / (1024.0 * 1024.0));
    }
}
