# AgentePublicidad · gestor de grupos

Implementación en Python del flujo de trabajo que vive en **GESTOR DE GRUPOS**, una hoja de Google Sheets. El proyecto publica las reglas y la integración, **no** exporta grupos, conversaciones, enlaces privados, teléfonos ni credenciales de la hoja real.

## Qué hace

- Lee `Grupos`, `Historial` y `Configuración`, y propone hasta 30 grupos de las áreas prácticas solicitadas.
- Respeta 30 días desde el último envío al mismo grupo y 7 días para una familia con confianza `Alta` o `Confirmada`.
- Evita repetir un posible gestor en la tanda; una familia `Media` o sin identificar ya contactada hoy no vuelve a sugerirse ese día.
- Añade envíos **declarados por la persona usuaria** a `Historial`, con fecha y hora de Madrid, sin inferir texto ni resultados.
- Busca invitaciones de WhatsApp publicadas en páginas web y las guarda como **candidatos por revisar** en `Grupos descubiertos`. Nunca interpreta un enlace como prueba de pertenencia, actividad o permiso de publicación.

La hoja original contiene fórmulas y un Top propio; este CLI calcula recomendaciones de forma independiente. Una automatización de ChatGPT que pudiera existir fuera del repositorio **no se traslada ni se activa** por subir este código. La búsqueda de GitHub Actions se activa cuando se configuran los secretos y se habilita el workflow en el repositorio.

## Preparación

1. Crea una cuenta de servicio de Google Cloud con acceso a la API de Google Sheets. Comparte la hoja existente con el correo de esa cuenta como editora.
2. Obtén una clave de Brave Search API para la búsqueda pública. No se usa la API de WhatsApp ni se accede a una cuenta personal.
3. Instala Python 3.11+ y el paquete:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -e .
   ```

4. Configura variables de entorno **fuera del repositorio**:

   ```bash
   export SPREADSHEET_ID='ID_DE_LA_HOJA_EXISTENTE'
   export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account", ...}'
   export BRAVE_API_KEY='CLAVE_DE_BRAVE'
   ```

   No copies aquí un JSON real de credenciales. En GitHub, configura esos mismos nombres en **Settings → Secrets and variables → Actions**. El secreto `BRAVE_API_KEY` solo se necesita para `discover`.

## Uso

```bash
agente-mariii recommend --limit 30
agente-mariii record-send G0001 --at 2026-10-06T20:30 --notes 'Envío confirmado por mí'
agente-mariii discover                  # vista previa, sin escribir
agente-mariii discover --write --limit 30
python -m unittest discover -s tests -v
```

`record-send` exige un ID o nombre inequívoco y bloquea otro registro en la misma fecha salvo `--force`. La hora se registra en `Notas`; `Fecha` contiene la fecha nativa de Sheets. El contenido y el resultado del mensaje quedan vacíos si no se aportan. El comando no envía mensajes.

`discover --write` solo añade filas a `Grupos descubiertos` con estado `Revisar enlace`. No incorpora candidatos a `Grupos` ni al Top. La persona usuaria debe comprobar acceso y normas antes de agregarlos. Las fuentes públicas pueden cambiar o caducar.

## Esquema esperado

La hoja existente usa estas pestañas y columnas relevantes:

| Pestaña | Campos que usa el programa |
| --- | --- |
| `Grupos` | A ID, B nombre, C familia/gestor posible, D confianza, J prioridad, K estado |
| `Historial` | A ID envío, B fecha, C grupo, D ID grupo, E familia, I notas |
| `Configuración` | A parámetro, B valor, G ID pendiente, H estado pendiente |
| `Grupos descubiertos` | A:Q, desde ID hallazgo hasta última comprobación |

La hoja conserva sus fórmulas de últimos envíos, estados y ranking. No ejecutes un segundo planificador de búsqueda si ya tienes otro proceso que escribe los mismos hallazgos sin comprobar duplicados.

## Límites y privacidad

Las familias inferidas por nombre son hipótesis, no administradores confirmados. El historial puede ser parcial: cero envíos anotados no implica que nunca se haya escrito. La búsqueda usa únicamente resultados públicos de Brave; no explora WhatsApp personal, grupos cerrados ni fuentes físicas por sí sola. Este repositorio es público: conserva fuera de él los datos, credenciales y configuraciones privadas.
