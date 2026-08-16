package net.kdt.pojavlaunch.value;


import android.graphics.BitmapFactory;
import android.util.Log;

import net.kdt.pojavlaunch.*;
import net.kdt.pojavlaunch.utils.FileUtils;

import java.io.*;
import com.google.gson.*;
import android.graphics.Bitmap;
import android.util.Base64;

import androidx.annotation.Keep;
import androidx.annotation.Nullable;

import org.apache.commons.io.IOUtils;

@SuppressWarnings("IOStreamConstructor")
@Keep
public class MinecraftAccount {
    public String accessToken = "0"; // access token
    public String clientToken = "0"; // clientID: refresh and invalidate
    public String profileId = "00000000-0000-0000-0000-000000000000"; // profile UUID, for obtaining skin
    public String username = "Steve";
    public String selectedVersion = "1.7.10";
    public boolean isMicrosoft = false;
    public String msaRefreshToken = "0";
    public String xuid;
    public long expiresAt;
    public String skinFaceBase64;
    private Bitmap mFaceCache;
    
    void updateSkinFace(String uuid) {
        try {
            File skinFile = getSkinFaceFile(username);
            Tools.downloadFile("https://mc-heads.net/head/" + uuid + "/100", skinFile.getAbsolutePath());
            
            Log.i("SkinLoader", "Update skin face success");
        } catch (IOException e) {
            // Skin refresh limit, no internet connection, etc...
            // Simply ignore updating skin face
            Log.w("SkinLoader", "Could not update skin face", e);
        }
    }

    public boolean isLocal(){
        return accessToken.equals("0") && !username.startsWith("Demo.");
    }

