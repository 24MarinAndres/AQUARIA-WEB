# AQUARIA WEB · ODS 14

Versión web de **AQUARIA**, adaptada del cuaderno académico `AQUARIA_CHATGPT_V03 (1)(1).ipynb`. Mantiene el propósito educativo y la lógica original: **una generación OpenAI de diez preguntas por partida**, tres opciones, una respuesta por turno, puntuación 0–100, retroalimentación, sesiones **Práctica / Piloto / Prueba técnica**, seis KPI, simulación del 60 % del ingreso elegible y descarga ZIP de los seis CSV.

Esta versión **se ejecuta en Streamlit**, no en GitHub Pages ni directamente en GitHub. GitHub almacena el código; Streamlit Community Cloud ejecuta Python y la solicitud privada a OpenAI. Los visitantes no necesitan una cuenta de Google Colab ni introducir una clave de API.

## Archivos

```text
AQUARIA-WEB/
├── streamlit_app.py         # Interfaz y flujo de juego
├── core.py                  # Reglas originales, validación y seis KPI
├── ai.py                    # Generación de preguntas por OpenAI
├── persistence.py           # Base de datos de eventos y cuota diaria
├── exportar.py              # Exportación de seis CSV a ZIP
├── requirements.txt         # Dependencias del alojamiento
├── .gitignore               # Excluye claves, base local y registros
├── .env.example             # Nombres de variables, SIN secretos
├── .streamlit/config.toml   # Aspecto visual (NO contiene claves)
├── tests/                   # Pruebas sin consumir tokens
└── .github/workflows/       # GitHub Actions: pruebas automáticas
```

## 1. Crea un repositorio en GitHub

1. Visita **https://github.com/new** y crea un repositorio llamado `AQUARIA-WEB` en tu cuenta.
2. Si no quieres exponer el código mientras lo pruebas, déjalo privado inicialmente.
3. Descomprime este ZIP **en tu computador**. Sube los **archivos descomprimidos**, no el ZIP.
4. Usa **Add file → Upload files** en GitHub. Asegúrate de que `streamlit_app.py` y `requirements.txt` queden en la **raíz** del repositorio. Conserva también las carpetas `tests/` y `.streamlit/`.
5. Confirma con **Commit changes**. No agregues nunca el valor real de `OPENAI_API_KEY` ni `DATABASE_URL` a GitHub. El archivo `.github/workflows/tests.yml` ejecuta pruebas automáticas en GitHub sin usar los créditos de OpenAI.

> Si usas tu repositorio `24MarinAndres/AQUARIA-WEB`, seleccionarás ese nombre en el despliegue. La dirección solo existirá cuando hayas creado el repositorio.

## 2. Despliega desde Streamlit Community Cloud

1. Entra en **https://share.streamlit.io** y accede con GitHub.
2. Pulsa **Create app → Yup, I have an app**.
3. Selecciona el repositorio `24MarinAndres/AQUARIA-WEB`, la rama `main` y el archivo `streamlit_app.py`.
4. Antes de pulsar Deploy, abre **Advanced settings → Secrets**.
5. Pega las siguientes variables, sustituyendo únicamente los textos de ejemplo por tus datos privados:

```toml
OPENAI_API_KEY = "TU_CLAVE_COMPLETA_DE_OPENAI"
AQUARIA_ADMIN_PASSWORD = "UNA_CONTRASENA_LARGA_Y_EXCLUSIVA"
AQUARIA_MAX_GENERATIONS_DAY = 5
AQUARIA_MAX_GENERATIONS_SESSION = 2
```

**Estos valores se escriben en los Secretos de Streamlit, nunca en un archivo que publiques.** La clave debe pertenecer al proyecto AQUARIA en Antares Tech. `AQUARIA_ADMIN_PASSWORD` es para exportar los registros de todas las personas, no para acceder al juego.

6. Pulsa **Deploy**. Community Cloud instalará `requirements.txt` y lanzará la aplicación.
7. Obtendrás una URL `https://<subdominio-disponible>.streamlit.app` que podrás compartir sin Colab. Una URL de ejemplo no es una aplicación ya publicada.
8. Verifica una partida con diez preguntas. Después revisa el consumo en **https://platform.openai.com/usage**, seleccionando la organización **Antares Tech** y el proyecto **AQUARIA**.

Documentación oficial: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## 3. IMPORTANTE: persistencia de registros y los seis KPI

Sin `DATABASE_URL` el programa utiliza **SQLite local**. Sirve para una prueba rápida, pero **Streamlit Community Cloud no garantiza que los archivos locales persistan**: un reinicio puede eliminar estadísticas, partidas y la cuota diaria. No utilices esa modalidad para un piloto académico con historial definitivo.

Para conservar datos y la cuota diaria de forma compartida entre todos los visitantes:

