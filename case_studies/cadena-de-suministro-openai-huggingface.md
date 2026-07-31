## Caso en profundidad · La cadena de suministro de modelos: OpenAI y Hugging Face (2023–2024)

**Incidentes analizados:** INC-011 (OpenAI, fuga vía `redis-py`, 20-03-2023) · INC-014 (tokens del
Hub expuestos, 04-12-2023) · INC-019 (modelos maliciosos en el Hub, 27-02-2024) · INC-022 (secretos
de Spaces, 31-05-2024).

Los cuatro se cuentan casi siempre por separado. Juntos describen mejor el problema real: **la
superficie de ataque de un sistema de IA moderno casi nunca es el modelo.** Es todo lo que hay
alrededor —la caché, el token, el formato de serialización, el contenedor— y todo eso se hereda de
terceros con el nivel de confianza con que se instala una dependencia.

---

### 1. Qué pasó

**INC-011 — OpenAI, 20 de marzo de 2023.** Durante unas nueve horas, algunos usuarios de ChatGPT
vieron en su barra lateral títulos de conversaciones de **otros** usuarios. La causa no estuvo en el
modelo ni en el producto: fue un fallo en `redis-py`, el cliente de la caché. Cuando una petición se
cancelaba, la conexión podía devolverse al *pool* con una respuesta pendiente sin leer; la siguiente
petición que reutilizaba esa conexión recibía datos que no le correspondían. Un pico de carga
multiplicó las cancelaciones y con ellas la probabilidad de colisión. OpenAI confirmó además que el
**1,2 % de los suscriptores de ChatGPT Plus** activos en esa ventana pudo tener expuestos nombre,
correo, dirección de facturación y los cuatro últimos dígitos de su tarjeta.

**INC-014 — Tokens del Hub, diciembre de 2023.** Lasso Security encontró **1.681 tokens de API
válidos** publicados en repositorios de Hugging Face y GitHub. No eran cuentas irrelevantes: varios
daban permiso de **escritura** sobre organizaciones como Meta-Llama, Bloom o Pythia. Quien tuviera
uno podía haber sustituido los pesos de un modelo que millones de proyectos descargan como
dependencia.

**INC-019 — Modelos maliciosos, febrero de 2024.** JFrog identificó alrededor de **100 modelos
maliciosos** publicados en el Hub. Al menos uno abría una *reverse shell* en la máquina del
científico de datos en el momento de cargar el checkpoint. El vector es el formato: un `.bin` de
PyTorch es un `pickle` de Python, y deserializar un `pickle` **es ejecutar código**. `from_pretrained()`
tiene, en ese formato, la misma superficie de riesgo que `curl | bash`.

**INC-022 — Secretos de Spaces, mayo de 2024.** Hugging Face detectó acceso no autorizado a la
infraestructura de Spaces, con posible exfiltración de los secretos que los usuarios guardan ahí
—entre ellos, claves de API de otros proveedores—. La respuesta fue revocar tokens y forzar rotación.

---

### 2. Causa raíz

El síntoma es distinto en cada caso; el mecanismo es el mismo tres veces de cuatro.

**Causa raíz común (INC-014, INC-019, INC-022): el ecosistema de ML trata artefactos ejecutables de
terceros como si fueran datos.** Un modelo descargado del Hub es, a efectos prácticos, un binario sin
firmar de un autor no verificado que se ejecuta con los permisos del usuario. La industria del
software resolvió esto hace veinte años —firma de paquetes, checksums, escaneo, SBOM, principio de
mínimo privilegio— y el ecosistema de ML lo reconstruyó desde cero sin esas defensas, porque creció
desde la investigación, donde compartir pesos sin fricción era la prioridad correcta. Los tokens con
permiso de escritura sobre organizaciones grandes (INC-014) son la misma deuda vista desde el otro
lado: el control de acceso al artefacto es tan débil como el peor secreto de cualquier colaborador.

