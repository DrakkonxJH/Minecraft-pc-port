package net.kdt.pojavlaunch.customcontrols;

import android.content.Context;
import android.graphics.Color;
import android.util.Log;

import net.kdt.pojavlaunch.LwjglGlfwKeycode;
import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;

import java.io.File;
import java.io.IOException;

/**
 * Modelos de controle prontos, gerados em codigo.
 * <p>
 * Antes existia um unico layout ({@code assets/default.json}) e a alternativa
 * era montar tudo botao a botao no editor. Isso e trabalhoso e o resultado
 * costuma ficar pior que um layout pensado com calma -- posicao de botao em
 * tela sensivel ao toque tem armadilhas (alcance do polegar, sobreposicao com
 * o HUD do jogo) que nao sao obvias.
 * <p>
 * Os presets sao gerados por codigo em vez de virem como JSON em assets porque
 * as posicoes usam expressoes dinamicas ({@code ${width}}, {@code ${bottom}})
 * que se adaptam a qualquer tela; um JSON fixo teria de ser reescrito para cada
 * proporcao.
 */
public final class ControlPresets {
    private static final String TAG = "ControlPresets";

    /** Versao do layout que o launcher gera; deve acompanhar CustomControls. */
    private static final int LAYOUT_VERSION = 8;

    /** Identificadores estaveis, usados como nome de arquivo e em preferencias. */
    public static final String PRESET_CLASSIC = "classic";
    public static final String PRESET_GAMEPAD = "gamepad";
    public static final String PRESET_COMPACT = "compact";
    public static final String PRESET_LEFTY   = "lefty";

    private ControlPresets() {}

    /** Todos os presets disponiveis, na ordem em que aparecem na interface. */
    public static String[] all() {
        return new String[]{PRESET_CLASSIC, PRESET_GAMEPAD, PRESET_COMPACT, PRESET_LEFTY};
    }

    public static int titleRes(String preset) {
        switch (preset) {
            case PRESET_GAMEPAD: return R.string.control_preset_gamepad;
            case PRESET_COMPACT: return R.string.control_preset_compact;
            case PRESET_LEFTY:   return R.string.control_preset_lefty;
            default:             return R.string.control_preset_classic;
        }
    }

    public static int descriptionRes(String preset) {
        switch (preset) {
            case PRESET_GAMEPAD: return R.string.control_preset_gamepad_description;
            case PRESET_COMPACT: return R.string.control_preset_compact_description;
            case PRESET_LEFTY:   return R.string.control_preset_lefty_description;
            default:             return R.string.control_preset_classic_description;
        }
    }

    /**
     * Gera o preset e grava em {@code controlmap/<preset>.json}.
     *
     * @return o arquivo gravado, ou {@code null} se falhar
     */
    public static File generate(Context context, String preset) {
        CustomControls controls;
        switch (preset) {
            case PRESET_GAMEPAD: controls = buildGamepad(context); break;
            case PRESET_COMPACT: controls = buildCompact(context); break;
            case PRESET_LEFTY:   controls = buildLefty(context);   break;
            default:             controls = buildClassic(context); break;
        }
        controls.version = LAYOUT_VERSION;

        File target = new File(Tools.CTRLMAP_PATH, preset + ".json");
        try {
            //noinspection ResultOfMethodCallIgnored
            target.getParentFile().mkdirs();
            controls.save(target.getAbsolutePath());
            return target;
        } catch (IOException e) {
            Log.e(TAG, "Nao foi possivel gravar o preset " + preset, e);
            return null;
        }
    }

    // ---------------------------------------------------------------- estilos

    /**
     * Estilo visual aplicado a um botao. Reunido aqui para que os quatro
     * presets tenham aparencia coerente entre si e com a identidade do app.
     */
    private static void style(ControlData data, int bgColor, float cornerRadius, float opacity) {
        data.bgColor = bgColor;
        data.cornerRadius = cornerRadius;
        data.opacity = opacity;
        data.strokeWidth = 0;
        data.strokeColor = Color.TRANSPARENT;
    }

