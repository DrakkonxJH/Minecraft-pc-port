package net.kdt.pojavlaunch.utils;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;

/**
 * Modo grafico escolhido pelo usuario: desempenho, automatico ou qualidade.
 * <p>
 * O {@link DeviceProfile} ja escolhe uma configuracao estavel para o aparelho,
 * mas essa escolha e uma so. Na pratica a preferencia varia com a situacao e
 * com a pessoa: o mesmo celular que roda liso em 60 fps num mundo vanilla
 * engasga num modpack pesado, e ha quem prefira imagem nitida a 30 fps
 * enquanto outros querem fluidez acima de tudo.
 * <p>
 * Este enum da esse controle em um unico toque, sem exigir que o usuario
 * entenda o que sao "surface alternativa", "desempenho sustentado" ou
 * "escala de resolucao" -- e sem tirar dele a possibilidade de continuar
 * ajustando cada item a mao depois.
 */
public enum GraphicsMode {
    /**
     * Prioriza quadros por segundo e temperatura. Reduz bastante a resolucao de
     * renderizacao e desliga tudo que custa tempo de quadro.
     */
    PERFORMANCE("performance"),

    /**
     * Deixa o launcher decidir a partir da classe do aparelho
     * ({@link DeviceProfile#detectTier(Context)}). Padrao.
     */
    AUTOMATIC("automatic"),

    /**
     * Prioriza nitidez. Renderiza em resolucao nativa e liga os recursos que
     * melhoram a imagem, ao custo de quadros e bateria.
     */
    QUALITY("quality");

    /** Chave em SharedPreferences. */
    public static final String PREF_KEY = "graphicsMode";
    private static final String TAG = "GraphicsMode";

    public final String key;

    GraphicsMode(String key) {
        this.key = key;
    }

    public static GraphicsMode fromKey(String key) {
        for (GraphicsMode mode : values()) {
            if (mode.key.equals(key)) return mode;
        }
        return AUTOMATIC;
    }

    /** Modo atualmente selecionado. */
    public static GraphicsMode current() {
        return fromKey(LauncherPreferences.DEFAULT_PREF.getString(PREF_KEY, AUTOMATIC.key));
    }

    /** Titulo curto para exibir na interface. */
    public int getTitleRes() {
        switch (this) {
            case PERFORMANCE: return R.string.graphics_mode_performance;
            case QUALITY:     return R.string.graphics_mode_quality;
            default:          return R.string.graphics_mode_automatic;
        }
    }

    public int getDescriptionRes() {
        switch (this) {
            case PERFORMANCE: return R.string.graphics_mode_performance_description;
            case QUALITY:     return R.string.graphics_mode_quality_description;
            default:          return R.string.graphics_mode_automatic_description;
        }
    }

    /**
     * Escala de renderizacao em porcentagem para este modo.
     * <p>
     * O modo automatico delega ao perfil do aparelho. Os outros dois usam a
     * classe do aparelho apenas como referencia e a deslocam para o lado
     * pedido, em vez de fixar um numero: 50% seria excessivo num topo de linha
     * e insuficiente num aparelho de entrada com tela 1440p.
     */
    public int resolutionScale(Context context) {
        DeviceProfile.Tier tier = DeviceProfile.detectTier(context);
        int automatic = DeviceProfile.recommendedResolutionScale(context, tier);
        switch (this) {
            case PERFORMANCE:
                // Um terco a menos de lado renderizado equivale a ~55% menos
                // pixels por quadro. Piso de 35%, abaixo disso o texto do jogo
                // fica ilegivel.
                return Math.max(35, roundToIncrement(context, (int) (automatic * 0.70f)));
            case QUALITY:
                return 100;
            default:
                return automatic;
        }
    }

    private static int roundToIncrement(Context context, int value) {
        int increment = context.getResources().getInteger(R.integer.resolution_seekbar_increment);
        return (int) (Math.ceil((double) value / increment) * increment);
    }

    /**
     * Aplica este modo, gravando as preferencias correspondentes.
     * <p>
     * Diferente do {@link DeviceProfile}, aqui <b>sobrescrevemos</b> os ajustes
     * de video: o usuario escolheu um modo explicitamente, entao ele espera ver
     * o efeito. Os itens que nao pertencem ao modo grafico (controles, RAM,
     * runtime) nao sao tocados.
     */
    public void apply(Context context) {
        SharedPreferences.Editor editor = LauncherPreferences.DEFAULT_PREF.edit();
        DeviceProfile.Tier tier = DeviceProfile.detectTier(context);
        boolean quality = this == QUALITY;
        boolean performance = this == PERFORMANCE;

        editor.putString(PREF_KEY, key);
        editor.putInt("resolutionRatio", resolutionScale(context));

        switch (this) {
            case PERFORMANCE:
                // VSync limita os quadros ao refresh da tela; no modo desempenho
                // queremos todos os quadros que a GPU conseguir entregar.
                editor.putBoolean("force_vsync", false);
                editor.putBoolean("vsync_in_zink", false);
                // Desempenho sustentado corta o clock de pico para evitar
                // aquecimento -- exatamente o oposto do que se quer aqui.
                editor.putBoolean("sustainedPerformance", false);
                // Fixar a thread do jogo nos nucleos rapidos evita que ela caia
                // num nucleo lento no meio da renderizacao.
                editor.putBoolean("bigCoreAffinity", true);
                // Verificar SHA-1 de todas as bibliotecas atrasa cada lancamento.
                editor.putBoolean("checkLibraries", false);
                break;

            case QUALITY:
                editor.putBoolean("force_vsync", true);
                editor.putBoolean("vsync_in_zink", true);
                // Aqui o objetivo e sessao longa e estavel, sem throttling brusco.
                editor.putBoolean("sustainedPerformance", true);
                editor.putBoolean("bigCoreAffinity", false);
                editor.putBoolean("checkLibraries", true);
                break;

            default: // AUTOMATIC: volta ao que o perfil do aparelho recomenda
                boolean high = tier == DeviceProfile.Tier.HIGH;
                editor.putBoolean("force_vsync", high);
                editor.putBoolean("vsync_in_zink", true);
                editor.putBoolean("sustainedPerformance", high);
                editor.putBoolean("bigCoreAffinity", !high);
                editor.putBoolean("checkLibraries", tier != DeviceProfile.Tier.LOW);
                break;
        }

        // A surface alternativa e mais leve, mas alguns drivers antigos a
        // implementam mal. No modo qualidade preferimos a mais compativel;
        // no de desempenho, a mais leve -- desde que o aparelho nao seja da
        // classe de entrada, onde ela costuma dar problema.
        if (performance) {
            editor.putBoolean("alternate_surface", tier != DeviceProfile.Tier.LOW);
        } else if (quality) {
            editor.putBoolean("alternate_surface", false);
        }

        editor.apply();
        Log.i(TAG, "Modo grafico aplicado: " + key + " (tier " + tier + ")");
    }
}
