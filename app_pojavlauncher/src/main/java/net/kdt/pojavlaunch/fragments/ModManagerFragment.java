package net.kdt.pojavlaunch.fragments;

import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.PopupMenu;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.widget.SwitchCompat;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import net.kdt.pojavlaunch.R;
import net.kdt.pojavlaunch.Tools;
import net.kdt.pojavlaunch.contracts.OpenDocumentWithExtension;
import net.kdt.pojavlaunch.mods.ModEntry;
import net.kdt.pojavlaunch.mods.ModManager;
import net.kdt.pojavlaunch.value.launcherprofiles.LauncherProfiles;
import net.kdt.pojavlaunch.value.launcherprofiles.MinecraftProfile;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Gerencia os mods de um perfil: ativar, desativar, adicionar, atualizar e
 * remover.
 * <p>
 * Antes disso a unica forma de mexer nos mods era pelo gerenciador de arquivos
 * do Android, e sem saber qual pasta o perfil realmente usa -- perfis de
 * modpack apontam para {@code custom_instances/<nome>}, nao para o
 * {@code .minecraft} padrao. Por isso a pasta em uso aparece no topo da tela.
 */
public class ModManagerFragment extends Fragment {
    public static final String TAG = "ModManagerFragment";
    /** Chave do argumento com o nome do perfil a editar. */
    public static final String BUNDLE_PROFILE_KEY = "profile_key";

    private String mProfileKey;
    private MinecraftProfile mProfile;
    private final List<ModEntry> mMods = new ArrayList<>();

    private TextView mFolderView, mSummaryView, mEmptyView;
    private RecyclerView mListView;
    private ModAdapter mAdapter;

    /** Mod que sera substituido pelo arquivo escolhido, quando atualizando. */
    private ModEntry mPendingUpdate;

    private final androidx.activity.result.ActivityResultLauncher<Object> mPickJar =
            registerForActivityResult(new OpenDocumentWithExtension("jar"), this::onJarPicked);

    public ModManagerFragment() {
        super(R.layout.fragment_mod_manager);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        Bundle args = getArguments();
        mProfileKey = args == null ? null : args.getString(BUNDLE_PROFILE_KEY);

        mFolderView = view.findViewById(R.id.mod_manager_folder);
        mSummaryView = view.findViewById(R.id.mod_manager_summary);
        mEmptyView = view.findViewById(R.id.mod_manager_empty);
        mListView = view.findViewById(R.id.mod_manager_list);

        mAdapter = new ModAdapter();
        mListView.setLayoutManager(new LinearLayoutManager(requireContext()));
        mListView.setAdapter(mAdapter);

        view.findViewById(R.id.mod_manager_add).setOnClickListener(v -> {
            mPendingUpdate = null;
            mPickJar.launch(null);
        });

        // Abre o CurseForge/Modrinth no navegador. Preferimos isso a embutir um
        // navegador: o download passa pelo gerenciador do Android, que lida com
        // Cloudflare e com os termos de uso dos sites, e o arquivo baixado entra
        // aqui pelo botao "Adicionar".
        view.findViewById(R.id.mod_manager_browse).setOnClickListener(v -> showBrowseDialog());

        loadProfile();
    }

    @Override
    public void onResume() {
        super.onResume();
        refresh();
    }

    private void loadProfile() {
        LauncherProfiles.load();
        if (mProfileKey != null && LauncherProfiles.mainProfileJson != null
                && LauncherProfiles.mainProfileJson.profiles != null) {
            mProfile = LauncherProfiles.mainProfileJson.profiles.get(mProfileKey);
        }
        if (mProfile == null) mProfile = LauncherProfiles.getCurrentProfile();
    }

    private void refresh() {
        if (mProfile == null) return;
        mFolderView.setText(ModManager.describeModsFolder(mProfile));

        mMods.clear();
        mMods.addAll(ModManager.listMods(mProfile));
        mAdapter.notifyDataSetChanged();

        int total = mMods.size();
        int enabled = ModManager.countEnabled(mMods);
        mSummaryView.setText(getString(R.string.mod_manager_summary, total, enabled));

        boolean empty = total == 0;
        mEmptyView.setVisibility(empty ? View.VISIBLE : View.GONE);
        mListView.setVisibility(empty ? View.GONE : View.VISIBLE);
    }

    private void onJarPicked(Uri uri) {
        if (uri == null || mProfile == null) return;
        try {
            if (mPendingUpdate != null) {
                ModManager.replaceMod(requireContext(), mProfile, mPendingUpdate, uri);
                toast(getString(R.string.mod_manager_updated,
                        mPendingUpdate.getDisplayName()));
            } else {
                ModManager.importMod(requireContext(), mProfile, uri);
                toast(getString(R.string.mod_manager_added));
            }
        } catch (IOException e) {
            toast(getString(R.string.mod_manager_add_failed, e.getMessage()));
        } finally {
            mPendingUpdate = null;
            refresh();
        }
    }

    /**
     * Oferece os catalogos de mods. Abrimos no navegador em vez de embutir um:
     * o download fica a cargo do Android, e o usuario traz o .jar pelo botao
     * "Adicionar".
     */
    private void showBrowseDialog() {
        String version = mProfile != null && mProfile.lastVersionId != null
                ? mProfile.lastVersionId : "";
        String query = extractMinecraftVersion(version);

        String modrinth = "https://modrinth.com/mods"
                + (query.isEmpty() ? "" : "?v=" + query);
        String curseforge = "https://www.curseforge.com/minecraft/search?class=mc-mods"
                + (query.isEmpty() ? "" : "&gameVersion=" + query);

        new AlertDialog.Builder(requireContext())
                .setTitle(R.string.mod_manager_browse)
                .setMessage(R.string.mod_manager_browse_message)
                .setPositiveButton("CurseForge",
                        (d, w) -> Tools.openURL(requireActivity(), curseforge))
                .setNeutralButton("Modrinth",
                        (d, w) -> Tools.openURL(requireActivity(), modrinth))
                .setNegativeButton(android.R.string.cancel, null)
                .show();
    }

