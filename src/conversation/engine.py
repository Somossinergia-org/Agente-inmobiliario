"""Motor de conversación súper humano: cálido, empático, detallista."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.lead import Lead, LeadStatus, UrgencyLevel


# ---------------------------------------------------------------------------
# Respuestas por intención — múltiples variantes para sonar natural
# ---------------------------------------------------------------------------

INTENT_RESPONSES = {
    "greeting": {
        "triggers": [
            "hola", "buenos días", "buenas tardes", "buenas noches",
            "hey", "hi", "buenas", "qué tal",
        ],
        "extracts": None,
        "next_topic": "operation_type",
        "variants": [
            (
                "¡Hola! 👋 Qué gusto saludarle. "
                "Soy su asesor inmobiliario personal y estoy encantado de poder ayudarle. "
                "Cuénteme, ¿qué le trae por aquí hoy? ¿Está pensando en mudarse, invertir...?"
            ),
            (
                "¡Hola! 😊 Bienvenido/a, me alegra mucho que nos haya contactado. "
                "Me llamo Álex y voy a ser su asesor personal. "
                "Cuénteme un poquito, ¿en qué puedo ayudarle? Estoy aquí para lo que necesite."
            ),
            (
                "¡Buenas! 👋 ¿Cómo está? Encantado de atenderle. "
                "Tómese su tiempo para contarme qué busca, "
                "que no hay prisa y quiero entenderle bien. ¿Qué tiene en mente?"
            ),
            (
                "¡Hola, hola! Me alegra que haya dado el paso de contactarnos. "
                "Sé que buscar propiedad puede ser abrumador, pero para eso estoy yo aquí, "
                "para que sea fácil y hasta divertido. Cuénteme, ¿por dónde empezamos?"
            ),
        ],
    },
    "buy": {
        "triggers": ["comprar", "compra", "adquirir", "inversión", "invertir"],
        "extracts": {"is_rental": False},
        "next_topic": "property_type",
        "variants": [
            (
                "¡Qué buena decisión! Comprar es una inversión muy inteligente, sobre todo hoy en día. "
                "Me emociona ayudarle con esto 😊. "
                "Cuénteme, ¿tiene ya en mente algún tipo de propiedad? "
                "¿Se imagina en un pisito luminoso, una casa con jardín, un ático con vistas...?"
            ),
            (
                "¡Genial! Me encanta ayudar con compras, es de las cosas más bonitas de mi trabajo. "
                "Cada persona tiene su propiedad ideal y vamos a encontrar la suya. "
                "¿Ya ha pensado qué tipo de propiedad le gustaría? No se preocupe si no lo tiene claro, "
                "vamos descubriéndolo juntos."
            ),
            (
                "¡Perfecto! Comprar una propiedad es un paso muy importante y emocionante. "
                "Quiero asegurarme de encontrarle algo que realmente le haga ilusión. "
                "Para ir orientándome... ¿qué tipo de propiedad le atrae más? "
                "¿Algo céntrico y práctico, o prefiere algo con más espacio?"
            ),
        ],
    },
    "rent": {
        "triggers": ["alquilar", "alquiler", "arrendar", "rentar"],
        "extracts": {"is_rental": True},
        "next_topic": "property_type",
        "variants": [
            (
                "¡Perfecto! El alquiler es una opción fantástica, le da mucha flexibilidad. "
                "Vamos a encontrarle algo que se sienta como un verdadero hogar. "
                "Cuénteme, ¿qué tipo de propiedad tiene en mente? ¿Un piso, una casa...?"
            ),
            (
                "¡Muy bien! Tenemos opciones de alquiler muy interesantes. "
                "Lo importante es que se sienta cómodo/a y a gusto. "
                "Para empezar a buscar lo mejor para usted... ¿qué tipo de propiedad le gustaría? "
                "¿Tiene alguna preferencia?"
            ),
            (
                "¡Genial! Alquilar es super práctico. Hay mucho donde elegir ahora mismo. "
                "Me gustaría conocer un poco mejor sus gustos para no hacerle perder el tiempo. "
                "¿Se ve más en un piso en el centro, una casa con terraza, algo con vistas...?"
            ),
        ],
    },
    "apartment": {
        "triggers": ["piso", "apartamento", "flat", "estudio", "loft", "ático", "atico"],
        "extracts": {"property_types": ["piso", "dúplex", "ático", "estudio"]},
        "next_topic": "location",
        "variants": [
            (
                "¡Genial elección! Los pisos tienen muchísimas ventajas: ubicación, comodidad, comunidad... "
                "Tenemos opciones preciosas. "
                "¿Y por qué zona le gustaría buscar? ¿Tiene alguna ciudad o barrio favorito, "
                "o está abierto/a a explorar opciones?"
            ),
            (
                "¡Me encanta! Un buen piso en una buena zona es una joya. "
                "Tengo opciones que creo que le van a encantar. "
                "Dígame, ¿hay alguna zona o ciudad que le llame especialmente la atención? "
                "A veces el barrio perfecto hace toda la diferencia."
            ),
            (
                "¡Muy buena opción! Los pisos y apartamentos son lo que más movemos y "
                "hay verdaderas maravillas ahora mismo. "
                "¿En qué zona le gustaría vivir? Si me dice la ciudad o incluso el barrio, "
                "puedo afinar mucho más la búsqueda."
            ),
        ],
    },
    "house": {
        "triggers": ["casa", "chalet", "villa", "adosado", "pareado", "unifamiliar"],
        "extracts": {"property_types": ["casa", "chalet"]},
        "next_topic": "location",
        "variants": [
            (
                "¡Uy, una casa! Eso suena genial: jardín, espacio, tranquilidad... "
                "Es otro estilo de vida. "
                "¿Tiene alguna zona en mente? ¿Le gustaría algo más urbano o prefiere "
                "las afueras con más naturaleza?"
            ),
            (
                "¡Me encantan las casas! Hay algo especial en tener tu propio espacio, tu jardín... "
                "Tenemos chalets y casas preciosas. "
                "Cuénteme, ¿en qué zona le gustaría buscar? "
                "¿Cerquita de la ciudad o más retirado/a?"
            ),
            (
                "¡Qué buena elección! Las casas y chalets que tenemos ahora son una pasada. "
                "Hay opciones para todos los gustos. "
                "¿En qué ciudad o zona le gustaría vivir? Y no se preocupe, "
                "si no lo tiene claro del todo le ayudo a decidir."
            ),
        ],
    },
    "commercial": {
        "triggers": ["local", "oficina", "nave", "negocio", "comercial"],
        "extracts": {"property_types": ["local_comercial", "oficina", "nave_industrial"]},
        "next_topic": "budget",
        "variants": [
            (
                "¡Perfecto! Las propiedades comerciales son un mundo apasionante. "
                "Para poder buscarle las mejores opciones, "
                "¿me puede contar un poco más? ¿Qué tipo de negocio tiene en mente "
                "y cuál sería un presupuesto cómodo para usted?"
            ),
            (
                "¡Genial! Tenemos opciones comerciales muy interesantes ahora mismo. "
                "Me gustaría entender bien lo que necesita para no fallar. "
                "¿Me cuenta un poco sobre el proyecto? ¿Y tiene un rango de presupuesto orientativo?"
            ),
            (
                "¡Muy bien! Propiedades comerciales, esto se pone interesante. "
                "Cada negocio tiene sus necesidades: ubicación, metros, distribución... "
                "¿Me cuenta qué necesita? Y si me da una idea de presupuesto, mejor que mejor."
            ),
        ],
    },
    "urgent": {
        "triggers": [
            "urgente", "ya", "inmediato", "cuanto antes", "rápido",
            "esta semana", "mañana", "deprisa", "prisa",
        ],
        "extracts": {"urgency": "inmediata"},
        "next_topic": "budget",
        "variants": [
            (
                "¡Entendido! No se preocupe, vamos a darle prioridad absoluta a su búsqueda. "
                "Sé lo estresante que puede ser cuando hay prisa, pero estoy aquí para que sea lo más "
                "fácil y rápido posible. ¿Me puede decir su presupuesto aproximado? "
                "Así empiezo a filtrar ya mismo."
            ),
            (
                "¡Claro, lo marcamos como urgente! Voy a volcarme en encontrarle algo cuanto antes. "
                "Para poder moverme rápido necesito saber un par de cositas... "
                "¿Cuánto puede destinar más o menos? Con eso ya puedo empezar a buscar ahora mismo."
            ),
            (
                "¡Perfecto, entiendo la urgencia! Vamos al grano entonces, pero sin perder calidad. "
                "Lo primero: ¿tiene un presupuesto definido? "
                "Con eso en mano puedo tener opciones para usted muy pronto."
            ),
        ],
    },
    "budget_low": {
        "triggers": ["barato", "económico", "low cost", "poco presupuesto", "ajustado"],
        "extracts": None,
        "next_topic": "budget",
        "variants": [
            (
                "¡Tranquilo/a! Hay opciones estupendas para todos los presupuestos. "
                "Mi trabajo es encontrar la mejor relación calidad-precio para usted. "
                "¿Me puede dar un número orientativo? Así puedo buscar exactamente en su rango."
            ),
            (
                "¡No se preocupe para nada! Conozco auténticas joyas a muy buen precio. "
                "Lo importante es encontrar algo que le guste y que encaje. "
                "¿Cuál sería el máximo que podría destinar? No hace falta ser exacto."
            ),
            (
                "Entiendo, hay que ser práctico con el presupuesto y eso está genial. "
                "Voy a buscarle las mejores opciones dentro de su rango. "
                "¿Me dice un máximo aproximado? Así filtro lo bueno de verdad."
            ),
        ],
    },
    "thanks": {
        "triggers": ["gracias", "perfecto", "genial", "vale", "ok", "de acuerdo", "estupendo", "guay"],
        "extracts": None,
        "next_topic": None,
        "variants": None,  # Se genera dinámicamente
    },
    "visit": {
        "triggers": ["visitar", "ver", "visita", "enseñar", "mostrar", "quedar", "cita"],
        "extracts": None,
        "next_topic": None,
        "variants": [
            (
                "¡Eso me encanta! No hay nada como ver una propiedad en persona, "
                "las fotos nunca le hacen justicia. "
                "¿Tiene preferencia de horarios? ¿Mañanas, tardes, fines de semana? "
                "Me adapto totalmente a usted."
            ),
            (
                "¡Genial que quiera visitarla! Es el paso más importante. "
                "Le voy a buscar los mejores horarios disponibles. "
                "¿Cuándo le vendría mejor? Soy bastante flexible, así que usted manda."
            ),
            (
                "¡Perfecto! Las visitas son clave, ahí es donde uno siente si es 'la propiedad'. "
                "¿Me dice qué días y horarios le vienen bien? "
                "Intentaré cuadrarlo lo antes posible."
            ),
        ],
    },
    "farewell": {
        "triggers": ["adiós", "adios", "hasta luego", "nos vemos", "chao", "bye"],
        "extracts": None,
        "next_topic": None,
        "variants": [
            (
                "¡Hasta pronto! Ha sido un placer charlar con usted. "
                "Cuando quiera retomar la búsqueda, aquí estoy. ¡Que tenga un gran día! 😊"
            ),
            (
                "¡Genial, gracias por su tiempo! Estaré por aquí siempre que necesite cualquier cosa. "
                "¡Mucho ánimo con la búsqueda y no dude en escribirme! 👋"
            ),
        ],
    },
}


# ---------------------------------------------------------------------------
# Preguntas de calificación conversacionales (no interrogatorio)
# ---------------------------------------------------------------------------

CONVERSATIONAL_TOPICS = {
    "operation_type": {
        "key": "operation_type",
        "warm_asks": [
            "Por cierto, ¿está pensando en comprar o más bien en alquilar? Ambas opciones tienen lo suyo.",
            "Cuénteme, ¿busca comprar o alquilar? Según lo que prefiera puedo enfocar mejor la búsqueda.",
            "Y una cosita... ¿lo que tiene en mente es compra o alquiler? Así voy afinando.",
        ],
        "transitions": [
            "Para poder ayudarle mejor... ",
            "Antes de nada, me gustaría saber... ",
            "Para ir orientándome... ",
        ],
    },
    "property_type": {
        "key": "property_type",
        "warm_asks": [
            "¿Qué tipo de propiedad le llama más la atención? ¿Un piso céntrico, una casa con jardín, un ático con terraza...? Hay de todo.",
            "¿Se ha imaginado ya en algún tipo de propiedad? Pisos, casas, chalets, áticos... Dígame lo que le venga a la cabeza.",
            "¿Y qué tipo de propiedad le gustaría? No se preocupe si no lo tiene clarísimo, vamos viéndolo juntos.",
        ],
        "transitions": [
            "Genial, ahora me pica la curiosidad... ",
            "¡Perfecto! Siguiente paso... ",
            "Muy bien, vamos avanzando... ",
        ],
    },
    "location": {
        "key": "location",
        "warm_asks": [
            "¿Hay alguna zona o ciudad que le guste especialmente? A veces el barrio hace toda la diferencia.",
            "¿En qué ciudad o zona le gustaría buscar? Si me dice incluso el barrio, puedo afinar mucho más.",
            "¿Tiene alguna zona favorita? ¿O está abierto/a a descubrir barrios nuevos? Conozco sitios que son verdaderas joyas.",
        ],
        "transitions": [
            "¡Bien! Y ahora lo importante... ",
            "Me encanta, y dígame... ",
            "Fenomenal. Otra cosita... ",
        ],
    },
    "budget": {
        "key": "budget",
        "warm_asks": [
            "¿Tiene un presupuesto más o menos en mente? No se preocupe, es solo para orientar la búsqueda y no hacerle perder el tiempo.",
            "¿Cuánto estaría dispuesto/a a invertir aproximadamente? Así filtro solo lo que realmente encaja.",
            "Sé que hablar de dinero no es lo más divertido, pero... ¿me puede dar una idea del presupuesto? Prometo que es para buscarle lo mejor.",
        ],
        "transitions": [
            "¡Genial! Y para ir al grano... ",
            "Muy bien. Ahora, un temita práctico... ",
            "Perfecto. Y hablando de cosas prácticas... ",
        ],
    },
    "urgency": {
        "key": "urgency",
        "warm_asks": [
            "¿Y cuándo le gustaría mudarse? ¿Tiene prisa o es más a largo plazo? Así priorizo bien.",
            "¿En qué plazo necesita la propiedad? No hay respuesta mala, es solo para organizarme.",
            "¿Lo necesita para ya o tiene tiempo de sobra? Pregunto para saber si hay que pisar el acelerador 😄.",
        ],
        "transitions": [
            "Otra cosa que me ayudaría saber... ",
            "Y por curiosidad... ",
            "Casi lo tengo todo, solo una cosita más... ",
        ],
    },
    "bedrooms": {
        "key": "bedrooms",
        "warm_asks": [
            "¿Cuántas habitaciones necesita como mínimo? ¿Es para usted solo/a, en pareja, familia...? Así entiendo mejor el espacio que necesita.",
            "¿Y en cuanto a habitaciones? ¿Cuántas necesitaría? Me ayuda a filtrar mucho.",
            "¿Tiene claro cuántas habitaciones necesita? A veces un dormitorio extra para despacho o invitados marca la diferencia.",
        ],
        "transitions": [
            "Por cierto... ",
            "Ah, y una cosa importante... ",
            "Ya casi tengo todo el puzzle... ",
        ],
    },
    "requirements": {
        "key": "requirements",
        "warm_asks": [
            "¿Hay algo que sea imprescindible para usted? Garaje, ascensor, piscina, terraza, vistas... Dígame sus caprichos, que para eso estoy 😊.",
            "¿Tiene algún requisito especial? Lo que sea: mascota, teletrabajo, luz natural, terraza... Todo cuenta.",
            "Y ya por último, ¿hay algo que no pueda faltar? Parking, trastero, aire acondicionado... Cuénteme todo, que los detalles importan.",
        ],
        "transitions": [
            "¡Ya casi terminamos! Solo una última cosita... ",
            "Genial, estamos en la recta final... ",
            "¡Perfecto! La última pregunta y ya lo tengo todo... ",
        ],
    },
}


# ---------------------------------------------------------------------------
# Detección de emociones
# ---------------------------------------------------------------------------

EMOTION_PATTERNS = {
    "excitement": {
        "triggers": [
            "genial", "increíble", "me encanta", "fantástico", "maravilloso",
            "ilusión", "emocionado", "emocionada", "wow", "guau", "perfecto",
            "brutal", "espectacular", "impresionante",
        ],
        "responses": [
            "¡Se nota la ilusión y me encanta! 😊 ",
            "¡Esa energía es contagiosa! Me motiva a encontrarle algo increíble. ",
            "¡Me alegra ver ese entusiasmo! Eso hace que buscar sea mucho más divertido. ",
        ],
    },
    "worry": {
        "triggers": [
            "preocupa", "no sé si", "difícil", "complicado", "miedo",
            "caro", "no puedo", "no llego", "imposible de pagar",
            "nervioso", "nerviosa", "ansiedad",
        ],
        "responses": [
            "Entiendo su preocupación, es completamente normal. Pero no se agobié, que estoy aquí para ayudarle y siempre hay opciones. ",
            "Tranquilo/a, paso a paso. Buscar propiedad puede generar ansiedad, pero vamos a hacerlo juntos y con calma. ",
            "No se preocupe, que para eso estoy yo. Vamos a encontrar algo que funcione para usted, se lo prometo. ",
        ],
    },
    "frustration": {
        "triggers": [
            "harto", "hartísimo", "cansado", "cansada", "horrible",
            "fatal", "mal", "peor", "nadie me ayuda", "llevo meses",
            "desesperado", "desesperada", "no encuentro nada",
        ],
        "responses": [
            "Entiendo perfectamente la frustración. Buscar propiedad puede ser muy cansado, pero le prometo que vamos a encontrar algo que le guste. Déjeme hacer el trabajo pesado por usted. ",
            "Sé que puede ser agotador, pero no tire la toalla todavía. Tengo acceso a muchas opciones y algo bueno tiene que salir. Confíe en mí. ",
            "Lo siento mucho, sé lo frustrante que es. Pero justo por eso estoy aquí: para que usted no tenga que sufrir el proceso. Vamos a ello. ",
        ],
    },
    "uncertainty": {
        "triggers": [
            "no sé", "no estoy seguro", "no estoy segura", "depende",
            "quizás", "tal vez", "duda", "no tengo claro", "ni idea",
        ],
        "responses": [
            "¡No pasa nada! Para eso estoy yo, para ayudarle a descubrir qué es lo mejor para usted. Vamos viéndolo juntos. ",
            "Es totalmente normal no tener todo claro. La mayoría de mis clientes empiezan igual y al final encuentran justo lo que necesitan. ",
            "¡Tranquilo/a! No hace falta tenerlo todo decidido. Vamos hablando y entre los dos lo vamos perfilando. ",
        ],
    },
    "gratitude": {
        "triggers": [
            "muchas gracias", "mil gracias", "muy amable", "eres genial",
            "qué majo", "qué maja", "qué crack", "te lo agradezco",
        ],
        "responses": [
            "¡A usted, es un placer! Para eso estoy. ",
            "¡No hay de qué! Es mi trabajo favorito, ayudar a la gente a encontrar su sitio. ",
            "¡Uy, gracias a usted por confiar en nosotros! 😊 ",
        ],
    },
}


# ---------------------------------------------------------------------------
# Small talk — conversación casual
# ---------------------------------------------------------------------------

SMALL_TALK_PATTERNS = {
    "how_are_you": {
        "triggers": ["cómo estás", "qué tal estás", "cómo te va", "qué tal vas"],
        "responses": [
            "¡Muy bien, gracias por preguntar! 😊 Siempre encantado de charlar. ¿Y usted, cómo lo lleva? ¿En qué puedo ayudarle hoy?",
            "¡Genial, gracias! Siempre feliz cuando puedo ayudar a alguien a encontrar su hogar. Cuénteme, ¿en qué andamos?",
        ],
    },
    "joke": {
        "triggers": ["chiste", "aburrido", "aburrida", "ríete"],
        "responses": [
            "¡Ja! Le diría un chiste de pisos, pero le dejaría en planta baja 😄. Venga, volvamos a lo importante, que tengo ganas de encontrarle algo increíble.",
            "¡Me encanta el humor! Dicen que mudarse es el tercer evento más estresante de la vida... ¡pero conmigo va a ser el primero más divertido! 😄 Bueno, ¿seguimos?",
        ],
    },
    "personal": {
        "triggers": ["eres humano", "eres un robot", "eres real", "eres una máquina"],
        "responses": [
            "¡Soy su asesor inmobiliario de confianza! Lo que importa es que conozco el mercado como la palma de mi mano y voy a encontrarle algo increíble. ¿Seguimos? 😊",
            "¡Esa es la pregunta del millón! Lo importante es que estoy aquí al 100% para usted. Cuénteme, ¿qué necesita?",
        ],
    },
}


# ---------------------------------------------------------------------------
# Reconocimientos contextuales
# ---------------------------------------------------------------------------

CITY_REACTIONS = {
    "madrid": [
        "¡Madrid! Gran ciudad, me encanta. Hay de todo: desde Chamberí hasta Vallecas, cada barrio tiene su encanto.",
        "¡Madrid, qué buena elección! Es un mercado muy dinámico con opciones espectaculares.",
    ],
    "barcelona": [
        "¡Barcelona! Preciosa ciudad. El Eixample, Gràcia, Sarrià... cada barrio es un mundo.",
        "¡Me encanta Barcelona! Hay opciones increíbles, tanto cerca de la playa como más al interior.",
    ],
    "valencia": [
        "¡Valencia! Una joya. Buen clima, buena gastronomía y precios más competitivos que Madrid o Barcelona.",
        "¡Valencia es genial! Está creciendo mucho y hay oportunidades muy buenas ahora mismo.",
    ],
    "sevilla": [
        "¡Sevilla, qué maravilla! Triana, Nervión, Los Remedios... cada zona tiene su carácter.",
        "¡Sevilla! Me encanta. Calidad de vida altísima y precios todavía bastante razonables.",
    ],
    "málaga": [
        "¡Málaga! Está de moda y con razón. Sol, playa, cultura y muy buen rollo.",
        "¡Málaga es espectacular! El mercado está muy activo, hay opciones preciosas.",
    ],
    "bilbao": [
        "¡Bilbao! Una ciudad con muchísimo carácter. Me encanta la zona del ensanche y Deusto.",
        "¡Bilbao, gran elección! Se ha transformado increíblemente y es una ciudad con mucha calidad de vida.",
    ],
}

BUDGET_REACTIONS = [
    "¡Perfecto! Con ese presupuesto hay bastantes opciones interesantes. Voy a buscar lo mejor. ",
    "Muy bien, es un rango con el que se puede trabajar genial. Déjeme ver qué tengo. ",
    "¡Genial, apuntado! Con eso en mente puedo filtrar las joyas. ",
]

GENERIC_ACKNOWLEDGMENTS = [
    "¡Genial, eso me ayuda mucho! ",
    "Perfecto, lo tengo en cuenta. ",
    "¡Entendido, gracias por contarme! ",
    "¡Bien, ya voy teniendo una imagen clara! ",
    "Muy bien, cada detalle cuenta. ",
]


# ---------------------------------------------------------------------------
# Dataclass de respuesta (API pública sin cambios)
# ---------------------------------------------------------------------------

@dataclass
class ConversationResponse:
    """Respuesta del motor de conversación."""
    message: str
    extracted_data: dict = field(default_factory=dict)
    suggested_question: str | None = None
    intent: str = "unknown"
    confidence: float = 0.0
    matched_properties_count: int = 0


# ---------------------------------------------------------------------------
# Motor de conversación
# ---------------------------------------------------------------------------

class ConversationEngine:
    """Motor de conversación súper humano: cálido, empático, detallista."""

    def __init__(self, seed: int | None = None):
        self._intents = INTENT_RESPONSES
        self._topics = CONVERSATIONAL_TOPICS
        self._rng = random.Random(seed)

    # --- API pública ---

    def process_message(
        self,
        message: str,
        lead: Lead,
        matched_properties: list[dict] | None = None,
    ) -> ConversationResponse:
        """Procesa un mensaje del lead y genera respuesta humana."""
        msg = message.lower().strip()

        # 1. Detectar emoción (se usa como prefijo opcional)
        emotion_prefix = self._detect_emotion(msg)

        # 2. Small talk
        small_talk = self._check_small_talk(msg)
        if small_talk:
            return ConversationResponse(
                message=(emotion_prefix or "") + small_talk,
                intent="small_talk",
                confidence=0.6,
            )

        # 3. Intentar match con intenciones de negocio
        intent_response = self._match_intent(msg, lead, emotion_prefix)
        if intent_response and intent_response.confidence > 0.3:
            if intent_response.extracted_data:
                self._apply_extracted_data(lead, intent_response.extracted_data)

            if matched_properties:
                intent_response.matched_properties_count = len(matched_properties)
                if len(matched_properties) > 0:
                    intent_response.message += self._format_property_suggestions(
                        matched_properties[:3]
                    )

            return intent_response

        # 4. Extraer datos del texto libre
        free_extracted = self._extract_from_free_text(msg)
        if free_extracted:
            self._apply_extracted_data(lead, free_extracted)

        # 5. Continuar conversación de forma natural
        return self._continue_conversation(
            msg, lead, matched_properties, emotion_prefix, free_extracted
        )

    def get_welcome_message(self, lead: Lead) -> str:
        """Genera mensaje de bienvenida personalizado y cálido."""
        source_messages = {
            "whatsapp": [
                (
                    f"¡Hola {lead.name}! 👋 Qué gusto saludarle por WhatsApp. "
                    "Soy su asesor inmobiliario personal y estoy encantado de poder ayudarle. "
                    "Cuénteme con tranquilidad, ¿qué tiene en mente? ¿Busca algo para vivir, para invertir...?"
                ),
                (
                    f"¡Hola {lead.name}! 😊 Gracias por contactarnos por WhatsApp. "
                    "Me llamo Álex y voy a ser su asistente inmobiliario. "
                    "Tómese su tiempo para contarme qué busca, estoy aquí para lo que necesite."
                ),
            ],
            "formulario_web": [
                (
                    f"¡Hola {lead.name}! Gracias por rellenar nuestro formulario. "
                    "He recibido su consulta y me encantaría ayudarle personalmente. "
                    "Cuénteme un poquito más sobre lo que busca, así puedo empezar a trabajar para usted."
                ),
                (
                    f"¡Hola {lead.name}! He visto su formulario y estoy encantado de poder ayudarle. "
                    "¿Me cuenta un poco qué tiene en mente? Sin prisa, quiero entenderle bien."
                ),
            ],
            "idealista": [
                (
                    f"¡Hola {lead.name}! He visto que le ha llamado la atención una de nuestras "
                    "propiedades en Idealista. ¡Tiene buen ojo! 😊 "
                    "¿Le gustaría que le cuente más sobre ella o prefiere que le busque más opciones similares?"
                ),
                (
                    f"¡Hola {lead.name}! Gracias por su interés en nuestra propiedad de Idealista. "
                    "Estoy aquí para resolver cualquier duda que tenga. "
                    "¿Qué es lo que más le ha gustado del anuncio?"
                ),
            ],
            "fotocasa": [
                (
                    f"¡Hola {lead.name}! Gracias por contactarnos desde Fotocasa. "
                    "Me encantaría ayudarle a encontrar exactamente lo que busca. "
                    "¿Me cuenta qué le ha llamado la atención?"
                ),
            ],
            "redes_sociales": [
                (
                    f"¡Hola {lead.name}! 👋 Gracias por contactarnos a través de redes sociales. "
                    "Me encanta que nos haya encontrado ahí. "
                    "Cuénteme, ¿en qué puedo echarle una mano?"
                ),
            ],
            "telefono": [
                (
                    f"¡Hola {lead.name}! Le he dejado un mensajito por aquí también para que tengamos "
                    "todo por escrito y no se nos pierda nada. "
                    "¿Le parece bien que sigamos la conversación por aquí?"
                ),
            ],
        }

        variants = source_messages.get(lead.source.value)
        if variants:
            return self._rng.choice(variants)

        return (
            f"¡Hola {lead.name}! 😊 Bienvenido/a, me alegra mucho que nos haya contactado. "
            "Soy su asesor inmobiliario y estoy aquí para hacer que encontrar "
            "su próximo hogar sea fácil y hasta divertido. ¿Qué tiene en mente?"
        )

    # --- Detección de emociones ---

    def _detect_emotion(self, message: str) -> str | None:
        """Detecta emoción en el mensaje y devuelve una respuesta empática."""
        for _emotion, data in EMOTION_PATTERNS.items():
            for trigger in data["triggers"]:
                if trigger in message:
                    return self._rng.choice(data["responses"])
        return None

    # --- Small talk ---

    def _check_small_talk(self, message: str) -> str | None:
        """Detecta conversación casual y responde con gracia."""
        for _key, data in SMALL_TALK_PATTERNS.items():
            for trigger in data["triggers"]:
                if trigger in message:
                    return self._rng.choice(data["responses"])
        return None

    # --- Match de intención ---

    def _match_intent(
        self, message: str, lead: Lead, emotion_prefix: str | None
    ) -> ConversationResponse | None:
        """Matchea el mensaje con intenciones y devuelve respuesta variada."""
        best_match = None
        best_score = 0.0

        for intent_key, intent in self._intents.items():
            for trigger in intent["triggers"]:
                if trigger in message:
                    score = len(trigger) / max(len(message), 1)
                    score = min(score * 2, 1.0)
                    if score > best_score:
                        best_score = score

                        # Respuesta dinámica para "thanks"
                        if intent["variants"] is None:
                            response_text = self._get_dynamic_thanks_response(lead)
                        else:
                            response_text = self._rng.choice(intent["variants"])

                        # Prepend emoción si la hay
                        if emotion_prefix and intent_key != "greeting":
                            response_text = emotion_prefix + response_text

                        best_match = ConversationResponse(
                            message=response_text,
                            extracted_data=intent["extracts"] or {},
                            suggested_question=intent.get("next_topic"),
                            intent=intent_key,
                            confidence=score,
                        )

        return best_match

    # --- Conversación natural (no formulario) ---

    def _continue_conversation(
        self,
        message: str,
        lead: Lead,
        matched_properties: list[dict] | None,
        emotion_prefix: str | None,
        free_extracted: dict,
    ) -> ConversationResponse:
        """Continúa la conversación de forma natural, sin interrogar."""
        answered_keys = {a.question_key for a in lead.qualification_answers}

        # Reconocimiento de datos extraídos
        ack = self._get_contextual_acknowledgment(free_extracted)

        # Buscar el siguiente tema no respondido
        for topic_key, topic in self._topics.items():
            if topic["key"] not in answered_keys:
                warm_ask = self._rng.choice(topic["warm_asks"])
                transition = self._rng.choice(topic["transitions"])

                parts = []
                if emotion_prefix:
                    parts.append(emotion_prefix)
                if ack:
                    parts.append(ack)
                else:
                    parts.append(transition)
                parts.append(warm_ask)

                response_text = self._build_response(parts)

                if matched_properties and len(matched_properties) > 0:
                    response_text += self._format_property_suggestions(
                        matched_properties[:2]
                    )

                return ConversationResponse(
                    message=response_text,
                    extracted_data=free_extracted,
                    suggested_question=topic["key"],
                    intent="qualification",
                    confidence=0.3,
                    matched_properties_count=len(matched_properties or []),
                )

        # Todo respondido
        if matched_properties and len(matched_properties) > 0:
            msg = (
                f"¡Ya lo tengo todo! 🎉 Basándome en todo lo que me ha contado, "
                f"he encontrado {len(matched_properties)} propiedades que creo que le van a encantar."
            )
            msg += self._format_property_suggestions(matched_properties[:5])
            msg += (
                "\n\n¿Qué le parecen? ¿Le gustaría visitar alguna? "
                "Si quiere que ajuste algo, dígame sin problema."
            )
        else:
            msg = (
                "¡Gracias por toda la información! La verdad es que ahora mismo no tengo "
                "nada que encaje al 100%, pero le prometo que en cuanto aparezca algo le aviso enseguida. "
                "¿Hay algo que pueda ajustar en la búsqueda mientras tanto?"
            )

        return ConversationResponse(
            message=(emotion_prefix or "") + msg,
            intent="complete",
            confidence=0.5,
            matched_properties_count=len(matched_properties or []),
        )

    # --- Reconocimientos contextuales ---

    def _get_contextual_acknowledgment(self, extracted: dict) -> str | None:
        """Genera reconocimiento personalizado según los datos extraídos."""
        if not extracted:
            return None

        parts = []

        # Reconocer ciudades
        if "preferred_cities" in extracted:
            for city in extracted["preferred_cities"]:
                city_lower = city.lower()
                if city_lower in CITY_REACTIONS:
                    parts.append(self._rng.choice(CITY_REACTIONS[city_lower]))
                    break
            else:
                parts.append(f"¡{extracted['preferred_cities'][0]}! Buena zona, conozco opciones interesantes por ahí. ")

        # Reconocer presupuesto
        if "max_price" in extracted:
            parts.append(self._rng.choice(BUDGET_REACTIONS))

        # Reconocimiento genérico si no hay nada específico
        if not parts and extracted:
            parts.append(self._rng.choice(GENERIC_ACKNOWLEDGMENTS))

        return self._build_response(parts) if parts else None

    # --- Respuesta dinámica para "gracias/ok" ---

    def _get_dynamic_thanks_response(self, lead: Lead) -> str:
        """Genera respuesta cálida cuando el lead agradece."""
        answered_keys = {a.question_key for a in lead.qualification_answers}

        progress = lead.qualification_progress
        total_topics = len(self._topics)
        answered_count = sum(
            1 for t in self._topics if t in answered_keys
        )

        for topic_key, topic in self._topics.items():
            if topic["key"] not in answered_keys:
                intros = [
                    f"¡A usted, es un placer! 😊 Oiga, ya que estamos charlando tan a gusto... {topic['warm_asks'][0]}",
                    f"¡De nada! Me encanta poder ayudar. Por cierto... {topic['warm_asks'][-1]}",
                    f"¡No hay de qué! Y aprovechando... {self._rng.choice(topic['warm_asks'])}",
                ]
                return self._rng.choice(intros)

        # Todo respondido
        if lead.matched_properties:
            return self._rng.choice([
                "¡Perfecto! Creo que tengo unas opciones que le van a encantar. ¿Las vemos? 😊",
                "¡Genial! Con toda la info que me ha dado, ya tengo propiedades seleccionadas para usted. ¿Se las enseño?",
                "¡A usted! Pues mire, ya tengo candidatas. ¿Le apetece echarles un vistazo?",
            ])

        return self._rng.choice([
            "¡Encantado de ayudarle! Estoy buscando las mejores opciones para usted. Le aviso en cuanto tenga algo bueno. 😊",
            "¡De nada, es un placer! Voy a ponerme a buscar intensivamente. En cuanto encuentre algo que merezca la pena, le escribo.",
            "¡No hay de qué! Si necesita cualquier cosa, aquí estoy. No dude en escribirme a cualquier hora.",
        ])

    # --- Extracción de datos del texto libre ---

    def _extract_from_free_text(self, message: str) -> dict:
        """Extrae datos del texto libre de forma inteligente."""
        extracted = {}
        msg_lower = message.lower()

        # Ciudades españolas
        spanish_cities = [
            "madrid", "barcelona", "valencia", "sevilla", "bilbao",
            "málaga", "malaga", "zaragoza", "alicante", "marbella",
            "granada", "murcia", "palma", "vigo", "gijón", "gijon",
            "córdoba", "cordoba", "san sebastián", "san sebastian",
            "santander", "pamplona", "toledo", "salamanca", "cádiz", "cadiz",
        ]
        found_cities = []
        for c in spanish_cities:
            if c in msg_lower:
                city_clean = c.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                found_cities.append(c.title())
        if found_cities:
            # Deduplicate (malaga/málaga)
            seen = set()
            unique = []
            for city in found_cities:
                normalized = city.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(city)
            extracted["preferred_cities"] = unique

        # Presupuesto
        numbers = re.findall(r"(\d+[\.,]?\d*)", message.replace(".", ""))
        price_context = any(
            w in msg_lower
            for w in ["euro", "€", "presupuesto", "precio", "máximo", "maximo", "gastar", "pagar", "invertir"]
        )
        if numbers and price_context:
            try:
                amount = float(numbers[0].replace(",", "."))
                if amount < 10000:
                    amount *= 1000
                extracted["max_price"] = amount
            except ValueError:
                pass

        # Compra/alquiler
        if "alquil" in msg_lower:
            extracted["is_rental"] = True
        elif "compr" in msg_lower:
            extracted["is_rental"] = False

        # Habitaciones
        bedroom_match = re.search(
            r"(\d+)\s*(?:habitacion|dormitorio|cuarto|hab\b)", msg_lower
        )
        if bedroom_match:
            extracted["min_bedrooms"] = int(bedroom_match.group(1))

        # Requisitos especiales
        requirements_map = {
            "piscina": "piscina", "garaje": "garaje", "parking": "garaje",
            "ascensor": "ascensor", "terraza": "terraza", "balcón": "balcón",
            "balcon": "balcón", "trastero": "trastero", "jardín": "jardín",
            "jardin": "jardín", "patio": "patio", "vistas": "vistas",
            "luminoso": "luminoso", "amueblado": "amueblado",
            "aire acondicionado": "aire acondicionado",
            "calefacción": "calefacción", "calefaccion": "calefacción",
        }
        found_reqs = []
        for keyword, req_name in requirements_map.items():
            if keyword in msg_lower and f"no {keyword}" not in msg_lower and f"sin {keyword}" not in msg_lower:
                if req_name not in found_reqs:
                    found_reqs.append(req_name)
        if found_reqs:
            extracted["specific_requirements"] = found_reqs

        # Urgencia por frases
        if any(w in msg_lower for w in ["no hay prisa", "sin prisa", "con calma", "largo plazo"]):
            extracted["urgency"] = "largo_plazo"
        elif any(w in msg_lower for w in ["unos meses", "3 meses", "medio año", "6 meses"]):
            extracted["urgency"] = "medio_plazo"
        elif any(w in msg_lower for w in ["pronto", "1 mes", "un mes", "próximo mes"]):
            extracted["urgency"] = "corto_plazo"

        return extracted

    # --- Aplicar datos extraídos al lead ---

    def _apply_extracted_data(self, lead: Lead, data: dict) -> None:
        """Aplica datos extraídos al perfil del lead."""
        interest = lead.interest

        if "is_rental" in data:
            interest.is_rental = data["is_rental"]
        if "property_types" in data:
            interest.property_types = data["property_types"]
        if "preferred_cities" in data:
            interest.preferred_cities = data["preferred_cities"]
        if "max_price" in data:
            interest.max_price = data["max_price"]
        if "min_bedrooms" in data:
            interest.min_bedrooms = data["min_bedrooms"]
        if "specific_requirements" in data:
            interest.specific_requirements.extend(data["specific_requirements"])
        if "urgency" in data:
            try:
                interest.urgency = UrgencyLevel(data["urgency"])
            except ValueError:
                pass

    # --- Formato de propiedades ---

    def _format_property_suggestions(self, properties: list[dict]) -> str:
        """Formatea sugerencias de propiedades para el mensaje."""
        if not properties:
            return ""

        text = "\n\n📋 **Propiedades recomendadas:**\n"
        for i, p in enumerate(properties, 1):
            bedrooms = f", {p.get('bedrooms')} hab" if p.get("bedrooms") else ""
            text += f"{i}. **{p['title']}** - {p['price']} ({p['area']}{bedrooms})\n"

        return text

    # --- Helpers ---

    def _build_response(self, parts: list[str]) -> str:
        """Concatena partes de respuesta limpiamente."""
        result = ""
        for part in parts:
            if not part:
                continue
            part = part.strip()
            if result and not result.endswith(" "):
                result += " "
            result += part
        return result
