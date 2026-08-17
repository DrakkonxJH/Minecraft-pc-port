package net.kdt.pojavlaunch.prefs.screens;

import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AlertDialog;

import androidx.preference.ListPreference;
import androidx.preference.SwitchPreference;
import androidx.preference.SwitchPreferenceCompat;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.prefs.CustomSeekBarPreference;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;
import net.kdt.pojavlaunch.utils.DeviceProfile;
import net.kdt.pojavlaunch.utils.GraphicsMode;

/**
 * Fragment for any settings video related
 */
public class LauncherPreferenceVideoFragment extends LauncherPreferenceFragment {
    @Override
    public void onCreatePreferences(Bundle b, String str) {
        addPreferencesFromResource(R.xml.pref_video);
        int resolution = (int) (LauncherPreferences.PREF_SCALE_FACTOR * 100);

        //Disable notch checking behavior on android 8.1 and below.
        requirePreference("ignoreNotch").setVisible(Build.VERSION.SDK_INT >= Build.VERSION_CODES.P && LauncherPreferences.PREF_NOTCH_SIZE > 0);

        CustomSeekBarPreference resolutionSeekbar = requirePreference("resolutionRatio",
                CustomSeekBarPreference.class);
        resolutionSeekbar.setSuffix(" %");

        // #724 bug fix
        if (resolution < 25) {
            resolutionSeekbar.setValue(100);
        } else {
            resolutionSeekbar.setValue(resolution);
        }

        // Sustained performance is only available since Nougat
        SwitchPreference sustainedPerfSwitch = requirePreference("sustainedPerformance",
                SwitchPreference.class);
        sustainedPerfSwitch.setVisible(Build.VERSION.SDK_INT >= Build.VERSION_CODES.N);
        sustainedPerfSwitch.setChecked(LauncherPreferences.PREF_SUSTAINED_PERFORMANCE);

        requirePreference("alternate_surface", SwitchPreferenceCompat.class).setChecked(LauncherPreferences.PREF_USE_ALTERNATE_SURFACE);
        requirePreference("force_vsync", SwitchPreferenceCompat.class).setChecked(LauncherPreferences.PREF_FORCE_VSYNC);

        setupGraphicsMode();
        setupOptimizeButton();
        computeVisibility();
    }

    /**
     * Seletor de modo grafico. Ao trocar, aplica na hora os ajustes do modo e
     * recarrega a tela para os controles refletirem os novos valores -- do
     * contrario o usuario veria o slider de resolucao com o valor antigo.
     */
    private void setupGraphicsMode() {
        ListPreference graphicsMode = findPreference(GraphicsMode.PREF_KEY);
        if (graphicsMode == null) return;

        graphicsMode.setOnPreferenceChangeListener((preference, newValue) -> {
            GraphicsMode mode = GraphicsMode.fromKey(String.valueOf(newValue));
            mode.apply(requireContext());
            LauncherPreferences.loadPreferences(requireContext());
            Toast.makeText(requireContext(),
                    getString(R.string.graphics_mode_applied, getString(mode.getTitleRes())),
                    Toast.LENGTH_SHORT).show();
            refreshVideoControls();
            return true;
        });
    }

