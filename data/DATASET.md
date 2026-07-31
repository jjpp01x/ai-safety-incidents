## Metodología del dataset

23 incidentes públicos de sistemas de IA **en producción**, recopilados a mano entre 2015 y 2025.
No es un censo: es una muestra construida para que las cuatro categorías de fallo tengan masa
suficiente y para cubrir tanto el consumo masivo como el sector público, la movilidad, las finanzas
y la propia infraestructura del ecosistema de IA.

### Criterios de inclusión

Un incidente entra si cumple **las tres** condiciones:

1. **Sistema desplegado.** Fallos en producción o en pruebas con usuarios reales. Se excluyen
   resultados de *red teaming* de laboratorio y demos controladas.
2. **Fuente primaria o de referencia verificable.** Documento oficial de la empresa, informe de un
   regulador, resolución judicial, investigación de seguridad publicada o investigación periodística
   de medio con estándar editorial. La columna `evidencia` registra cuál de las cinco es, para poder
   leer el dataset sabiendo en qué se apoya.
3. **Consecuencia observable.** Daño a personas, pérdida económica, sanción, retirada del sistema o
   compromiso técnico confirmado. Se excluye la mera polémica.

### Taxonomía de modos de fallo

Cuatro categorías mutuamente excluyentes. Cuando un incidente encaja en dos, se clasifica por el
**fallo que hizo posible el daño**, no por el síntoma más visible.

| Tipo | Definición operativa | Ejemplo del dataset |
|---|---|---|
| **Contención** | El sistema actúa fuera de los límites que su operador había previsto: sin guardarraíles suficientes, con una autonomía mal calibrada o con un comportamiento emergente no anticipado. | Uber ATG (INC-004), Tay (INC-002) |
| **Sesgo** | Rendimiento sistemáticamente desigual entre grupos, con efecto material sobre derechos u oportunidades. | Toeslagenaffaire (INC-008), COMPAS (INC-003) |
| **Alucinación** | El sistema fabrica información y la presenta con la misma confianza que la verificada. | Mata v. Avianca (INC-013), MyCity (INC-020) |
| **Seguridad** | Compromiso de confidencialidad, integridad o disponibilidad, incluido el abuso adversario del propio modelo. | Tokens del Hub (INC-014), deepfake de Arup (INC-016) |

### Escala de severidad (1–5)

Mide el **daño materializado**, no la sofisticación técnica del fallo ni la notoriedad del caso.
Es una escala editorial: por eso está escrita, y por eso es discutible fila a fila.

| Nivel | Criterio | Ejemplo |
|---|---|---|
| **5** | Daño físico irreversible, o daño masivo y sostenido a derechos fundamentales. | Muerte de una peatona (INC-004); decenas de miles de familias arruinadas (INC-008) |
| **4** | Daño grave y demostrado sobre personas identificables, o compromiso crítico de infraestructura compartida. | Detención errónea (INC-006); 1.681 tokens con permiso de escritura sobre modelos de terceros (INC-014) |
| **3** | Pérdida económica o reputacional relevante, o fuga de datos confirmada de alcance acotado. | Cierre de Zillow Offers (INC-009); fuga de redis-py (INC-011) |
| **2** | Daño acotado y reversible, corregido con rapidez. | Reembolso de Air Canada (INC-018) |
| **1** | Sin daño material demostrado; valor como prueba de concepto de un fallo real. | Chatbot del concesionario (INC-015) |

### Esquema