1. Crea una base de datos **PostgreSQL administrada**, por ejemplo en **Neon** (https://neon.tech).
2. En el panel de Neon, crea el proyecto y pulsa **Connect**.
3. Copia la cadena de conexión PostgreSQL **pooled**, con `sslmode=require` (no compartas esa cadena; contiene contraseña).
4. En **Streamlit Community Cloud → tu app → Settings → Secrets**, añade:

```toml
DATABASE_URL = "postgresql://USUARIO:CONTRASENA@HOST/NOMBRE_BD?sslmode=require"
```

5. Guarda la configuración y reinicia la app. Las tablas `events` y `generation_quota` se crean automáticamente. Los nuevos registros se guardarán en PostgreSQL.
6. **Los datos anteriores en SQLite no se migran automáticamente a PostgreSQL.** Configura PostgreSQL antes de recopilar resultados definitivos.

Esta base permite conservar los seis KPI conforme al criterio original (primer piloto por código, etc.) y hace que el límite diario esté compartido entre los usuarios del servidor. Guía de Neon: https://neon.com/docs/get-started/connect-neon

## 4. Qué se conserva y qué cambia

| Función | Versión web |
|---|---|
| Una llamada de IA por partida de 10 preguntas | Sí; `gpt-4.1-mini`, `store=False`, validación y mezcla de opciones |
| 10 turnos, 3 opciones, máximo 100 puntos | Sí |
| Respuesta única, explicación y botón Siguiente | Sí |
| Partidas completadas o abandonadas, último resultado | Sí, por sesión de navegador |
| Práctica, Piloto y Prueba técnica | Sí |
| Indicadores 1, 2, 3, 5 y 6 | Sí, misma definición lógica |
| Indicador 4: inicio de interfaz Python en Colab | **Adaptado** a inicio del script Python de la interfaz web; no es directamente comparable |
| Simulación académica de aporte del 60 % | Sí, sin pagos reales |
| CSV y ZIP | Sí; los visitantes descargan **solo sus propios registros** y el administrador puede descargar los globales |
| Fondo marino y opción pausar | Sí, implementados con HTML/CSS para web; no es la misma implementación ipywidgets |
| Segundo minijuego “Decisiones por el océano” | Sigue marcado **Próximamente**, como en el cuaderno original |
| Guardado de KPI entre reinicios | Sí, **si configuras PostgreSQL** |

**Privacidad:** no solicites nombre, correo ni teléfono como código de jugador. Las estadísticas globales se muestran agregadas. Los CSV globales solo pueden descargarse con contraseña de administración. El almacenamiento de respuestas guarda textos de preguntas y elecciones, así que informa a los participantes del registro académico de datos y establece una política de retención antes de publicar.

## 5. Control de gasto de la API

- El usuario **nunca escribe ni ve** la clave privada: solo la conoce el servidor.
- Por defecto hay un tope diario global de **15 intentos** y **3 por sesión**. Para pruebas iniciales usa **5 y 2** en Secretos, como en el ejemplo.
- Un intento fallido también reserva cuota: evita reintentos automáticos que agoten el saldo.
- Para que el tope global siga contando después de reinicios, configura PostgreSQL.
- Son controles básicos, **no una protección completa contra ataques distribuidos**. Antes de promover el enlace públicamente, considera un captcha, un proxy con límites por IP y restricciones de gastos en OpenAI Platform. Para uso intensivo, un backend con autenticación y almacenamiento duradero puede ser más adecuado.
- Configura alertas de gasto y revisa el consumo desde OpenAI Platform.

## 6. Ejecutar y probar en tu computador (opcional)

```bash
python -m venv .venv
# Activa el entorno virtual según tu sistema operativo.
pip install -r requirements.txt pytest
# Para ejecución local crea .streamlit/secrets.toml y coloca ahí los secretos,
# sin subir ese archivo a GitHub.
streamlit run streamlit_app.py
```

La aplicación abrirá una dirección local `http://localhost:8501`.

Para probar reglas de negocio sin utilizar tokens ni crédito de OpenAI:

```bash
python -m pytest -q
```

Los tests del adaptador de OpenAI utilizan una **respuesta simulada**. No afirman que se haya hecho una generación real desde este paquete. Prueba al menos una partida completa tras configurar los secretos en Streamlit Cloud.

## 7. Solución de problemas

- **Falta API:** comprueba `OPENAI_API_KEY` en **Secrets** del despliegue, no en los Secretos de Colab.
- **Clave revocada o inválida:** confirma en OpenAI Platform que la clave corresponde al proyecto AQUARIA y sigue activa.
- **La app se apaga o duerme:** los alojamientos gratuitos pueden hibernar; no borra el código de GitHub. Configura PostgreSQL si necesitas conservar el historial.
- **No hay nuevas partidas:** revisa la cuota diaria y la cuota por sesión; ambas usan días UTC o sesiones del navegador, respectivamente.
- **Los KPI globales desaparecen después de reiniciar:** no se configuró una base PostgreSQL persistente, o se cambió la conexión.
- **El servidor no conecta a PostgreSQL:** verifica credenciales y SSL; no publiques capturas que expongan `DATABASE_URL`.
- **La visualización no es idéntica a Colab:** `ipywidgets` no funciona como una app alojada en Streamlit; se conserva la experiencia y la lógica, pero se adaptan controles y disposición.

## Nota de despliegue

Este ZIP contiene el **proyecto preparado**, no una web ya publicada. GitHub y la cuenta de alojamiento requieren configuración y autorización del propietario. No publiques la contraseña de administrador ni la clave API en un issue, commit, README o captura.