    /** Cinza translucido neutro, o mesmo tom historico do launcher. */
    private static final int COLOR_NEUTRAL = 0x4CC4C4C4;
    /** Esmeralda translucido da identidade MineDrakk, para acoes principais. */
    private static final int COLOR_PRIMARY = 0x552ECC71;
    /** Tom escuro para acoes secundarias, menos chamativo. */
    private static final int COLOR_SECONDARY = 0x66000000;

    // --------------------------------------------------------------- presets

    /**
     * Layout classico: o mesmo do PojavLauncher, com as cores da identidade.
     * Mantido para quem ja tem o costume dele.
     */
    private static CustomControls buildClassic(Context context) {
        CustomControls controls = new CustomControls(context);
        for (ControlData data : controls.mControlDataList) {
            style(data, COLOR_NEUTRAL, 20, 0.72f);
        }
        return controls;
    }

    /**
     * Estilo gamepad: D-pad a esquerda e botoes de acao em losango a direita,
     * como num controle de video game. Os botoes sao redondos e maiores, para
     * uso com os dois polegares.
     */
    private static CustomControls buildGamepad(Context context) {
        CustomControls controls = new CustomControls();
        controls.scaledAt = 100f;

        // Especiais indispensaveis (teclado, alternar controles, mouse virtual)
        addSpecial(controls, 0, "${margin} * 3 + ${width} * 2", "${margin}");
        addSpecial(controls, 1, "${margin}", "${bottom} - ${margin}");
        addSpecial(controls, 4, "${right}", "${margin}");

        // --- D-pad a esquerda, em cruz ---
        // O centro da cruz fica a uma distancia confortavel da borda para o
        // polegar esquerdo alcancar sem esticar.
        String padLeft = "${margin} * 2";
        String padCol2 = padLeft + " + ${width}";
        String padCol3 = padLeft + " + ${width} * 2";
        String padRow3 = "${bottom} - ${margin} * 2";
        String padRow2 = padRow3 + " - ${height}";
        String padRow1 = padRow3 + " - ${height} * 2";

        add(controls, context, R.string.control_up, LwjglGlfwKeycode.GLFW_KEY_W,
                padCol2, padRow1, true, COLOR_NEUTRAL, 100);
        add(controls, context, R.string.control_left, LwjglGlfwKeycode.GLFW_KEY_A,
                padLeft, padRow2, true, COLOR_NEUTRAL, 100);
        add(controls, context, R.string.control_right, LwjglGlfwKeycode.GLFW_KEY_D,
                padCol3, padRow2, true, COLOR_NEUTRAL, 100);
        add(controls, context, R.string.control_down, LwjglGlfwKeycode.GLFW_KEY_S,
                padCol2, padRow3, true, COLOR_NEUTRAL, 100);

        // --- Botoes de acao a direita, em losango (posicoes A/B/X/Y) ---
        String actRight = "${right} - ${margin} * 2 - ${width}";
        String actCol2 = actRight + " - ${width}";
        String actCol1 = actRight + " - ${width} * 2";
        String actRow3 = "${bottom} - ${margin} * 2";
        String actRow2 = actRow3 + " - ${height}";
        String actRow1 = actRow3 + " - ${height} * 2";

        // Posicao "A" (embaixo): pular -- a acao mais frequente
        add(controls, context, R.string.control_jump, LwjglGlfwKeycode.GLFW_KEY_SPACE,
                actCol2, actRow3, true, COLOR_PRIMARY, 100);
        // Posicao "X" (esquerda): agachar, com trava
        ControlData sneak = add(controls, context, R.string.control_shift,
                LwjglGlfwKeycode.GLFW_KEY_LEFT_SHIFT, actCol1, actRow2, true,
                COLOR_NEUTRAL, 100);
        sneak.isToggle = true;
        // Posicao "B" (direita): inventario
        add(controls, context, R.string.control_inventory, LwjglGlfwKeycode.GLFW_KEY_E,
                actRight, actRow2, true, COLOR_NEUTRAL, 100);
        // Posicao "Y" (em cima): correr
        ControlData sprint = add(controls, context, R.string.control_sprint,
                LwjglGlfwKeycode.GLFW_KEY_LEFT_CONTROL, actCol2, actRow1, true,
                COLOR_NEUTRAL, 100);
        sprint.isToggle = true;

        // --- Gatilhos: ataque e usar, no alto das laterais ---
        addSpecialStyled(controls, 2, "${margin} * 2", "${margin} * 2",
                COLOR_SECONDARY, 30);   // PRI (ataque), "LT"
        addSpecialStyled(controls, 3, "${right} - ${margin} * 2 - ${width}", "${margin} * 2",
                COLOR_SECONDARY, 30);   // SEC (usar), "RT"

        // --- Barra superior: itens de menu ---
        add(controls, context, R.string.control_chat, LwjglGlfwKeycode.GLFW_KEY_T,
                "${margin} * 5 + ${width} * 4", "${margin}", false, COLOR_SECONDARY, 20);
        add(controls, context, R.string.control_listplayers, LwjglGlfwKeycode.GLFW_KEY_TAB,
                "${margin} * 7 + ${width} * 6", "${margin}", false, COLOR_SECONDARY, 20);

        return controls;
    }