| Columna | Tipo | Notas |
|---|---|---|
| `id` | texto | `INC-nnn`, único |
| `fecha` | `YYYY-MM-DD` | Fecha del hecho documentado; si el hecho se conoce por una resolución o informe posterior, la de ese documento |
| `empresa` | texto | Organización responsable del despliegue |
| `sistema` | texto | Sistema concreto, no la empresa entera |
| `tipo_fallo` | enum | `contencion` · `sesgo` · `alucinacion` · `seguridad` |
| `severidad` | entero 1–5 | Según la rúbrica anterior |
| `pais` | texto | Jurisdicción principal del impacto |
| `dominio` | texto | Sector de aplicación |
| `evidencia` | enum | `Oficial` · `Regulador` · `Judicial` · `Periodística` · `Investigación de seguridad` |
| `estado` | texto | `Mitigado` · `Revertido` · `Sistema retirado` · `Sancionado` · `En litigio` · `Sin remedio público` |
| `resumen` | texto | Una o dos frases: qué falló, no qué se dijo |
| `fuente` | texto | Nombre de la fuente |
| `url` | URL | Enlace directo al documento concreto, absoluto. Nunca la portada ni la raíz del dominio |
| `url_archivo` | URL \| vacío | Copia permanente en Internet Archive, tomada del snapshot más cercano *posterior* al incidente. La rellena `scripts/fetch_archives.py` |
| `detectable_dd` | enum | `si` · `parcial` · `no` — ver rúbrica abajo |
| `control_dd` | texto | El control concreto que lo habría anticipado |

### Detectabilidad en revisión previa (`detectable_dd`)

La pregunta: **¿habría anticipado este fallo una revisión técnica hecha antes del
despliegue, con los controles disponibles en ese momento?**

| Valor | Criterio |
| --- | --- |
| `si` | Un control estándar y disponible en la época lo habría revelado (evaluación desagregada, red-teaming, escaneo de secretos, verificación de citas). |
| `parcial` | La *clase* de riesgo era anticipable, pero no su forma concreta; o el fallo tenía un componente institucional u operativo fuera del alcance de una revisión técnica. |
| `no` | El fallo no es una propiedad del sistema evaluable en revisión: ataque externo sobre el proceso, o condición no conocible en el momento. |

**Esta es la única columna del dataset que es un juicio y no un hecho.** Por eso cada
fila lleva `control_dd`: nombrar el control concreto convierte el veredicto en algo que
quien lea el dataset puede rebatir. Un `si` sin control nombrado sería una opinión con
formato de dato.

**Sesgo declarado y no corregible:** el veredicto se emite conociendo el desenlace, que
es exactamente la información de la que carece quien hace la revisión previa. El
porcentaje resultante es un **techo optimista**, no una estimación de cuántos fallos se
habrían evitado de verdad.

### Lo que dice esta columna

Con el dataset actual (23 incidentes):

| Detectabilidad | Incidentes | % | Severidad media |
| --- | ---: | ---: | ---: |
| Sí | 16 | 70 % | 2.94 |
| Parcial | 6 | 26 % | 3.83 |
| No | 1 | 4 % | 4.00 |

Dos lecturas, ninguna evidente de antemano:

1. **Casi nada aquí era exótico.** El 96 % era total o parcialmente anticipable con
   controles que ya existían. El patrón dominante no es una tecnología que sorprende a
   sus creadores, sino un control conocido que no se aplicó.
2. **La severidad se mueve en dirección contraria a la previsibilidad** (2.94 → 3.83 →
   4.00). Lo previsible es más frecuente pero más leve; lo imprevisible es raro y caro.
   Con n=23 esto no es un resultado estadístico, pero sí una hipótesis con consecuencia
   práctica: los controles baratos recortan volumen, no cola.

El cruce por modo de fallo lo afina: **la alucinación es 100 % previsible** en esta
muestra (5 de 5), mientras que **seguridad es el modo menos previsible** (2 de 6 con un
`si` claro). Un revisor que solo controle alucinación está cubriendo la parte fácil.

El contrato se valida en cada carga (`aisid.data.validar`) y la aplicación **falla ruidosamente** si
el CSV lo incumple: una fila mal escrita no debe convertirse en una barra silenciosamente
equivocada. Los tests de `tests/test_data.py` cubren cada regla.

### Limitaciones — leer antes de citar cifras

