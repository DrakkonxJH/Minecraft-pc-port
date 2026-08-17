package net.kdt.pojavlaunch.utils;

import android.app.ActivityManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.DisplayMetrics;
import android.util.Log;

import net.kdt.pojavlaunch.Architecture;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;

/**
 * Classifica o aparelho e aplica uma configuracao conhecidamente estavel para
 * a classe dele.
 * <p>
 * <b>Por que isto existe.</b> Os padroes do launcher foram calibrados em
 * aparelhos topo de linha. Num celular de entrada os mesmos padroes produzem
 * travamentos, encerramento pelo Android por pressao de memoria ou tela preta
 * -- e o usuario nao tem como saber que mexer em "surface alternativa" ou na
 * escala de resolucao resolveria. Aqui o launcher decide por ele.
 * <p>
 * <b>Principio de projeto:</b> este perfil so escolhe <i>padroes</i>. Tudo o
 * que o usuario ajustou manualmente continua valendo -- ver
 * {@link #applyRecommendedDefaults(Context, boolean)}.
 */
public final class DeviceProfile {
    private static final String TAG = "DeviceProfile";

    /** Marca que os padroes ja foram aplicados uma vez, para nao sobrescrever o usuario. */
    public static final String PREF_KEY_PROFILE_APPLIED = "deviceProfileApplied";
    /** Versao do perfil: incrementar reaplica os padroes apos uma atualizacao do app. */
    public static final String PREF_KEY_PROFILE_VERSION = "deviceProfileVersion";
    private static final int CURRENT_PROFILE_VERSION = 1;

    /** Classe de desempenho do aparelho. */
    public enum Tier {
        /**
         * Pouca RAM, CPU fraca, muitas vezes 32 bits ou GLES 2.
         * Prioriza "abrir e continuar aberto" acima de qualidade visual.
         */
        LOW,
        /** Intermediario: equilibra estabilidade e qualidade. */
        MEDIUM,
        /** Topo de linha: pode usar os recursos mais pesados. */
        HIGH
    }

    private DeviceProfile() {}

    /**
     * Classifica o aparelho por RAM, nucleos, arquitetura e GLES.
     * <p>
     * Usa varios sinais em vez de so a RAM porque eles discordam com frequencia:
     * ha celulares de entrada com 8 GB e CPU fraca, e aparelhos antigos de 4 GB
     * com CPU boa. O criterio e conservador -- na duvida, classifica para baixo,
     * porque um aparelho potente com configuracao conservadora perde um pouco de
     * qualidade, enquanto um aparelho fraco com configuracao agressiva nao roda.
     */
    public static Tier detectTier(Context context) {
        int ram = Tools.getTotalDeviceMemory(context);
        int cores = Runtime.getRuntime().availableProcessors();
        boolean is32Bit = Architecture.is32BitsDevice();

        // A versao do GLES so entra na conta se ja tiver sido consultada: criar um
        // contexto EGL custa dezenas de milissegundos e este metodo pode rodar na
        // thread principal durante a inicializacao. Quando ainda nao ha
        // informacao, os outros sinais decidem sozinhos.
        int gles = GLInfoUtils.hasInfo() ? GLInfoUtils.getGlInfo().glesMajorVersion : 3;

        // Qualquer um destes sozinho ja define aparelho de entrada.
        if (ram < 4096 || cores <= 4 || is32Bit || gles < 3) return Tier.LOW;

        // Topo de linha exige folga em todos os eixos.
        if (ram >= 8192 && cores >= 8 && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return Tier.HIGH;
        }
        return Tier.MEDIUM;
    }

    /**
     * Se o Android considera o aparelho com pouca memoria. Nesses aparelhos o
     * sistema encerra processos em segundo plano de forma muito mais agressiva.
     */
    public static boolean isLowRamDevice(Context context) {
        ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (am == null) return false;
        return am.isLowRamDevice();
    }

    /**
     * Escala de resolucao recomendada, em porcentagem.
     * <p>
     * Renderizar em resolucao menor e, de longe, o ajuste com maior efeito sobre
     * fluidez e temperatura: o custo por quadro cai com o quadrado da escala.
     * Telas de celular sao pequenas o bastante para que a perda seja discreta.
     */
    public static int recommendedResolutionScale(Context context, Tier tier) {
        DisplayMetrics metrics = context.getResources().getDisplayMetrics();
        int minSide = Math.min(metrics.widthPixels, metrics.heightPixels);

        // Lado menor que a renderizacao deve mirar, por classe de aparelho.
        int targetSide;
        switch (tier) {
            case LOW:    targetSide = 540;  break;
            case MEDIUM: targetSide = 720;  break;
            default:     targetSide = 1080; break;
        }
        if (minSide <= targetSide) return 100;

        int scale = Math.round(100f * targetSide / minSide);
        // O seekbar trabalha em incrementos; arredondar evita um valor que a
        // interface nao consegue representar.
        int increment = context.getResources()
                .getInteger(net.kdt.pojavlaunch.R.integer.resolution_seekbar_increment);
        scale = (int) (Math.ceil((double) scale / increment) * increment);

        // Piso por classe de aparelho. Num celular de entrada com tela 1440p o
        // alvo de 540p exigiria 37%, e sem um piso o texto do jogo fica
        // ilegivel; mas usar 50% para todos faria justamente os aparelhos mais
        // fracos com tela densa continuarem renderizando pixels demais. O piso
        // menor so vale para a classe de entrada, onde rodar importa mais que
        // nitidez.
        int floor = tier == Tier.LOW ? 35 : 50;
        return Math.max(floor, Math.min(scale, 100));
    }