    /**
     * Compacto: botoes menores e mais transparentes, deixando o maximo de tela
     * livre. Pensado para telas pequenas e para quem se incomoda com o HUD
     * coberto de controles.
     */
    private static CustomControls buildCompact(Context context) {
        CustomControls controls = new CustomControls(context);
        for (ControlData data : controls.mControlDataList) {
            style(data, COLOR_NEUTRAL, 35, 0.45f);
            // Reduz em 20% mantendo a proporcao, para nao quebrar as expressoes
            // dinamicas de posicao que dependem de ${width} e ${height}.
            data.width *= 0.8f;
            data.height *= 0.8f;
        }
        return controls;
    }

    /**
     * Canhoto: espelha o layout classico, movendo o bloco de movimento para a
     * direita e as acoes para a esquerda.
     */
    private static CustomControls buildLefty(Context context) {
        CustomControls controls = new CustomControls(context);
        for (ControlData data : controls.mControlDataList) {
            style(data, COLOR_NEUTRAL, 20, 0.72f);
            data.dynamicX = mirrorX(data.dynamicX);
        }
        return controls;
    }

    /**
     * Espelha horizontalmente uma expressao de posicao.
     * <p>
     * As posicoes sao expressoes ({@code "${margin} * 2 + ${width}"}), nao
     * numeros, entao o espelhamento e feito envolvendo a expressao original:
     * {@code ${screen_width} - ${width} - (expressao)}. Assim o resultado
     * continua valido em qualquer resolucao.
     */
    private static String mirrorX(String dynamicX) {
        if (dynamicX == null || dynamicX.isEmpty()) return dynamicX;
        return "${screen_width} - ${width} - (" + dynamicX + ")";
    }

    // ------------------------------------------------------------- auxiliares

    private static ControlData add(CustomControls controls, Context context, int nameRes,
                                   int keycode, String x, String y, boolean square,
                                   int color, float cornerRadius) {
        ControlData data = new ControlData(context, nameRes, new int[]{keycode}, x, y, square);
        style(data, color, cornerRadius, 0.75f);
        controls.mControlDataList.add(data);
        return data;
    }

    private static void addSpecial(CustomControls controls, int index, String x, String y) {
        ControlData data = new ControlData(ControlData.getSpecialButtons()[index]);
        data.dynamicX = x;
        data.dynamicY = y;
        style(data, COLOR_SECONDARY, 20, 0.7f);
        controls.mControlDataList.add(data);
    }

    private static void addSpecialStyled(CustomControls controls, int index, String x, String y,
                                         int color, float cornerRadius) {
        ControlData data = new ControlData(ControlData.getSpecialButtons()[index]);
        data.dynamicX = x;
        data.dynamicY = y;
        style(data, color, cornerRadius, 0.7f);
        controls.mControlDataList.add(data);
    }
}
