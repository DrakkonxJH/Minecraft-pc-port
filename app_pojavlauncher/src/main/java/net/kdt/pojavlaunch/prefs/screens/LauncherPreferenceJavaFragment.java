package net.kdt.pojavlaunch.prefs.screens;

import static net.kdt.pojavlaunch.Architecture.is32BitsDevice;
import static net.kdt.pojavlaunch.Tools.getTotalDeviceMemory;

import android.os.Bundle;
import android.widget.TextView;

import androidx.activity.result.ActivityResultLauncher;
import androidx.annotation.Nullable;
import androidx.preference.EditTextPreference;
import androidx.preference.Preference;
import androidx.preference.SwitchPreference;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.contracts.OpenDocumentWithExtension;
import net.kdt.pojavlaunch.multirt.MultiRTConfigDialog;
import net.kdt.pojavlaunch.prefs.CustomSeekBarPreference;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;

public class LauncherPreferenceJavaFragment extends LauncherPreferenceFragment {
    private MultiRTConfigDialog mDialogScreen;
    private SwitchPreference mSwitchAutoJRE;
    private final ActivityResultLauncher<Object> mVmInstallLauncher =
            registerForActivityResult(new OpenDocumentWithExtension("xz"), (data)->{
                if(data != null) Tools.installRuntimeFromUri(getContext(), data);
            });

    @Override
    public void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mSwitchAutoJRE = findPreference("disable_autojre_select");
        mSwitchAutoJRE.setSummary("Stops automatic selection of which runtime to use in \"" + getString(R.string.main_install_jar_file) + "\"");

    }

    @Override
    public void onCreatePreferences(Bundle b, String str) {
        int ramAllocation = LauncherPreferences.PREF_RAM_ALLOCATION;
        // Triggers a write for some reason
        addPreferencesFromResource(R.xml.pref_java);

        CustomSeekBarPreference memorySeekbar = requirePreference("allocation",
                CustomSeekBarPreference.class);

        int maxRAM;
        int deviceRam = getTotalDeviceMemory(memorySeekbar.getContext());

        if(is32BitsDevice() || deviceRam < 2048) maxRAM = Math.min(1024, deviceRam);
        else maxRAM = deviceRam - (deviceRam < 3064 ? 800 : 1024); //To have a minimum for the device to breathe

        memorySeekbar.setMaxKeepIncrement(maxRAM);
        memorySeekbar.setValue(ramAllocation);
        memorySeekbar.setSuffix(" MB");

        // MODO AUTOMATICO: quando ligado, o launcher recalcula a RAM a cada
        // lancamento (memoria livre + quantidade de mods), entao o slider manual
        // fica desabilitado para deixar claro que o valor nao sera usado.
        SwitchPreference automaticMemory = findPreference("allocationAutomatic");
        if (automaticMemory != null) {
            applyAutomaticMemoryState(automaticMemory, memorySeekbar, automaticMemory.isChecked());
            automaticMemory.setOnPreferenceChangeListener((preference, newValue) -> {
                applyAutomaticMemoryState(automaticMemory, memorySeekbar,
                        Boolean.TRUE.equals(newValue));
                return true;
            });
        }

        EditTextPreference editJVMArgs = findPreference("javaArgs");
        if (editJVMArgs != null) {
            editJVMArgs.setOnBindEditTextListener(TextView::setSingleLine);
        }

        requirePreference("install_jre").setOnPreferenceClickListener(preference->{
            openMultiRTDialog();
            return true;
        });
    }

    /**
     * Sincroniza a interface com o estado do modo automatico de RAM.
     * <p>
     * Quando ligado, o slider fica desabilitado (o valor dele nao seria usado) e
     * o resumo do switch passa a mostrar quanto seria reservado agora, para que o
     * usuario nao precise abrir o jogo so para descobrir esse numero.
     */
    private void applyAutomaticMemoryState(SwitchPreference automaticMemory,
                                           CustomSeekBarPreference memorySeekbar,
                                           boolean automatic) {
        memorySeekbar.setEnabled(!automatic);
        if (!automatic) {
            automaticMemory.setSummary(R.string.mcl_memory_automatic_subtitle);
            return;
        }
        int suggestion = LauncherPreferences.computeAutomaticRAM(
                automaticMemory.getContext(), Tools.countInstalledMods());
        memorySeekbar.setValue(suggestion);
        automaticMemory.setSummary(getString(R.string.mcl_memory_automatic_active, suggestion));
    }

    private void openMultiRTDialog() {
        if (mDialogScreen == null) {
            mDialogScreen = new MultiRTConfigDialog();
            mDialogScreen.prepare(getContext(), mVmInstallLauncher);
        }
        mDialogScreen.show();
    }
}