    /**
     * Atualiza os controles da tela apos uma alteracao em lote das preferencias.
     * <p>
     * A primeira versao disto recriava a tela inteira
     * ({@code setPreferenceScreen(null)} seguido de {@code onCreatePreferences}).
     * Isso era perigoso: gravar as preferencias dispara
     * {@link #onSharedPreferenceChanged}, que chama {@code computeVisibility()}
     * e portanto {@code requirePreference()} -- e esse metodo <b>lanca
     * IllegalStateException</b> quando a tela esta nula. Ou seja, trocar o modo
     * grafico podia derrubar o app numa condicao de corrida.
     * <p>
     * Atualizar cada controle no lugar e mais simples e nao tem esse risco.
     */
    private void refreshVideoControls() {
        CustomSeekBarPreference resolutionSeekbar = findPreference("resolutionRatio");
        if (resolutionSeekbar != null) {
            resolutionSeekbar.setValue((int) (LauncherPreferences.PREF_SCALE_FACTOR * 100));
        }
        SwitchPreference sustained = findPreference("sustainedPerformance");
        if (sustained != null) {
            sustained.setChecked(LauncherPreferences.PREF_SUSTAINED_PERFORMANCE);
        }
        SwitchPreferenceCompat alternateSurface = findPreference("alternate_surface");
        if (alternateSurface != null) {
            alternateSurface.setChecked(LauncherPreferences.PREF_USE_ALTERNATE_SURFACE);
        }
        SwitchPreferenceCompat forceVsync = findPreference("force_vsync");
        if (forceVsync != null) {
            forceVsync.setChecked(LauncherPreferences.PREF_FORCE_VSYNC);
        }
        SwitchPreferenceCompat vsyncInZink = findPreference("vsync_in_zink");
        if (vsyncInZink != null) {
            vsyncInZink.setChecked(LauncherPreferences.PREF_VSYNC_IN_ZINK);
        }
        // O botao "Otimizar para este aparelho" reescreve as mesmas chaves do
        // modo grafico e volta a selecao para "automatico"; o seletor precisa
        // acompanhar, senao exibiria um modo que nao corresponde aos valores.
        ListPreference graphicsMode = findPreference(GraphicsMode.PREF_KEY);
        if (graphicsMode != null) {
            graphicsMode.setValue(GraphicsMode.current().key);
        }
        computeVisibility();
    }

    /**
     * Botao que reaplica o perfil de estabilidade do aparelho.
     * <p>
     * Diferente da aplicacao automatica na primeira execucao, aqui o usuario
     * pediu explicitamente, entao sobrescrevemos os ajustes manuais dele -- por
     * isso a confirmacao antes.
     */
    private void setupOptimizeButton() {
        androidx.preference.Preference optimize = findPreference("optimizeForDevice");
        if (optimize == null) return;

        DeviceProfile.Tier tier = DeviceProfile.detectTier(requireContext());
        optimize.setSummary(getString(R.string.preference_optimize_device_description)
                + "\n\n" + DeviceProfile.describe(requireContext(), tier));

        optimize.setOnPreferenceClickListener(preference -> {
            new AlertDialog.Builder(requireContext())
                    .setTitle(R.string.preference_optimize_device_title)
                    .setMessage(R.string.preference_optimize_device_confirm)
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(android.R.string.ok, (dialog, which) -> {
                        DeviceProfile.Tier applied =
                                DeviceProfile.applyRecommendedDefaults(requireContext(), true);
                        LauncherPreferences.loadPreferences(requireContext());
                        Toast.makeText(requireContext(),
                                getString(R.string.preference_optimize_device_done,
                                        describeTier(applied)),
                                Toast.LENGTH_LONG).show();
                        refreshVideoControls();
                    })
                    .show();
            return true;
        });
    }

    private String describeTier(DeviceProfile.Tier tier) {
        switch (tier) {
            case LOW:  return getString(R.string.device_tier_low);
            case HIGH: return getString(R.string.device_tier_high);
            default:   return getString(R.string.device_tier_medium);
        }
    }

    @Override
    public void onSharedPreferenceChanged(SharedPreferences p, String s) {
        super.onSharedPreferenceChanged(p, s);
        computeVisibility();
    }

    private void computeVisibility(){
        // findPreference em vez de requirePreference: este metodo e chamado pelo
        // listener de SharedPreferences, que pode disparar quando a tela ainda
        // nao foi montada (ou ja foi destruida). requirePreference lancaria.
        SwitchPreferenceCompat forceVsync = findPreference("force_vsync");
        if (forceVsync == null) return;
        forceVsync.setVisible(LauncherPreferences.PREF_USE_ALTERNATE_SURFACE);
    }
}
