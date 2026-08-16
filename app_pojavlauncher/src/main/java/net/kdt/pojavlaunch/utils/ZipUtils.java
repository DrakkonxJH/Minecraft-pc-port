package net.kdt.pojavlaunch.utils;

import org.apache.commons.io.IOUtils;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Enumeration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public class ZipUtils {
    /**
     * Gets an InputStream for a given ZIP entry, throwing an IOException if the ZIP entry does not
     * exist.
     * @param zipFile The ZipFile to get the entry from
     * @param entryPath The full path inside of the ZipFile
     * @return The InputStream provided by the ZipFile
     * @throws IOException if the entry was not found
     */
    public static InputStream getEntryStream(ZipFile zipFile, String entryPath) throws IOException{
        ZipEntry entry = zipFile.getEntry(entryPath);
        if(entry == null) throw new IOException("No entry in ZIP file: "+entryPath);
        return zipFile.getInputStream(entry);
    }

    /**
     * Extracts all files in a ZipFile inside of a given directory to a given destination directory
     * How to specify dirName:
     * If you want to extract all files in the ZipFile, specify ""
     * If you want to extract a single directory, specify its full path followed by a trailing /
     * @param zipFile The ZipFile to extract files from
     * @param dirName The directory to extract the files from
     * @param destination The destination directory to extract the files into
     * @throws IOException if it was not possible to create a directory or file extraction failed
     */
    public static void zipExtract(ZipFile zipFile, String dirName, File destination) throws IOException {
        Enumeration<? extends ZipEntry> zipEntries = zipFile.entries();

        // AUDITORIA 4.3 (Zip Slip): resolvemos o diretorio de destino uma unica vez
        // para comparar contra o caminho canonico de cada entrada extraida.
        String canonicalDestination = destination.getCanonicalPath() + File.separator;

        int dirNameLen = dirName.length();
        while(zipEntries.hasMoreElements()) {
            ZipEntry zipEntry = zipEntries.nextElement();
            String entryName = zipEntry.getName();
            if(!entryName.startsWith(dirName) || zipEntry.isDirectory()) continue;
            File zipDestination = new File(destination, entryName.substring(dirNameLen));

            // AUDITORIA 4.3 (Zip Slip): um archive malicioso pode conter entradas como
            // "../../../../data/data/<pacote>/files/x". Sem esta verificacao a extracao
            // escreveria fora do diretorio de destino. Como o launcher instala modpacks
            // de terceiros (CurseForge/Modrinth), o vetor e real.
            if(!isInsideDirectory(zipDestination, canonicalDestination)) {
                throw new IOException("Blocked Zip Slip attempt, entry resolves outside of the "
                        + "destination directory: " + entryName);
            }

            FileUtils.ensureParentDirectory(zipDestination);
            try (InputStream inputStream = zipFile.getInputStream(zipEntry);
                 OutputStream outputStream = new FileOutputStream(zipDestination)) {
                IOUtils.copy(inputStream, outputStream);
            }
        }
    }

    /**
     * Check that a resolved file stays within a given canonical directory.
     * Used to prevent Zip Slip (path traversal) when extracting untrusted archives.
     * @param target the file that is about to be written
     * @param canonicalDirectoryWithSeparator the canonical destination directory, with a trailing separator
     * @return true when the target is contained by the destination directory
     * @throws IOException if the canonical path of the target cannot be resolved
     */
    public static boolean isInsideDirectory(File target, String canonicalDirectoryWithSeparator) throws IOException {
        return target.getCanonicalPath().startsWith(canonicalDirectoryWithSeparator);
    }
}