- **Sesgo de muestreo occidental y anglófono.** Los incidentes documentados en inglés están
  sobrerrepresentados. Que un dominio tenga pocos incidentes aquí no significa que sea seguro:
  significa que se documenta menos.
- **Sesgo de visibilidad.** Un fallo llega al dataset cuando alguien lo publica. Los fallos internos
  detectados y corregidos sin publicidad —la mayoría— son invisibles por construcción.
- **La severidad es un juicio.** Está anclada a una rúbrica escrita para que sea auditable y
  discutible, no para que parezca objetiva.
- **N pequeño.** Con 23 filas, las tendencias temporales son ilustrativas, no inferencia estadística.
  El aumento de incidentes desde 2023 refleja tanto más despliegue de IA generativa como más
  atención mediática; el dataset no permite separar ambos efectos.

### Extender el dataset

Añade una fila al CSV siguiendo el esquema y ejecuta `pytest`. Si la fila incumple el contrato, la
suite falla antes de que el dashboard la muestre.

### Trazabilidad a prueba de link rot

Un dataset cuyo valor es la trazabilidad se degrada solo: los medios reorganizan sus URLs, las
entradas de blog se renombran y algunos dominios bloquean tráfico por región. Dos mecanismos lo
contienen:

- **`scripts/fetch_archives.py`** rellena `url_archivo` con el snapshot de Internet Archive más
  cercano *posterior* a la fecha del incidente — el que refleja la página tal como era cuando se
  citó, no como quedó después de una reescritura. Idempotente: solo rellena huecos.
- **`scripts/check_links.py`** recorre las fuentes sin dejar ninguna sin veredicto. Cuando el
  origen no se deja consultar —muro anti-bot de Reuters, NYT o Bloomberg; bloqueo regional de
  `dewr.gov.au`— verifica la copia archivada, que es exactamente para lo que está:

| Veredicto | Significado | Acción |
|---|---|---|
| `vivo` | El origen responde 200 | Ninguna |
| `copia` | El origen no se deja consultar, pero la copia archivada responde 200 | Ninguna: la cita es verificable |
| `ROTO` | Ni origen ni copia | Sustituir la fuente |

Sale con código distinto de 0 solo ante un `ROTO`, que es el único caso que obliga a tocar una fila.
**Último repaso: 23/23 verificadas** — 18 por el origen, 5 por copia archivada (INC-005, INC-010,
INC-011, INC-012, INC-023).

`sec.gov` merece una nota: rechaza los User-Agent de navegador y exige identificación con un contacto
entre paréntesis. El script lo contempla; pon el tuyo en `SEC_CONTACT=tu@correo.com` en lugar del
marcador de posición, porque la SEC pide un contacto real para poder avisarte si tu tráfico les
molesta.

Un test (`test_toda_fuente_es_verificable_a_diez_anos_vista`) exige que **cada fila sea verificable
dentro de diez años**: o tiene copia archivada, o cita un repositorio cuya permanencia es su función
—EDGAR de la SEC—, donde una copia externa no añadiría nada. Estado actual: 22 filas con copia
archivada y 1 en EDGAR.

**Sobre INC-023 (`dewr.gov.au`).** El dominio no responde desde ninguna red de pruebas —falla el
handshake, no devuelve 403—, pero Internet Archive conserva snapshots con código 200 hasta 2026: el
sitio está vivo y lo que hay es un bloqueo de acceso, no link rot. La fila apuntaba además a la raíz
del dominio, que incumple el criterio de "enlace directo al documento". Ahora apunta a la página del
*Targeted Compliance Framework assurance review*, verificada en el snapshot del 7 de octubre de 2025
—un día después del reembolso— donde constan Deloitte, la revisión independiente y el importe.

Referencia recomendada para ampliar la muestra: [AI Incident Database](https://incidentdatabase.ai/)
(> 3.000 informes) y el [AIAAIC Repository](https://www.aiaaic.org/).