    /**
     * Extrai a versao do Minecraft de um id de perfil.
     * <p>
     * Ids de perfis modificados vem como {@code fabric-loader-0.18.6-1.21.11}
     * ou {@code 1.21-forge-51.0.33}. Os catalogos filtram por versao do jogo,
     * entao pegamos o trecho que parece uma versao do Minecraft.
     */
    static String extractMinecraftVersion(String versionId) {
        if (versionId == null || versionId.isEmpty()) return "";

        // Os formatos de id colocam a versao do jogo em posicoes diferentes:
        //   fabric-loader-0.18.6-1.21.11  -> a do jogo vem por ULTIMO
        //   1.21-forge-51.0.33            -> a do jogo vem PRIMEIRO
        // Pegar sempre a ultima devolveria "51.0.33" (a versao do Forge) e
        // levaria o usuario ao catalogo filtrado pela versao errada.
        //
        // Regra: quando o id contem um nome de modloader, a versao do jogo e a
        // que aparece ANTES dele. Caso contrario, usamos a ultima candidata.
        String[] parts = versionId.split("[-_]");
        String[] loaders = {"forge", "neoforge", "fabric", "quilt", "optifine", "lwjgl3ify"};

        int loaderIndex = -1;
        for (int i = 0; i < parts.length; i++) {
            for (String loader : loaders) {
                if (parts[i].equalsIgnoreCase(loader)) {
                    loaderIndex = i;
                    break;
                }
            }
            if (loaderIndex >= 0) break;
        }

        // Versao imediatamente anterior ao nome do loader (caso do Forge)
        if (loaderIndex > 0) {
            for (int i = loaderIndex - 1; i >= 0; i--) {
                if (isGameVersion(parts[i])) return parts[i];
            }
        }

        // Caso contrario, a ultima candidata valida (caso do Fabric)
        String best = "";
        for (String part : parts) {
            if (isGameVersion(part)) best = part;
        }
        return best;
    }

    /**
     * Se o trecho parece uma versao do Minecraft.
     * <p>
     * Versoes de loader (0.18.6, 0.26.0) sao descartadas: nenhuma versao do
     * jogo comeca com zero.
     */
    private static boolean isGameVersion(String part) {
        return part.matches("\\d+\\.\\d+(\\.\\d+)?") && !part.startsWith("0.");
    }

    private void showModMenu(View anchor, ModEntry mod) {
        PopupMenu menu = new PopupMenu(requireContext(), anchor);
        menu.getMenu().add(0, 1, 0, R.string.mod_manager_update);
        menu.getMenu().add(0, 2, 1, R.string.mod_manager_delete);
        menu.setOnMenuItemClickListener(item -> {
            if (item.getItemId() == 1) {
                mPendingUpdate = mod;
                mPickJar.launch(null);
                return true;
            }
            if (item.getItemId() == 2) {
                confirmDelete(mod);
                return true;
            }
            return false;
        });
        menu.show();
    }

    private void confirmDelete(ModEntry mod) {
        new AlertDialog.Builder(requireContext())
                .setTitle(R.string.mod_manager_delete)
                .setMessage(getString(R.string.mod_manager_delete_confirm, mod.getFileName()))
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(android.R.string.ok, (d, w) -> {
                    if (!mod.delete()) {
                        toast(getString(R.string.mod_manager_delete_failed));
                    }
                    refresh();
                })
                .show();
    }

    private void toast(String message) {
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show();
    }

    // ------------------------------------------------------------- adaptador

    private class ModAdapter extends RecyclerView.Adapter<ModAdapter.Holder> {
        @NonNull
        @Override
        public Holder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View v = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_mod, parent, false);
            return new Holder(v);
        }

        @Override
        public void onBindViewHolder(@NonNull Holder holder, int position) {
            holder.bind(mMods.get(position));
        }

        @Override
        public int getItemCount() {
            return mMods.size();
        }

        class Holder extends RecyclerView.ViewHolder {
            private final SwitchCompat mSwitch;
            private final TextView mName, mDetails;

            Holder(View itemView) {
                super(itemView);
                mSwitch = itemView.findViewById(R.id.mod_item_switch);
                mName = itemView.findViewById(R.id.mod_item_name);
                mDetails = itemView.findViewById(R.id.mod_item_details);
            }

            void bind(ModEntry mod) {
                mName.setText(mod.getDisplayName());

                String version = mod.getVersionHint();
                String size = ModManager.formatSize(mod.getSizeBytes());
                mDetails.setText(version.isEmpty() ? size : version + "  \u2022  " + size);

                // Remove o listener antes de setChecked: o RecyclerView reaproveita
                // as views, e sem isso o estado da linha anterior dispararia uma
                // renomeacao no mod errado.
                mSwitch.setOnCheckedChangeListener(null);
                mSwitch.setChecked(mod.isEnabled());
                mSwitch.setOnCheckedChangeListener((button, checked) -> {
                    if (!mod.setEnabled(checked)) {
                        toast(getString(R.string.mod_manager_toggle_failed));
                        button.setChecked(!checked);
                        return;
                    }
                    int enabled = ModManager.countEnabled(mMods);
                    mSummaryView.setText(getString(R.string.mod_manager_summary,
                            mMods.size(), enabled));
                });

                itemView.findViewById(R.id.mod_item_menu)
                        .setOnClickListener(v -> showModMenu(v, mod));
            }
        }
    }
}