    /**
     * Aplica os padroes recomendados para este aparelho.
     * <p>
     * <b>Nao sobrescreve escolhas do usuario.</b> Cada ajuste so e gravado se a
     * chave ainda nao existir em SharedPreferences, ou seja, se o usuario nunca
     * tocou naquela opcao. Quem ja configurou o launcher do jeito que gosta nao
     * tem nada alterado.
     *
     * @param force ignora a marca de "ja aplicado" e regrava tudo, inclusive por
     *              cima do que o usuario mudou. Usado apenas pelo botao
     *              "Otimizar para este aparelho" nas configuracoes.
     * @return a classe detectada, para exibicao
     */
    public static Tier applyRecommendedDefaults(Context context, boolean force) {
        SharedPreferences prefs = LauncherPreferences.DEFAULT_PREF;
        Tier tier = detectTier(context);

        boolean alreadyApplied = prefs.getBoolean(PREF_KEY_PROFILE_APPLIED, false);
        int appliedVersion = prefs.getInt(PREF_KEY_PROFILE_VERSION, 0);
        if (alreadyApplied && appliedVersion >= CURRENT_PROFILE_VERSION && !force) {
            return tier;
        }

        SharedPreferences.Editor editor = prefs.edit();
        boolean lowRam = isLowRamDevice(context);
        boolean highTier = tier == Tier.HIGH;

        // Resolucao: o ajuste de maior impacto em fluidez e temperatura.
        setIfAbsent(prefs, editor, force, "resolutionRatio",
                recommendedResolutionScale(context, tier));

        // Surface alternativa (SurfaceView): mais estavel e economica, mas alguns
        // drivers antigos a implementam mal. So ligamos onde ha confianca.
        setIfAbsent(prefs, editor, force, "alternate_surface", tier != Tier.LOW);

        // Modo de desempenho sustentado: o Android reduz o pico de clock para
        // evitar throttling termico. Em aparelho fraco o pico e justamente o que
        // segura os quadros, entao so faz sentido no topo de linha.
        setIfAbsent(prefs, editor, force, "sustainedPerformance", highTier);

        // VSync evita tearing e economiza bateria, mas limita os quadros. Em
        // aparelho fraco o problema e nao alcancar a taxa da tela, nao passar dela.
        setIfAbsent(prefs, editor, force, "force_vsync", highTier);

        // Afinidade com os nucleos rapidos ajuda quando ha nucleos lentos que
        // segurariam a thread principal do jogo.
        setIfAbsent(prefs, editor, force, "bigCoreAffinity", tier != Tier.HIGH);

        // Verificacao de SHA-1 das bibliotecas: custa CPU e I/O a cada
        // lancamento. Em aparelho de entrada isso e um atraso perceptivel, e a
        // protecao que oferece (deteccao de download corrompido) e secundaria.
        setIfAbsent(prefs, editor, force, "checkLibraries", tier != Tier.LOW);

        // RAM automatica: essencial em aparelho com pouca memoria, onde um heap
        // fixo grande demais faz o Android encerrar o jogo.
        setIfAbsent(prefs, editor, force, "allocationAutomatic", true);

        // Em aparelhos que o proprio Android marca como low-RAM, desligar a
        // animacao de fundo do launcher reduz a pressao de memoria.
        if (lowRam) {
            setIfAbsent(prefs, editor, force, "disableGestures", false);
        }

        editor.putBoolean(PREF_KEY_PROFILE_APPLIED, true);
        editor.putInt(PREF_KEY_PROFILE_VERSION, CURRENT_PROFILE_VERSION);
        editor.apply();

        Log.i(TAG, "Perfil aplicado: " + tier + " (lowRam=" + lowRam + ")");
        return tier;
    }

    /** Grava so se a chave ainda nao existir, preservando o que o usuario ajustou. */
    private static void setIfAbsent(SharedPreferences prefs, SharedPreferences.Editor editor,
                                    boolean force, String key, boolean value) {
        if (!force && prefs.contains(key)) return;
        editor.putBoolean(key, value);
    }

    private static void setIfAbsent(SharedPreferences prefs, SharedPreferences.Editor editor,
                                    boolean force, String key, int value) {
        if (!force && prefs.contains(key)) return;
        editor.putInt(key, value);
    }

    /** Resumo legivel do aparelho, para a tela de configuracoes e para o log. */
    public static String describe(Context context, Tier tier) {
        StringBuilder builder = new StringBuilder(tier.name())
                .append(" \u2022 ").append(Tools.getTotalDeviceMemory(context)).append(" MB")
                .append(" \u2022 ").append(Runtime.getRuntime().availableProcessors())
                .append(" cores");
        // So relata a GPU se ela ja tiver sido consultada, para nao criar um
        // contexto EGL apenas por causa de um texto informativo.
        if (GLInfoUtils.hasInfo()) {
            GLInfoUtils.GLInfo info = GLInfoUtils.getGlInfo();
            builder.append(" \u2022 ").append(info.getVendorFamily())
                    .append(" GLES ").append(info.glesMajorVersion);
        }
        return builder.toString();
    }
}
