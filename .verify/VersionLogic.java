/* Replica exata da logica corrigida em Tools.java (AUDITORIA 5.2 e 5.3)
 * e da antiga, para comparar comportamento lado a lado. */
public class VersionLogic {

    /* ---------- implementacao NOVA (corrigida) ---------- */
    static int versionComponent(String[] components, int index) {
        if (components == null || index >= components.length) return -1;
        String raw = components[index].trim();
        int end = 0;
        while (end < raw.length() && Character.isDigit(raw.charAt(end))) end++;
        if (end == 0) return -1;
        try { return Integer.parseInt(raw.substring(0, end)); }
        catch (NumberFormatException e) { return -1; }
    }

    static boolean versionAtLeast(String[] components, int minMajor, int minMinor) {
        int major = versionComponent(components, 0);
        if (major < 0) return false;
        if (major != minMajor) return major > minMajor;
        int minor = versionComponent(components, 1);
        if (minor < 0) return false;
        return minor >= minMinor;
    }

    /* ---------- implementacao ANTIGA (com bugs) ---------- */
    static String oldBehaviour(String libName) {
        try {
            String[] version = libName.split(":")[2].split("\\.");
            boolean skip = Integer.parseInt(version[0]) >= 5 && Integer.parseInt(version[1]) >= 13;
            return skip ? "mantem" : "troca p/ 5.13.0";
        } catch (ArrayIndexOutOfBoundsException e) {
            return "CRASH: ArrayIndexOutOfBounds";
        } catch (NumberFormatException e) {
            return "CRASH: NumberFormatException";
        }
    }

    static String newBehaviour(String libName) {
        if (libName == null) return "ignorado";
        String[] nameParts = libName.split(":");
        if (nameParts.length < 3) return "ignorado (coordenada malformada)";
        String[] version = nameParts[2].split("\\.");
        return versionAtLeast(version, 5, 13) ? "mantem" : "troca p/ 5.13.0";
    }

    public static void main(String[] args) {
        String[] cases = {
            "net.java.dev.jna:jna:5.13.0",          // novo o suficiente -> mantem
            "net.java.dev.jna:jna:5.14.0",          // mais novo -> mantem
            "net.java.dev.jna:jna:6.2.1",           // BUG 5.3: antigo fazia DOWNGRADE
            "net.java.dev.jna:jna:6.0.0",           // BUG 5.3: idem
            "net.java.dev.jna:jna:4.5.2",           // antigo de verdade -> troca
            "net.java.dev.jna:jna:5.12.9",          // minor menor -> troca
            "net.java.dev.jna:jna:5.13.0-SNAPSHOT", // BUG 5.2: NumberFormatException
            "net.java.dev.jna:jna:5",               // BUG 5.2: AIOOBE (sem minor)
            "net.java.dev.jna:jna:2.0.0-beta",      // BUG 5.2: NumberFormatException
            "net.java.dev.jna:jna:1.0.0+build1",    // BUG 5.2: NumberFormatException
            "grupo:artefato",                       // BUG 5.2: AIOOBE (sem versao)
        };

        System.out.printf("%-38s | %-28s | %s%n", "LIBRARY", "ANTIGO", "NOVO");
        System.out.println("-".repeat(100));
        int crashes = 0, downgrades = 0;
        for (String c : cases) {
            String o = oldBehaviour(c), n = newBehaviour(c);
            if (o.startsWith("CRASH")) crashes++;
            if (o.equals("troca p/ 5.13.0") && n.equals("mantem")) downgrades++;
            System.out.printf("%-38s | %-28s | %s%n", c, o, n);
        }
        System.out.println("-".repeat(100));
        System.out.println("Crashes evitados: " + crashes);
        System.out.println("Downgrades indevidos evitados: " + downgrades);
        if (crashes == 0 || downgrades == 0) {
            System.out.println("FALHA: o teste deveria demonstrar ambos os problemas");
            System.exit(1);
        }
        System.out.println("OK");
    }
}