    /**
     * Compute the UUID that an offline-mode server assigns to a given player name.
     * <p>
     * MULTIPLAYER OFFLINE: servidores com {@code online-mode=false} derivam o UUID do
     * jogador de {@code md5("OfflinePlayer:" + nome)} (UUID versao 3). Contas locais do
     * launcher usavam sempre o UUID nulo
     * ({@code 00000000-0000-0000-0000-000000000000}), o que fazia TODOS os jogadores
     * offline compartilharem a mesma identidade: inventarios, posicao e permissoes se
     * misturavam ao entrar num servidor com amigos.
     * <p>
     * Gerando o mesmo UUID que o servidor calcularia, cada jogador passa a ter
     * identidade propria e os dados persistem corretamente entre sessoes.
     *
     * @param username the player name
     * @return the offline-mode UUID for that name
     */
    public static String generateOfflineUUID(String username) {
        try {
            byte[] hash = java.security.MessageDigest.getInstance("MD5")
                    .digest(("OfflinePlayer:" + username).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            hash[6] = (byte) ((hash[6] & 0x0f) | 0x30); // version 3
            hash[8] = (byte) ((hash[8] & 0x3f) | 0x80); // IETF variant
            long msb = 0, lsb = 0;
            for (int i = 0; i < 8; i++) msb = (msb << 8) | (hash[i] & 0xff);
            for (int i = 8; i < 16; i++) lsb = (lsb << 8) | (hash[i] & 0xff);
            return new java.util.UUID(msb, lsb).toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            // MD5 e obrigatorio em toda JVM; se faltar, mantem o comportamento antigo.
            Log.e("MinecraftAccount", "MD5 unavailable, falling back to the null UUID", e);
            return "00000000-0000-0000-0000-000000000000";
        }
    }

    public boolean isDemo(){
        return username.startsWith("Demo.");
    }
    
    public void updateSkinFace() {
        updateSkinFace(profileId);
    }
    
    public String save(String outPath) throws IOException {
        Tools.write(outPath, Tools.GLOBAL_GSON.toJson(this));
        return username;
    }
    
    public String save() throws IOException {
        return save(Tools.DIR_ACCOUNT_NEW + "/" + username + ".json");
    }
    
    public static MinecraftAccount parse(String content) throws JsonSyntaxException {
        return Tools.GLOBAL_GSON.fromJson(content, MinecraftAccount.class);
    }
    @Nullable
    public static MinecraftAccount load(String name) {
        if(!accountExists(name)) return null;
        try {
            MinecraftAccount acc = parse(Tools.read(Tools.DIR_ACCOUNT_NEW + "/" + name + ".json"));
            if (acc.accessToken == null) {
                acc.accessToken = "0";
            }
            if (acc.clientToken == null) {
                acc.clientToken = "0";
            }
            if (acc.profileId == null) {
                acc.profileId = "00000000-0000-0000-0000-000000000000";
            }
            // Migra contas "Demo.<nome>" criadas por versoes anteriores do launcher.
            //
            // O prefixo "Demo." faz isDemo() retornar true, o que adiciona a flag
            // --demo (jogo limitado a ~100 minutos, mundo fixo) e desvia o diretorio
            // do jogo para /demo/.minecraft. Como agora criamos contas offline
            // completas nesse cenario, contas antigas ficariam presas no modo demo
            // para sempre. Renomeia removendo o prefixo e apaga o arquivo antigo.
            if (acc.username != null && acc.username.startsWith("Demo.")) {
                String oldName = acc.username;
                String newName = oldName.substring("Demo.".length());
                if (newName.isEmpty()) newName = "Player";
                acc.username = newName;
                acc.profileId = generateOfflineUUID(newName);
                try {
                    acc.save();
                    File oldFile = new File(Tools.DIR_ACCOUNT_NEW + "/" + oldName + ".json");
                    if (oldFile.exists() && !oldFile.delete()) {
                        Log.w("MinecraftAccount", "Could not delete the old demo account file");
                    }
                    Log.i("MinecraftAccount", "Migrated demo account to offline: " + newName);
                } catch (IOException e) {
                    Log.w("MinecraftAccount", "Could not persist the migrated demo account", e);
                    acc.username = oldName; // mantem o estado antigo se a migracao falhar
                }
            }

            // MULTIPLAYER OFFLINE: migra contas locais antigas que foram salvas com o
            // UUID nulo. Sem isso, quem ja tinha perfis offline continuaria com todos
            // os jogadores compartilhando a mesma identidade no servidor.
            if (acc.username != null
                    && acc.isLocal()
                    && "00000000-0000-0000-0000-000000000000".equals(acc.profileId)) {
                acc.profileId = generateOfflineUUID(acc.username);
                try {
                    acc.save();
                } catch (IOException e) {
                    Log.w("MinecraftAccount", "Could not persist the migrated offline UUID", e);
                }
            }
            if (acc.username == null) {
                acc.username = "0";
            }
            if (acc.selectedVersion == null) {
                acc.selectedVersion = "1.7.10";
            }
            if (acc.msaRefreshToken == null) {
                acc.msaRefreshToken = "0";
            }
            return acc;
        } catch(NullPointerException | IOException | JsonSyntaxException e) {
            Log.e(MinecraftAccount.class.getName(), "Caught an exception while loading the profile",e);
            return null;
        }
    }

    public Bitmap getSkinFace(){
        if(isLocal()) return null;

        File skinFaceFile = getSkinFaceFile(username);
        if (!skinFaceFile.exists()) {
            // Legacy version, storing the head inside the json as base 64
            if(skinFaceBase64 == null) return null;
            byte[] faceIconBytes = Base64.decode(skinFaceBase64, Base64.DEFAULT);
            return BitmapFactory.decodeByteArray(faceIconBytes, 0, faceIconBytes.length);
        } else {
            if(mFaceCache == null) {
                mFaceCache = BitmapFactory.decodeFile(skinFaceFile.getAbsolutePath());
            }
        }

        return mFaceCache;
    }

    public static Bitmap getSkinFace(String username) {
        return BitmapFactory.decodeFile(getSkinFaceFile(username).getAbsolutePath());
    }

    private static File getSkinFaceFile(String username) {
        return new File(Tools.DIR_CACHE, username + ".png");
    }

    private static boolean accountExists(String username){
        return new File(Tools.DIR_ACCOUNT_NEW + "/" + username + ".json").exists();
    }
}