**Causa raíz de INC-011: acoplamiento entre concurrencia y aislamiento de datos en una dependencia de
infraestructura.** Aquí no hay nada de IA. Es un bug clásico de reutilización de conexiones en un
*pool* bajo cancelación, y ese es justo el punto: el dato más sensible de un producto de IA —la
conversación— estaba protegido por la corrección de una librería de caché de propósito general que
nadie del equipo de producto había auditado.

**Lo que une a los cuatro:** el modelo de amenazas se dibujó alrededor del modelo, y el daño entró
por la infraestructura. Ningún *eval* de seguridad del LLM, ningún filtro de contenido y ninguna
alineación habrían evitado uno solo de estos cuatro incidentes.

---

### 3. Qué lo habría prevenido

Controles concretos, ordenados por relación coste/impacto. Todos existían y estaban disponibles antes
de cada incidente.

| # | Control | Habría evitado |
|---|---|---|
| 1 | **Prohibir `pickle` en la frontera de confianza:** cargar solo `safetensors` y rechazar formatos que ejecutan código al deserializar. | INC-019 |
| 2 | **Escaneo de secretos obligatorio** en pre-commit y en el lado del servidor, con revocación automática al detectar un token válido publicado. | INC-014 |
| 3 | **Tokens de grano fino, alcance mínimo y expiración corta**, en lugar de tokens de organización con permiso de escritura y vida indefinida. | INC-014, INC-022 |
| 4 | **Mirror interno de modelos**: nada se descarga del Hub directamente a producción; se promueve por un registro propio con checksum fijado y escaneo previo. | INC-019, INC-022 |
| 5 | **Cargar modelos no verificados en sandbox** (sin red, sin credenciales, contenedor efímero). Convierte una *reverse shell* en un contenedor muerto. | INC-019 |
| 6 | **Test de aislamiento bajo carga y cancelación** en la capa de caché: aserción de que la respuesta que recibe la sesión A nunca contiene datos de la sesión B, ejecutado con concurrencia y cancelaciones agresivas. | INC-011 |
| 7 | **Segmentar el secreto del dato:** los secretos de terceros en un gestor externo (KMS/Vault) y no en la plataforma de ejecución, de modo que comprometer la plataforma no comprometa las claves. | INC-022 |

---

### 4. Qué se lleva un analista de esto

1. **Al evaluar una startup de IA, el riesgo técnico interesante rara vez está en el modelo.** Las
   preguntas que discriminan son de cadena de suministro: ¿de dónde vienen los pesos que cargáis en
   producción?, ¿en qué formato?, ¿quién puede publicar en vuestro registro de modelos?, ¿qué pasa si
   se filtra el token de un becario?
2. **La velocidad del ecosistema es la vulnerabilidad.** Lo que hace atractivo al Hub —publicar y
   consumir modelos sin fricción— es exactamente el mecanismo que INC-014 e INC-019 explotan. No es
   un defecto corregible sin renunciar a parte de la propuesta de valor; es un *trade-off* que hay
   que ver declarado en el diseño del proveedor.
3. **La respuesta post-incidente es una señal medible de madurez.** OpenAI publicó un informe técnico
   con causa raíz y ventana temporal; Hugging Face publicó la brecha de Spaces y forzó rotación. Esa
   transparencia es un indicador de gobernanza mucho más fiable que cualquier declaración de
   principios sobre IA responsable.
4. **Estos cuatro son de severidad 3–4, no 5.** No murió nadie ni se arruinaron familias: en la
   escala de este dataset, eso lo reservan INC-004 y INC-008. Pero son los de mayor **riesgo
   sistémico latente**, porque comprometen dependencias compartidas por miles de proyectos aguas
   abajo.

---

*Fuentes primarias:*
[OpenAI, informe del incidente del 20 de marzo](https://openai.com/index/march-20-chatgpt-outage/) ·
[Lasso Security](https://www.lasso.security/blog/1500-huggingface-api-tokens-were-exposed-putting-meta-llama-bloom-pythia-and-openai-users-at-critical-risk) ·
[JFrog Security Research](https://jfrog.com/blog/data-scientists-targeted-by-malicious-hugging-face-ml-models-with-silent-backdoor/) ·
[Hugging Face, Space secrets disclosure](https://huggingface.co/blog/space-secrets-disclosure)
