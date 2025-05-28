# Iris - Treball de Final de Grau

Aquest projecte forma part d’un Treball de Final de Grau i té com a objectiu analitzar i demostrar, en un entorn controlat, el funcionament d’una **backdoor** moderna, així com les tècniques d’ocultament, persistència i comunicació remota utilitzades habitualment en aquest tipus de malware.

⚠️ **Aquest projecte ha estat creat exclusivament amb finalitats educatives i de recerca.**

## 📂 Contingut del repositori

El repositori conté tres components principals:

- `SysUpdate.py` – Codi que s'executa a la màquina víctima.
- `proxy11.py` – Servidor intermediari (proxy) que connecta víctima i atacant.
- `main.py` – Interfície gràfica per part de l’atacant (GUI).
- `bckdr11.py` – Lògica de comunicació integrada dins la GUI.
- Carpeta `Updates/` – Versió portàtil de Python amb llibreries incloses.
- Altres scripts auxiliars i recursos gràfics (icones, recursos GUI, etc.).

## 🚀 Execució

1. **Executar el servidor proxy** (`proxy11.py`) en un servidor amb IP pública.
2. **Executar `SysUpdate.py`** a la màquina víctima (idealment des d’un USB amb Python portàtil).
3. **Executar `main.py`** des de l’atacant per obrir la GUI i connectar-se al proxy.

## 🔐 Xifratge

Les comunicacions entre víctima i atacant estan protegides amb **xifrat simètric Fernet**, garantint confidencialitat i evitant anàlisis simples de xarxa.

## 💡 Finalitat

Aquest projecte busca oferir una visió realista i didàctica del funcionament de les backdoors actuals, tot aprofundint en les tècniques de desenvolupament i les implicacions de seguretat associades.

---

🔗 Desenvolupat com a part del Treball de Final de Grau – Escola Politècnica Superior UDG
