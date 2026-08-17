package net.kdt.pojavlaunch.utils;

import android.content.Context;
import android.content.res.Resources;
import android.util.Log;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.multirt.MultiRTUtils;
import net.kdt.pojavlaunch.multirt.Runtime;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;
import net.kdt.pojavlaunch.value.launcherprofiles.LauncherProfiles;
import net.kdt.pojavlaunch.value.launcherprofiles.MinecraftProfile;

import java.util.Arrays;
import java.util.List;

/**
 * Monta o resumo de configuracao mostrado na tela inicial.
 * <p>
 * Antes, para saber quanta RAM seria usada, qual runtime Java estava ativo ou
 * qual renderizador seria carregado, o usuario precisava abrir tres telas de
 * configuracao diferentes -- ou lancar o jogo e ler o log. Este resumo torna
 * essas tres informacoes visiveis de imediato, que sao justamente as que mais
 * causam falha de inicializacao.
 */
public final class LauncherStatus {
    private static final String TAG = "LauncherStatus";

    private LauncherStatus() {}

    /**
     * @return algo como {@code "3072 MB (auto) - Java 21 - MobileGlues"}, ou
     *         {@code null} se nem sequer a RAM puder ser determinada (caso em
     *         que a interface deve simplesmente esconder o resumo).
     */
    public static String describeCurrentSetup(Context context) {
        try {
            MinecraftProfile profile = getCurrentProfile();
            StringBuilder builder = new StringBuilder();

            int ram = LauncherPreferences.getEffectiveRAMAllocation(context);
            builder.append(context.getString(LauncherPreferences.PREF_RAM_AUTOMATIC
                    ? R.string.launcher_status_ram_auto
                    : R.string.launcher_status_ram_manual, ram));

            String java = describeRuntime(profile);
            if (java != null) builder.append("  \u2022  ").append(java);

            String renderer = describeRenderer(context, profile);
            if (renderer != null) builder.append("  \u2022  ").append(renderer);

            return builder.toString();
        } catch (RuntimeException e) {
            // O resumo e puramente informativo: nunca deve impedir a tela de abrir.
            Log.w(TAG, "Nao foi possivel montar o resumo de configuracao", e);
            return null;
        }
    }

    private static MinecraftProfile getCurrentProfile() {
        String currentProfile = LauncherPreferences.DEFAULT_PREF
                .getString(LauncherPreferences.PREF_KEY_CURRENT_PROFILE, null);
        if (!Tools.isValidString(currentProfile)) return null;
        LauncherProfiles.load();
        if (LauncherProfiles.mainProfileJson == null
                || LauncherProfiles.mainProfileJson.profiles == null) return null;
        return LauncherProfiles.mainProfileJson.profiles.get(currentProfile);
    }

    /** Versao maior do runtime que o perfil atual usaria (ex.: "Java 21"). */
    private static String describeRuntime(MinecraftProfile profile) {
        String runtimeName = profile != null
                ? Tools.getSelectedRuntime(profile)
                : LauncherPreferences.PREF_DEFAULT_RUNTIME;
        if (!Tools.isValidString(runtimeName)) return null;
        Runtime runtime = MultiRTUtils.read(runtimeName);
        if (runtime == null || runtime.javaVersion <= 0) return null;
        return "Java " + runtime.javaVersion;
    }

    /**
     * Nome amigavel do renderizador do perfil. Resolvido pelo indice em
     * {@code renderer_values} para reaproveitar as traducoes ja existentes,
     * em vez de repetir os nomes aqui.
     */
    private static String describeRenderer(Context context, MinecraftProfile profile) {
        if (profile == null || !Tools.isValidString(profile.pojavRendererName)) return null;
        Resources resources = context.getResources();
        List<String> ids = Arrays.asList(resources.getStringArray(R.array.renderer_values));
        String[] names = resources.getStringArray(R.array.renderer);
        int index = ids.indexOf(profile.pojavRendererName);
        if (index < 0 || index >= names.length) return profile.pojavRendererName;
        return names[index];
    }
}
