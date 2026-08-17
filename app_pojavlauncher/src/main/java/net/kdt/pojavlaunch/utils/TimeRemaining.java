package net.kdt.pojavlaunch.utils;

import android.content.Context;

import net.kdt.pojavlaunch.R;

/**
 * Converte "quanto falta" e "quao rapido esta indo" em um texto curto de tempo
 * restante.
 * <p>
 * Existe porque a barra de download mostrava apenas porcentagem e velocidade
 * instantanea. Numa primeira instalacao de Minecraft (algumas centenas de MB
 * em milhares de arquivos pequenos) isso nao responde a unica pergunta que o
 * usuario tem: da pra esperar ou e melhor deixar baixando e voltar depois?
 */
public final class TimeRemaining {
    /**
     * Abaixo desta velocidade a estimativa fica sem sentido (dividir por algo
     * proximo de zero gera "faltam 900 horas"). Nesses casos nao mostramos nada.
     */
    private static final double MIN_MEANINGFUL_SPEED = 1024; // 1 KB/s

    /** Acima disso a estimativa e tao incerta que exibi-la so atrapalha. */
    private static final long MAX_MEANINGFUL_SECONDS = 24 * 60 * 60;

    private TimeRemaining() {}

    /**
     * @param remainingBytes bytes que ainda faltam baixar
     * @param bytesPerSecond velocidade media atual, em bytes por segundo
     * @return texto como {@code "2 min restantes"}, ou {@code null} quando a
     *         estimativa nao for confiavel o bastante para ser mostrada
     */
    public static String format(Context context, long remainingBytes, double bytesPerSecond) {
        if (remainingBytes <= 0) return null;
        if (bytesPerSecond < MIN_MEANINGFUL_SPEED) return null;

        long seconds = (long) Math.ceil(remainingBytes / bytesPerSecond);
        if (seconds <= 0 || seconds > MAX_MEANINGFUL_SECONDS) return null;

        if (seconds < 60) {
            return context.getString(R.string.eta_seconds, seconds);
        }
        if (seconds < 3600) {
            // Arredonda para cima: prometer 1 min e levar 1 min e 50 s frustra
            // mais do que prometer 2 min e terminar antes.
            long minutes = (seconds + 59) / 60;
            return context.getString(R.string.eta_minutes, minutes);
        }
        long hours = seconds / 3600;
        long minutes = (seconds % 3600) / 60;
        return context.getString(R.string.eta_hours, hours, minutes);
    }
}
