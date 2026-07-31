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
| `url` | URL | Enlace directo, absoluto |

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

Referencia recomendada para ampliar la muestra: [AI Incident Database](https://incidentdatabase.ai/)
(> 3.000 informes) y el [AIAAIC Repository](https://www.aiaaic.org/).
