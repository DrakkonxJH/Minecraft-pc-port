package net.kdt.pojavlaunch.prefs.screens;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Toast;

import androidx.preference.ListPreference;
import androidx.preference.PreferenceCategory;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.prefs.CustomSeekBarPreference;
import net.kdt.pojavlaunch.customcontrols.ControlPresets;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;

import java.io.File;

public class LauncherPreferenceControlFragment extends LauncherPreferenceFragment {
    private boolean mGyroAvailable = false;

    @Override
    public void onCreatePreferences(Bundle b, String str) {
        // Get values
        int longPressTrigger = LauncherPreferences.PREF_LONGPRESS_TRIGGER;
        int prefButtonSize = (int) LauncherPreferences.PREF_BUTTONSIZE;
        int mouseScale = (int) (LauncherPreferences.PREF_MOUSESCALE * 100);
        int gyroSampleRate = LauncherPreferences.PREF_GYRO_SAMPLE_RATE;
        int touchControllerVibrateLength = LauncherPreferences.PREF_TOUCHCONTROLLER_VIBRATE_LENGTH;
        float mouseSpeed = LauncherPreferences.PREF_MOUSESPEED;
        float gyroSpeed = LauncherPreferences.PREF_GYRO_SENSITIVITY;
        float joystickDeadzone = LauncherPreferences.PREF_DEADZONE_SCALE;


        //Triggers a write for some reason which resets the value
        addPreferencesFromResource(R.xml.pref_control);

        setupControlPresets();

        CustomSeekBarPreference seek2 = requirePreference("timeLongPressTrigger",
                CustomSeekBarPreference.class);
        seek2.setValue(longPressTrigger);
        seek2.setSuffix(" ms");

        CustomSeekBarPreference seek3 = requirePreference("buttonscale",
                CustomSeekBarPreference.class);
        seek3.setValue(prefButtonSize);
        seek3.setSuffix(" %");

        CustomSeekBarPreference seek4 = requirePreference("mousescale",
                CustomSeekBarPreference.class);
        seek4.setValue(mouseScale);
        seek4.setSuffix(" %");

        CustomSeekBarPreference seek6 = requirePreference("mousespeed",
                CustomSeekBarPreference.class);
        seek6.setValue((int) (mouseSpeed * 100f));
        seek6.setSuffix(" %");

        CustomSeekBarPreference deadzoneSeek = requirePreference("gamepad_deadzone_scale",
                CustomSeekBarPreference.class);
        deadzoneSeek.setValue((int) (joystickDeadzone * 100f));
        deadzoneSeek.setSuffix(" %");


        Context context = getContext();
        if (context != null) {
            mGyroAvailable = Tools.deviceSupportsGyro(context);
        }
        PreferenceCategory gyroCategory = requirePreference("gyroCategory",
                PreferenceCategory.class);
        gyroCategory.setVisible(mGyroAvailable);

        CustomSeekBarPreference gyroSensitivitySeek = requirePreference("gyroSensitivity",
                CustomSeekBarPreference.class);
        gyroSensitivitySeek.setValue((int) (gyroSpeed * 100f));
        gyroSensitivitySeek.setSuffix(" %");

        CustomSeekBarPreference gyroSampleRateSeek = requirePreference("gyroSampleRate",
                CustomSeekBarPreference.class);
        gyroSampleRateSeek.setValue(gyroSampleRate);
        gyroSampleRateSeek.setSuffix(" ms");

        CustomSeekBarPreference touchControllerVibrateLengthSeek = requirePreference(
                "touchControllerVibrateLength",
                CustomSeekBarPreference.class);
        touchControllerVibrateLengthSeek.setValue(touchControllerVibrateLength);
        touchControllerVibrateLengthSeek.setSuffix(" ms");

        computeVisibility();
    }

    @Override
    public void onSharedPreferenceChanged(SharedPreferences p, String s) {
        super.onSharedPreferenceChanged(p, s);
        computeVisibility();
    }

    private void computeVisibility() {
        requirePreference("timeLongPressTrigger").setVisible(!LauncherPreferences.PREF_DISABLE_GESTURES);
        requirePreference("gyroSensitivity").setVisible(LauncherPreferences.PREF_ENABLE_GYRO);
        requirePreference("gyroSampleRate").setVisible(LauncherPreferences.PREF_ENABLE_GYRO);
        requirePreference("gyroInvertX").setVisible(LauncherPreferences.PREF_ENABLE_GYRO);
        requirePreference("gyroInvertY").setVisible(LauncherPreferences.PREF_ENABLE_GYRO);
        requirePreference("gyroSmoothing").setVisible(LauncherPreferences.PREF_ENABLE_GYRO);
    }


    /**
     * Seletor de modelo de controles.
     * <p>
     * Gera o layout escolhido em {@code controlmap/<preset>.json} e o define
     * como padrao. O layout anterior nao e apagado: se o usuario tinha um
     * arquivo proprio, ele continua la para ser reaberto no editor.
     */
    private void setupControlPresets() {
        ListPreference presetPreference = findPreference("controlPreset");
        if (presetPreference == null) return;

        presetPreference.setOnPreferenceChangeListener((preference, newValue) -> {
            String preset = String.valueOf(newValue);
            File generated = ControlPresets.generate(requireContext(), preset);
            if (generated == null) {
                Toast.makeText(requireContext(), R.string.control_preset_failed,
                        Toast.LENGTH_LONG).show();
                return false;
            }
            // Passa a ser o layout carregado ao entrar no jogo.
            LauncherPreferences.DEFAULT_PREF.edit()
                    .putString("defaultCtrl", generated.getAbsolutePath())
                    .apply();
            LauncherPreferences.loadPreferences(requireContext());
            Toast.makeText(requireContext(),
                    getString(R.string.control_preset_applied,
                            getString(ControlPresets.titleRes(preset))),
                    Toast.LENGTH_SHORT).show();
            return true;
        });
    }
}
