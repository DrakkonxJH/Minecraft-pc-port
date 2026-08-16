package net.kdt.pojavlaunch;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.ListView;

import androidx.activity.OnBackPressedCallback;
import androidx.drawerlayout.widget.DrawerLayout;

import net.kdt.pojavlaunch.customcontrols.ControlData;
import net.kdt.pojavlaunch.customcontrols.ControlDrawerData;
import net.kdt.pojavlaunch.customcontrols.ControlJoystickData;
import net.kdt.pojavlaunch.customcontrols.ControlLayout;
import net.kdt.pojavlaunch.customcontrols.EditorExitable;
import net.kdt.pojavlaunch.prefs.LauncherPreferences;

import java.io.IOException;


public class CustomControlsActivity extends BaseActivity implements EditorExitable {
	private DrawerLayout mDrawerLayout;
	private ListView mDrawerNavigationView;
	private ControlLayout mControlLayout;

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		setContentView(R.layout.activity_custom_controls);

		getOnBackPressedDispatcher().addCallback(this, mBackCallback);

		mControlLayout = findViewById(R.id.customctrl_controllayout);
		mDrawerLayout = findViewById(R.id.customctrl_drawerlayout);
		mDrawerNavigationView = findViewById(R.id.customctrl_navigation_view);
		View mPullDrawerButton = findViewById(R.id.drawer_button);

		mPullDrawerButton.setOnClickListener(v -> mDrawerLayout.openDrawer(mDrawerNavigationView));
		mDrawerLayout.setDrawerLockMode(DrawerLayout.LOCK_MODE_LOCKED_CLOSED);

		mDrawerNavigationView.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1,getResources().getStringArray(R.array.menu_customcontrol_customactivity)));
		mDrawerNavigationView.setOnItemClickListener((parent, view, position, id) -> {
			switch(position) {
				case 0: mControlLayout.addControlButton(new ControlData("New")); break;
				case 1: mControlLayout.addDrawer(new ControlDrawerData()); break;
				case 2: mControlLayout.addJoystickButton(new ControlJoystickData()); break;
				case 3: mControlLayout.openLoadDialog(); break;
				case 4: mControlLayout.openSaveDialog(this); break;
				case 5: mControlLayout.openSetDefaultDialog(); break;
				case 6: // Saving the currently shown control
					try {
						Uri contentUri = DocumentsContract.buildDocumentUri(getString(R.string.storageProviderAuthorities), mControlLayout.saveToDirectory(mControlLayout.mLayoutFileName));

						Intent shareIntent = new Intent();
						shareIntent.setAction(Intent.ACTION_SEND);
						shareIntent.putExtra(Intent.EXTRA_STREAM, contentUri);
						shareIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
						shareIntent.setType("application/json");
						startActivity(shareIntent);

						Intent sendIntent = Intent.createChooser(shareIntent, mControlLayout.mLayoutFileName);
						startActivity(sendIntent);
					}catch (Exception e) {
						Tools.showError(this, e);
					}
					break;
			}
			mDrawerLayout.closeDrawers();
		});
		mControlLayout.setModifiable(true);
		try {
			mControlLayout.loadLayout(LauncherPreferences.PREF_DEFAULTCTRL_PATH);
		}catch (IOException e) {
			Tools.showError(this, e);
		}
	}

	// AUDITORIA 6 / B2: migrado de onBackPressed() para OnBackPressedDispatcher.
	// Com targetSdk 35+ o predictive back e padrao e onBackPressed() nao e mais
	// chamado, o que faria o editor fechar sem perguntar se ha alteracoes pendentes.
	private final OnBackPressedCallback mBackCallback = new OnBackPressedCallback(true) {
		@Override
		public void handleOnBackPressed() {
			mControlLayout.askToExit(CustomControlsActivity.this);
		}
	};

	@Override
	public void exitEditor() {
		// Desabilita o callback para que o proximo "voltar" siga o fluxo padrao
		// e efetivamente encerre a activity.
		mBackCallback.setEnabled(false);
		getOnBackPressedDispatcher().onBackPressed();
	}
}
