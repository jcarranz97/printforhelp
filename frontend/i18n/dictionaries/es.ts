/** Spanish message catalog. This object's shape defines `Dictionary`. */

export const es = {
  nav: {
    home: "Inicio",
    centers: "Centros",
    requests: "Peticiones",
    parts: "Piezas",
    supplies: "Insumos",
    myContributions: "Mis aportes",
    about: "Nosotros",
    users: "Usuarios",
    notices: "Avisos",
    ariaLabel: "Navegación principal",
  },
  social: {
    githubAriaLabel: "PrintForHelp en GitHub",
    discordAriaLabel: "Únete a nuestro Discord",
  },
  header: {
    greeting: "Hola,",
    makerGreeting: "Hola, Maker",
    logout: "Cerrar sesión",
    login: "Iniciar sesión",
    localeAriaLabel: "Cambiar idioma",
    localeMenuHeading: "Elige un idioma",
    themeAriaLabel: "Cambiar tema",
    themeLight: "Claro",
    themeDark: "Oscuro",
    themeSystem: "Sistema",
  },
  makerPrompt: {
    title: "¡Bienvenido/a!",
    question:
      "¿Imprimes en 3D para ayudar? Identificarte como Maker personaliza tu " +
      "experiencia.",
    yes: "Sí, soy Maker",
    no: "No por ahora",
    later: "Preguntar luego",
  },
  localePrompt: {
    title: "Idioma",
    description: "Detectamos tu idioma automáticamente. ¿Prefieres cambiarlo?",
  },
  description: {
    showMore: "Ver más",
    showLess: "Ver menos",
  },
  landing: {
    eyebrow: "Comunidad 3D",
    title: "PrintForHelp",
    subtitle:
      "Conectamos a quienes imprimen en 3D con quienes necesitan piezas, " +
      "empezando por férulas para los afectados por el terremoto en Venezuela.",
    howItWorks: "¿Cómo funciona?",
    wantToHelp: "Quiero ayudar",
    comingSoon: "Próximamente",
    featuresAriaLabel: "Funciones principales",
    announcementsAriaLabel: "Comunicados de la comunidad",
    announcement: {
      tag: "Comunicado oficial",
      priority: "Importante",
      permalinkLabel: "Copiar enlace a este comunicado",
      publishedLabel: "Publicado:",
      title: "Estándares de impresión para las férulas de Venezuela",
      summary:
        "Algunas piezas se están imprimiendo sin seguir los estándares " +
        "recomendados. Para asegurar que cada férula pueda usarse de " +
        "verdad, sigue estas pautas de material y de impresión.",
      materialsHeading: "Materiales a usar",
      materialsUse: [
        {
          label: "PLA",
          value: "Normal, Tough, + o variaciones, Matte, Translúcido",
        },
        { label: "PETG", value: "Normal, HF, Translúcido" },
      ],
      avoidHeading: "Evita filamentos cosméticos o con aditivos",
      materialsAvoid: [
        {
          label: "PLA",
          value:
            "CF, GF, HT, Madera, Fluorescente, Fosforescente, Silk, " +
            "Metal, Granito",
        },
        { label: "PETG", value: "CF, GF" },
      ],
      settingsHeading: "Ajustes de impresión",
      settings: [
        { label: "Diámetro de boquilla", value: "Mínimo 0.4 mm" },
        { label: "Grosor de capa", value: "Lo más grueso posible" },
        { label: "Paredes", value: "2 mínimo o sólido" },
        { label: "Relleno", value: "15% Cross Hatch o sólido" },
      ],
    },
    centersTitle: "Centros de acopio",
    centersDescription:
      "Directorio de puntos de entrega donde llevar tus piezas impresas para " +
      "que lleguen a quien las necesita.",
    requestsTitle: "Peticiones de piezas",
    requestsDescription:
      "Quien necesita una férula u otra pieza puede solicitarla aquí, con " +
      "detalles y urgencia.",
    printingTitle: "¿Qué estás imprimiendo?",
    printingDescription:
      "Reporta lo que tienes en cola para que la comunidad no duplique trabajo " +
      "y cubra mejor la demanda.",
    howItWorksHeading: "¿Cómo funciona?",
    howItWorksIntro:
      "PrintForHelp conecta a quienes necesitan piezas impresas en 3D con " +
      "quienes tienen una impresora y quieren ayudar. Así fluye el proceso:",
    step1Title: "1. Alguien publica una petición",
    step1Body:
      "Una persona u organización crea una campaña (por ejemplo «Férulas para " +
      "Venezuela») y enumera las piezas y cantidades que se necesitan.",
    step2Title: "2. Los makers se comprometen a imprimir",
    step2Body:
      "Quienes tienen una impresora 3D exploran las peticiones, eligen cuántas " +
      "piezas pueden imprimir y registran su compromiso. El avance se ve en " +
      "tiempo real.",
    step3Title: "3. Entrega y reparto",
    step3Body:
      "Las piezas impresas se llevan a un centro de acopio, que las reúne y " +
      "las envía a donde más se necesitan.",
    help: {
      heading: "Quiero ayudar",
      intro:
        "Gracias por sumarte al esfuerzo internacional de makers que apoya " +
        "la respuesta al terremoto en Venezuela. Esta página te ayuda a " +
        "unirte rápido a los esfuerzos de ayuda que ya están en marcha.",
      quakeNote:
        "El 24 de junio, alrededor de las 6:30 p. m. (hora local), Venezuela " +
        "fue sacudida por dos terremotos de magnitud 7.1 y 7.5, con apenas " +
        "39 segundos de diferencia y más de tres minutos de duración " +
        "combinada.",

      stepsHeading: "Cómo ayudar",
      stepsIntro:
        "Si tienes una impresora 3D, así puedes empezar a aportar hoy mismo:",

      printTitle: "1. Elige qué imprimir",
      printBody:
        "Todos los archivos aprobados se necesitan. Empieza por las piezas " +
        "marcadas como alta prioridad y, si buscas algo específico, explora " +
        "por etiquetas:",
      printTags: [
        { label: "Niños", href: "/parts?tag=Children" },
        { label: "Mascotas", href: "/parts?tag=mascotas" },
      ],
      printCaution:
        "Las piezas con la etiqueta «⚠️ Imprimir solo si se solicita» se " +
        "imprimen únicamente cuando alguien las pide; no las imprimas por " +
        "adelantado.",
      printCautionCta: "Ver estas piezas",
      printCautionHref:
        "/parts?tag=%E2%9A%A0%EF%B8%8F+Imprimir+solo+si+se+solicita",
      printCta: "Ver piezas de alta prioridad",
      printCtaHref: "/parts?tag=High+Priority",

      qualityTitle: "2. Imprime lo que puedas",
      qualityBody:
        "Todos los archivos aprobados se necesitan. Sigue los estándares de " +
        "material y de impresión para que cada férula pueda usarse de verdad.",
      qualityCta: "Ver estándares de impresión",

      packTitle: "3. Empaca tus impresiones",
      packBody: "Antes de entregar, asegúrate de que cada pieza:",
      packChecklist: [
        "Esté limpia y, cuando sea posible, embolsada individualmente.",
        "Incluya un identificador que indique qué es la pieza.",
        "Incluya instrucciones impresas cuando envíes férulas.",
      ],
      packNote:
        "Cada pieza incluye sus instrucciones y su etiqueta imprimible en su " +
        "propia página: imprime la etiqueta, pégala a la pieza e inclúyela en " +
        "el paquete.",
      packAllCta: "Ver todas las piezas",

      deliverTitle: "4. Entrega o envía tus impresiones",
      deliverBody:
        "Los puntos de entrega se están recopilando en varias plataformas. " +
        "Busca un centro cerca de ti. Si no encuentras uno, revisa los tres " +
        "mapas y pregunta en los grupos de la comunidad: se agregan nuevos " +
        "centros cada día. Estamos trabajando activamente para unificar la " +
        "información de los puntos de entrega entre plataformas.",
      deliverCentersCta: "Ver centros de acopio",
      mapUshahidiLabel: "Mapa Ushahidi Venezuela",
      mapDisainLabel: "Mapa Disain",

      noPrinterTitle: "¿No tienes impresora?",
      noPrinterBody: "También puedes ayudar. Se necesitan voluntarios para:",
      noPrinterList: [
        "Organizar colectas locales",
        "Coordinar logística",
        "Traducir información",
        "Difundir y crear conciencia",
        "Donar insumos o fondos",
      ],
      noPrinterCta: "Únete a la comunidad",

      aboutTitle: "Sobre este esfuerzo",
      aboutBody:
        "Makers de todo el mundo se han unido para apoyar a Venezuela. Las " +
        "primeras impresiones médicas ampliamente adoptadas fueron las " +
        "férulas diseñadas por @ostec3d, que siguen siendo urgentemente " +
        "necesarias. A medida que cambian las necesidades en el terreno, se " +
        "agregan nuevos archivos y recursos aprobados. Como es una emergencia " +
        "en evolución, la información y las prioridades pueden cambiar rápido: " +
        "vuelve con frecuencia para ver novedades.",

      communityHeading: "Ayuda y comunidad",
      communityIntro:
        "Únete a la comunidad si tienes preguntas, necesitas ayuda eligiendo " +
        "archivos o quieres coordinar donaciones.",
      whatsappEsTitle: "Grupo de WhatsApp (Español)",
      whatsappEsBody:
        "Coordina con makers y centros de habla hispana en tiempo real.",
      whatsappEnTitle: "Grupo de WhatsApp (English)",
      whatsappEnBody:
        "Conéctate con la comunidad internacional de makers en inglés.",
      discordTitle: "Discord (English)",
      discordBody:
        "Conversaciones, soporte y coordinación para la comunidad en inglés.",
      communityJoinCta: "Unirme",
    },
    footer:
      "PrintForHelp · Proyecto comunitario sin fines de lucro · MIT License",
  },
  login: {
    title: "Iniciar sesión",
    description: "Inicia sesión para coordinar la ayuda.",
    noAccountPrompt: "¿No tienes cuenta?",
    registerLink: "Regístrate",
    usernameLabel: "Email o usuario",
    usernamePlaceholder: "tu@email.com",
    passwordLabel: "Contraseña",
    passwordPlaceholder: "Tu contraseña",
    submit: "Iniciar sesión",
    submitting: "Entrando…",
    errorMissing: "Ingresa tu email o usuario y tu contraseña.",
    errorInactive: "Esta cuenta está inactiva.",
    errorInvalid: "Email/usuario o contraseña incorrectos.",
    errorGeneric: "No se pudo iniciar sesión. Inténtalo de nuevo.",
  },
  register: {
    title: "Crear cuenta",
    description: "Regístrate para ayudar a coordinar la ayuda.",
    haveAccountPrompt: "¿Ya tienes cuenta?",
    loginLink: "Inicia sesión",
    nameLabel: "Nombre",
    namePlaceholder: "Tu nombre",
    usernameLabel: "Usuario",
    usernamePlaceholder: "Tu usuario",
    emailLabel: "Email",
    emailPlaceholder: "tu@email.com",
    passwordLabel: "Contraseña",
    passwordPlaceholder: "Mín. 8, con una letra y un número",
    submit: "Crear cuenta",
    submitting: "Creando cuenta…",
    errorRequired: "Este campo es obligatorio.",
    errorUsernameTaken: "Ese usuario ya está en uso.",
    errorEmailTaken: "Ya existe una cuenta con ese email.",
    errorInvalidEmail: "Ingresa un email válido.",
    errorWeakPassword:
      "La contraseña debe tener al menos 8 caracteres, con una letra y un número.",
    errorGeneric: "No se pudo crear la cuenta. Inténtalo de nuevo.",
  },
  about: {
    title: "Sobre nosotros",
    intro:
      "PrintForHelp es una plataforma comunitaria sin fines de lucro que " +
      "conecta a quienes imprimen en 3D con quienes necesitan piezas de ayuda " +
      "humanitaria.",
    missionTitle: "Nuestra misión",
    missionTagline: "Coordinar la ayuda de forma abierta.",
    missionBody:
      "Centralizamos la información de centros de acopio, peticiones de piezas " +
      "y producción en curso, y la ponemos a disposición de todos, en " +
      "cualquier lugar, para que la comunidad pueda coordinarse y ayudar donde " +
      "más se necesita.",
    focusTitle: "Enfoque inicial",
    focusTagline: "Férulas para Venezuela.",
    focusBody:
      "Comenzamos coordinando la impresión de férulas médicas para las personas " +
      "afectadas por el terremoto de junio de 2026 en Venezuela, con la mira " +
      "puesta en convertirnos en un hub general de ayuda impresa en 3D.",
    helpNote:
      "¿Quieres ayudar? Por ahora las cuentas las crea un administrador. Pronto " +
      "habilitaremos el registro abierto para makers y organizaciones.",
    contributeTitle: "Cómo contribuir",
  },
  contribute: {
    title: "Contribuir",
    intro:
      "PrintForHelp es un proyecto comunitario de código abierto. Toda ayuda " +
      "es bienvenida, ya sea escribiendo código, reportando problemas o " +
      "difundiendo el proyecto.",
    repoTitle: "Código abierto",
    repoBody:
      "El código vive en GitHub bajo licencia MIT. Clónalo, revísalo y envía " +
      "tus mejoras mediante un pull request.",
    repoCta: "Ver en GitHub",
    apiTitle: "API abierta",
    apiBody:
      "PrintForHelp funciona sobre un backend hecho con FastAPI, y su API está " +
      "abierta para que otras personas desarrolladoras construyan sobre ella y " +
      "la contribución sea aún mayor. La idea siempre es compartir la " +
      "información de quienes necesitan ayuda: muchos endpoints son públicos y " +
      "no requieren autenticación, mientras que otros sí la necesitan. La API " +
      "está disponible en {apiUrl} y su documentación interactiva (generada " +
      "automáticamente por FastAPI) en {docsUrl}.",
    apiCta: "Explorar la documentación de la API",
    issuesTitle: "Peticiones, mejoras y errores",
    issuesBody:
      "Por ahora puedes reportar cualquier petición, idea de mejora o error " +
      "de dos formas: cuéntanos en el canal #support de Discord o, si puedes, " +
      "abre un issue directamente en GitHub. En ambos casos el equipo lo verá " +
      "y le dará seguimiento.",
    issuesCta: "Abrir un issue",
    issuesDiscordCta: "Reportar en Discord",
    discordTitle: "Únete a la comunidad",
    discordBody:
      "Creamos un servidor de Discord para coordinarnos, resolver dudas y " +
      "conocer a otros makers. ¡Te esperamos!",
    discordCta: "Unirse a Discord",
  },
  centers: {
    title: "Centros de acopio",
    subtitle:
      "Puntos de entrega donde llevar tus piezas impresas para que lleguen a " +
      "quien las necesita.",
    register: "Registrar centro",
    filterByCountry: "Filtrar por país",
    filterByState: "Filtrar por estado / provincia / región",
    filterByCity: "Filtrar por ciudad",
    filterByTag: "Filtrar por etiqueta",
    filterByStatus: "Filtrar por estado",
    allCountries: "Todos los países",
    allStates: "Todas las regiones",
    allCities: "Todas las ciudades",
    allTags: "Todas las etiquetas",
    allStatuses: "Todos los centros",
    statusReceiving: "Recibiendo donaciones",
    countOne: "centro de acopio",
    countOther: "centros de acopio",
    empty: "No hay centros de acopio que coincidan con el filtro.",
    verified: "Verificado",
    unverified: "No verificado",
    notReceiving: "No recibe donaciones",
    viewDetails: "Ver detalles de",
    queueHeading: "Centros sin verificar",
    queueDescription:
      "Registrados por la comunidad y aún sin verificar. Verifícalos para " +
      "confirmarlos.",
    archivedHeading: "Centros archivados",
    archivedDescription:
      "Centros retirados del directorio. Restáuralos para devolverlos a la " +
      "lista pública.",
    archivedBadge: "Archivado",
  },
  centerDetail: {
    back: "← Volver a centros de acopio",
    backToContributions: "← Volver a mis aportes",
    verified: "Verificado",
    unverified: "No verificado",
    privateLocation: "Ubicación de la petición",
    address: "Dirección",
    viewOnMap: "Ver en el mapa",
    noMapLink: "Sin enlace de ubicación",
    noMapLinkHint:
      "Este centro aún no ha agregado un enlace de ubicación. Edítalo para " +
      "añadir uno.",
    city: "Ciudad",
    contact: "Contacto",
    hours: "Horario",
    organization: "Organización",
    orgVerified: "Verificada",
    orgUnverified: "Organización sin verificar",
    management: "Gestión",
    managedIndividually: "Gestionado por un colaborador individual",
    description: "Descripción",
    tags: "Etiquetas",
    edit: "Editar centro",
    clone: "Clonar centro",
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Deja una nota para la comunidad o sigue la actividad de este centro.",
  },
  centerEdit: {
    back: "← Volver al centro de acopio",
    title: "Editar centro de acopio",
    subtitle:
      "Actualiza los datos de este centro. Los cambios se reflejan de " +
      "inmediato en el directorio.",
  },
  centerNew: {
    back: "← Volver a centros de acopio",
    title: "Registrar centro de acopio",
    subtitle:
      "Añade un punto de entrega para que la comunidad pueda llevar sus piezas " +
      "impresas. No necesitas cuenta: un mantenedor lo revisará antes de " +
      "marcarlo como verificado.",
    cloneTitle: "Clonar centro de acopio",
    cloneSubtitle:
      "Partimos de los datos de un centro existente. Ajusta lo que cambie y " +
      "regístralo: se creará como un centro nuevo, sin verificar.",
  },
  centerForm: {
    title: "Registrar centro de acopio",
    description:
      "Tu centro aparecerá de inmediato en el directorio como «No verificado» " +
      "hasta que un mantenedor lo verifique.",
    name: "Nombre",
    namePlaceholder: "UCAB Lab - Caracas",
    country: "País",
    countryPlaceholder: "VE",
    state: "Estado / Provincia / Región",
    statePlaceholder: "Ej.: Miranda, California, Lima",
    city: "Ciudad",
    cityPlaceholder: "Caracas",
    address: "Dirección",
    addressPlaceholder: "Av. Teherán, Montalbán, Caracas",
    locationUrl: "Enlace de ubicación (opcional)",
    locationUrlPlaceholder: "https://maps.google.com/...",
    contact: "Contacto",
    contactPlaceholder: "Teléfono o correo",
    hours: "Horario (opcional)",
    hoursPlaceholder: "Lun-Vie 9-17",
    descriptionLabel: "Descripción (opcional, admite Markdown)",
    descriptionPlaceholder:
      "Indicaciones de entrega, referencias, etc. Admite Markdown.",
    tags: "Etiquetas (opcional)",
    submit: "Registrar centro",
    editTitle: "Editar centro de acopio",
    editDescription:
      "Actualiza la información de contacto y entrega de este centro.",
    editSubmit: "Guardar cambios",
    errorRequired: "Completa todos los campos obligatorios.",
    errorOrgMembership: "No eres miembro activo de esa organización.",
    errorNotFound: "El centro de acopio ya no existe.",
    errorNotOwner: "Solo el propietario del centro puede archivarlo.",
    errorNotMember: "No tienes permisos para cambiar el estado de este centro.",
    errorArchiveBlocked:
      "Este centro tiene contribuciones abiertas y no se puede archivar " +
      "todavía.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  centerVerify: {
    verify: "Verificar",
    revoke: "Revocar verificación",
  },
  centerArchive: {
    archive: "Archivar centro",
    forceArchive: "Archivar centro",
    confirmQuestion:
      "¿Archivar este centro? Dejará de aparecer en el directorio público.",
    confirm: "Sí, archivar",
    cancel: "Cancelar",
    restore: "Restaurar",
  },
  resourceArchive: {
    heading: "Zona de peligro",
    hintPart: "Al archivar, la pieza deja de aparecer en el catálogo.",
    hintSupply: "Al archivar, el insumo deja de aparecer en el catálogo.",
    archivePart: "Archivar pieza",
    archiveSupply: "Archivar insumo",
    confirmPart: "¿Archivar esta pieza? Dejará de aparecer en el catálogo.",
    confirmSupply: "¿Archivar este insumo? Dejará de aparecer en el catálogo.",
    confirm: "Sí, archivar",
    cancel: "Cancelar",
    errorBlocked:
      "No se puede archivar: hay peticiones abiertas que lo utilizan. " +
      "Ciérralas primero.",
    errorGeneric: "No se pudo archivar. Inténtalo de nuevo.",
  },
  centerStatus: {
    markInactive: "Marcar: no recibe donaciones",
    markActive: "Marcar: recibiendo donaciones",
  },
  shipments: {
    title: "Envíos",
    subtitle:
      "Fechas en las que este centro despacha la ayuda a donde se necesita.",
    addShipment: "Añadir envío",
    empty: "Este centro todavía no tiene envíos programados.",
    noOpen: "No hay envíos abiertos en este momento.",
    archivedHeading: "Cerrados o cancelados",
    date: "Fecha de envío",
    statusLabel: "Estado",
    status: {
      receiving: "Recibiendo paquetes",
      closed: "Cerrado",
      cancelled: "Cancelado",
    },
    destination: "Destino",
    destinationPlaceholder: "Caracas, Venezuela",
    description: "Detalles",
    descriptionPlaceholder: "Detalles del envío (admite Markdown).",
    create: "Crear envío",
    saveChanges: "Guardar cambios",
    cancel: "Cancelar",
    edit: "Editar",
    delete: "Eliminar",
    viewDetails: "Ver envío",
    detailBack: "← Volver a",
    commentsTitle: "Comentarios y actividad",
    commentsSubtitle: "Coordina la entrega o sigue la actividad de este envío.",
    errorDateRequired: "Indica la fecha del envío.",
    errorNotMember: "Solo el equipo del centro puede gestionar los envíos.",
    errorNotFound: "El envío o el centro ya no existe.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorAuth: "Debes iniciar sesión para gestionar envíos.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  feed: {
    composerPlaceholder: "Escribe un comentario… admite Markdown.",
    markdownHint: "Admite Markdown",
    post: "Comentar",
    loginToComment: "Inicia sesión para dejar un comentario.",
    empty: "Aún no hay actividad.",
    edited: "editado",
    save: "Guardar",
    cancel: "Cancelar",
    edit: "Editar",
    delete: "Eliminar",
    copyLink: "Copiar enlace",
    linkCopied: "Enlace copiado",
    actions: {
      created: "creó esto",
      updated: "actualizó esto",
      status_changed: "cambió el estado",
      item_added: "añadió un artículo",
      deleted: "eliminó esto",
      commented: "comentó",
      comment_edited: "editó un comentario",
      comment_deleted: "eliminó un comentario",
    },
    // Action labels for commitment events on a request item's timeline.
    itemActions: {
      created: "se comprometió",
      status_changed: "actualizó su compromiso",
    },
    commitmentStatus: {
      claimed: "Comprometida",
      prepared: "Impresa",
      delivered: "Entregada",
      received: "Recibida en el centro",
      released: "Liberada",
    },
    commitmentUnit: "piezas",
    errorNotAuthor: "Solo el autor puede editar este comentario.",
    errorDeleteForbidden:
      "Solo el autor o un mantenedor/administrador puede eliminarlo.",
    errorNotFound: "El comentario o el elemento ya no existe.",
    errorEmpty: "El comentario no puede estar vacío.",
    errorAuth: "Debes iniciar sesión para comentar.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  admin: {
    pageTitle: "Gestión de usuarios",
    pageSubtitle: "Crea cuentas, cambia roles y restablece contraseñas.",
    createTitle: "Crear cuenta",
    createDescription:
      "Provisiona una cuenta para un colaborador de confianza.",
    username: "Usuario",
    usernamePlaceholder: "usuario",
    password: "Contraseña",
    passwordPlaceholder: "Mín. 8, letra y número",
    role: "Rol",
    rolePlaceholder: "Selecciona un rol",
    roleUser: "Usuario",
    roleMaintainer: "Mantenedor",
    roleAdmin: "Administrador",
    createSubmit: "Crear cuenta",
    createSuccess: "Cuenta creada correctamente.",
    tableAriaLabel: "Usuarios",
    colUser: "Usuario",
    colRole: "Rol",
    colStatus: "Estado",
    colActions: "Acciones",
    you: "(tú)",
    statusActive: "Activo",
    statusInactive: "Inactivo",
    passwordButton: "Contraseña",
    deactivate: "Desactivar",
    activate: "Activar",
    resetTitle: "Cambiar contraseña de",
    resetNewPassword: "Nueva contraseña",
    resetSave: "Guardar",
    resetClose: "Cerrar",
    resetSuccess: "Contraseña actualizada.",
    roleAriaLabel: "Rol de",
    errorUsernameTaken: "Ese nombre de usuario ya está en uso.",
    errorWeakPassword:
      "La contraseña debe tener al menos 8 caracteres, con una letra y un número.",
    errorLockout:
      "No puedes degradar ni desactivar al último administrador activo.",
    errorUserNotFound: "El usuario ya no existe.",
    errorMissingCreate: "Completa el usuario y la contraseña.",
    errorMissingPassword: "Ingresa la nueva contraseña.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  parts: {
    title: "Catálogo de piezas",
    subtitle:
      "Diseños imprimibles que la comunidad puede usar en las campañas de " +
      "ayuda. Cada pieza enlaza al archivo para descargar e imprimir.",
    register: "Añadir pieza",
    empty: "Todavía no hay piezas en el catálogo.",
    search: "Buscar",
    searchPlaceholder: "Buscar por nombre…",
    filterByTag: "Filtrar por etiqueta",
    allTags: "Todas las etiquetas",
    download: "Descargar archivo",
    discontinued: "Descontinuada",
    viewDetails: "Ver detalles de",
  },
  partNew: {
    back: "← Volver al catálogo",
    title: "Añadir una pieza",
    subtitle:
      "Registra un diseño imprimible para que se pueda solicitar en las " +
      "campañas de ayuda.",
  },
  partDetail: {
    back: "← Volver al catálogo",
    backToContributions: "← Volver a mis aportes",
    backToItem: "Volver a",
    download: "Descargar archivo",
    descriptionHeading: "Descripción",
    edit: "Editar pieza",
    discontinued: "Descontinuada",
    // Provider-aware call to action for the source link (the file lives on
    // an external site, not on PrintForHelp).
    sourceLinks: {
      self: "Descargar archivo",
      makerworld: "Llévame a MakerWorld",
      googledrive: "Llévame a Google Drive",
      thingiverse: "Ver en Thingiverse",
      printables: "Ver en Printables",
      thangs: "Ver en Thangs",
      cults3d: "Ver en Cults3D",
      github: "Ver en GitHub",
      dropbox: "Abrir en Dropbox",
      onedrive: "Abrir en OneDrive",
      default: "Abrir enlace de descarga",
    },
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Deja una nota para la comunidad o sigue la actividad de esta pieza.",
  },
  partEdit: {
    back: "← Volver a la pieza",
    title: "Editar pieza",
    subtitle:
      "Actualiza el nombre, los enlaces, la descripción (en Markdown) y las " +
      "etiquetas de esta pieza.",
  },
  partForm: {
    title: "Añadir pieza",
    description:
      "La pieza quedará disponible en el catálogo para usarse en peticiones.",
    name: "Nombre",
    namePlaceholder: "Férula de muñeca",
    chooseFile: "Elegir archivo",
    noFile: "Ningún archivo seleccionado",
    sourceFile: "Sube el archivo",
    sourceFileHint:
      "STL, 3MF, OBJ, STEP, ZIP… hasta 100 MB. Se aloja en PrintForHelp.",
    sourceUrl: "O pega un enlace si el archivo ya está alojado en otro sitio",
    sourceUrlPlaceholder: "https://www.thingiverse.com/thing:123",
    currentFile: "Archivo actual",
    imageUpload: "Subir imagen (opcional)",
    imageUploadHint: "PNG, JPEG o WebP, hasta 5 MB.",
    currentImage: "Imagen actual",
    image: "O pega una URL de imagen",
    imagePlaceholder: "https://…/foto.png",
    labelUpload: "Subir etiqueta para imprimir (opcional)",
    labelUploadHint:
      "Una imagen (p. ej. «Donación médica») que puedes incluir sobre el " +
      "QR al imprimir. PNG, JPEG o WebP, hasta 5 MB.",
    currentLabel: "Etiqueta actual",
    label: "O pega una URL de etiqueta",
    labelPlaceholder: "https://…/etiqueta.png",
    descriptionLabel: "Descripción (opcional)",
    descriptionPlaceholder: "Material sugerido, notas de impresión, etc.",
    tags: "Etiquetas (opcional)",
    submit: "Añadir pieza",
    editTitle: "Editar pieza",
    editSubmit: "Guardar cambios",
    errorRequired: "Indica el nombre y un enlace de descarga o un archivo.",
    errorOrgMembership: "No eres miembro activo de esa organización.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorImageTooLarge: "La imagen supera el tamaño máximo permitido (5 MB).",
    errorImageInvalid: "El archivo no es una imagen válida (PNG, JPEG o WebP).",
    errorFileTooLarge: "El archivo supera el tamaño máximo permitido (100 MB).",
    errorFileType:
      "Tipo de archivo no admitido. Usa STL, 3MF, OBJ, STEP o ZIP.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  supplies: {
    title: "Catálogo de insumos",
    subtitle:
      "Artículos no imprimibles que la comunidad puede aportar a las " +
      "campañas de ayuda: medicinas, agua, alimentos y más.",
    register: "Añadir insumo",
    empty: "Todavía no hay insumos en el catálogo.",
    search: "Buscar",
    searchPlaceholder: "Buscar por nombre…",
    filterByTag: "Filtrar por etiqueta",
    allTags: "Todas las etiquetas",
    units: "Unidades",
    discontinued: "Descontinuado",
    viewDetails: "Ver detalles de",
  },
  supplyNew: {
    back: "← Volver al catálogo",
    title: "Añadir un insumo",
    subtitle:
      "Registra un artículo no imprimible para que se pueda solicitar en " +
      "las campañas de ayuda.",
  },
  supplyDetail: {
    back: "← Volver al catálogo",
    backToContributions: "← Volver a mis aportes",
    backToItem: "Volver a",
    descriptionHeading: "Descripción",
    edit: "Editar insumo",
    discontinued: "Descontinuado",
    units: "Unidades",
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Deja una nota para la comunidad o sigue la actividad de este insumo.",
  },
  supplyEdit: {
    back: "← Volver al insumo",
    title: "Editar insumo",
    subtitle:
      "Actualiza el nombre, la unidad, la imagen, la descripción y las " +
      "etiquetas de este insumo.",
  },
  supplyForm: {
    title: "Añadir insumo",
    description:
      "El insumo quedará disponible en el catálogo para usarse en peticiones.",
    name: "Nombre",
    namePlaceholder: "Agua potable",
    units: "Unidades de medida (opcional)",
    unitsHint:
      "Añade las unidades sugeridas para este insumo (p. ej. litros, kg, " +
      "cajas). Quien haga una petición podrá elegir una o añadir otra.",
    chooseFile: "Elegir archivo",
    noFile: "Ningún archivo seleccionado",
    imageUpload: "Subir imagen (opcional)",
    imageUploadHint: "PNG, JPEG o WebP, hasta 5 MB.",
    currentImage: "Imagen actual",
    image: "O pega una URL de imagen",
    imagePlaceholder: "https://…/foto.png",
    descriptionLabel: "Descripción (opcional)",
    descriptionPlaceholder: "Presentación, cantidad sugerida, notas, etc.",
    tags: "Etiquetas (opcional)",
    submit: "Añadir insumo",
    editTitle: "Editar insumo",
    editSubmit: "Guardar cambios",
    errorRequired: "Indica el nombre del insumo.",
    errorOrgMembership: "No eres miembro activo de esa organización.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorImageTooLarge: "La imagen supera el tamaño máximo permitido (5 MB).",
    errorImageInvalid: "El archivo no es una imagen válida (PNG, JPEG o WebP).",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  requests: {
    title: "Peticiones",
    subtitle:
      "Campañas de piezas que la comunidad necesita imprimir. Cada campaña " +
      "agrupa varias piezas con su avance.",
    register: "Crear petición",
    empty: "No hay peticiones abiertas en este momento.",
    status: {
      open: "Abierta",
      fulfilled: "Completada",
      closed: "Cerrada",
    },
    itemsCount: "piezas",
    viewDetails: "Ver detalles de",
    lastActivity: "Última actividad",
    noActivity: "Sin actividad reciente",
  },
  requestNew: {
    back: "← Volver a peticiones",
    title: "Crear una petición",
    subtitle:
      "Crea una campaña y añade las piezas que se necesitan, con la cantidad " +
      "objetivo de cada una.",
  },
  requestForm: {
    title: "Nueva petición",
    description: "Agrupa una o más piezas en una campaña de ayuda.",
    campaignTitle: "Título de la campaña",
    campaignTitlePlaceholder: "Férulas para Venezuela 2026",
    descriptionLabel: "Descripción (opcional)",
    descriptionPlaceholder: "Contexto de la campaña (admite Markdown).",
    imageUpload: "Subir imagen (opcional)",
    imageUploadHint: "PNG, JPEG o WebP, hasta 5 MB.",
    currentImage: "Imagen actual",
    imageUrl: "O pega una URL de imagen",
    imageUrlPlaceholder: "https://…/foto.png",
    deadline: "Fecha límite (opcional)",
    afterCreateHint:
      "Después de crear la petición podrás añadir las piezas e insumos que " +
      "se necesitan.",
    itemsHeading: "Piezas (opcional)",
    itemsHint: "Puedes añadirlas ahora o agregarlas más tarde a la petición.",
    itemPart: "Pieza",
    itemKind: "Tipo",
    itemKindBoth: "Piezas e insumos",
    itemKindParts: "Solo piezas",
    itemKindSupplies: "Solo insumos",
    itemResource: "Artículo",
    itemUnit: "Unidad",
    itemUnitPlaceholder: "p. ej. litros",
    preferredCenters: "Centros de entrega preferidos (opcional)",
    preferredCentersHint:
      "Si eliges uno o más, quienes ayuden solo verán estos centros al " +
      "entregar sus aportes.",
    preferredCentersEmpty: "No hay centros verificados disponibles todavía.",
    privateCenterTag: "privada",
    addLocation: "+ Añadir una ubicación privada",
    addLocationHint:
      "Registra un punto de entrega solo para esta petición. No aparecerá " +
      "en el directorio de centros de acopio, pero será visible para quienes " +
      "ayuden en esta petición.",
    addLocationSubmit: "Añadir ubicación",
    locationName: "Nombre",
    locationContact: "Contacto",
    locationAddress: "Dirección",
    locationCity: "Ciudad",
    locationCountry: "País",
    locationMapUrl: "Enlace de ubicación (opcional)",
    locationHours: "Horario (opcional)",
    locationErrorRequired:
      "Indica nombre, dirección, país, ciudad y contacto de la ubicación.",
    cancel: "Cancelar",
    itemQuantity: "Cantidad (opcional)",
    addItem: "Añadir otra pieza",
    addItemSubmit: "Añadir pieza",
    removeItem: "Quitar",
    noParts:
      "Aún no hay piezas en el catálogo. Crea la petición y añádelas más " +
      "tarde.",
    submit: "Crear petición",
    editTitle: "Editar petición",
    editSubmit: "Guardar cambios",
    alreadyAdded: "ya añadida",
    errorRequired: "Indica un título para la petición.",
    errorDuplicatePart: "Esa pieza ya está en la petición.",
    errorPartDiscontinued: "Una de las piezas ya no está disponible.",
    errorPartNotFound: "Una de las piezas seleccionadas ya no existe.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorImageTooLarge: "La imagen supera el tamaño máximo permitido (5 MB).",
    errorImageInvalid: "El archivo no es una imagen válida (PNG, JPEG o WebP).",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  requestEdit: {
    back: "← Volver a la petición",
    title: "Editar petición",
    subtitle:
      "Actualiza el título, la descripción (en Markdown) y la fecha límite " +
      "de la campaña.",
  },
  requestDetail: {
    back: "← Volver a peticiones",
    backToContributions: "← Volver a mis aportes",
    backToItem: "Volver a",
    deadline: "Fecha límite",
    noDeadline: "Sin fecha límite",
    edit: "Editar",
    close: "Cerrar petición",
    reopen: "Reabrir petición",
    reopenItem: "Reabrir artículo",
    lateHelpNote:
      "Aunque una petición o un artículo esté cerrado o completo, si ya " +
      "tienes ayuda lista para enviar, todavía puedes comprometerte a " +
      "aportarla.",
    jumpTo: "Ver:",
    closeItem: "Cerrar",
    removeItem: "Eliminar",
    editTargetLabel: "Objetivo",
    saveTarget: "Guardar objetivo",
    addPartHeading: "Añadir un artículo",
    itemsHeading: "Artículos solicitados",
    progressClaimed: "Comprometidas",
    progressAtCenter: "En el centro",
    progressRemaining: "Faltan",
    created: "Creado",
    target: "Objetivo",
    openEnded: "Sin objetivo fijo",
    itemClosed: "Cerrada",
    itemFulfilled: "Completada",
    viewItem: "Ver detalles y comentarios →",
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Deja una nota para la comunidad o sigue la actividad de esta petición.",
  },
  requestItem: {
    back: "← Volver a la petición",
    target: "Objetivo",
    openEnded: "Sin objetivo fijo",
    progressClaimed: "Comprometidas",
    progressAtCenter: "En el centro",
    progressRemaining: "Faltan",
    created: "Creada",
    lastActivity: "Última actividad",
    whoHeading: "¿Quién hace la petición?",
    whatHeading: "¿Qué están solicitando?",
    centersHeading: "Centros de entrega para este artículo",
    centersHelp:
      "¿Puedes ayudar con esta petición? Consulta abajo los lugares donde " +
      "puedes dejar o enviar tu aporte.",
    centersDirections: "Ver ubicación",
    centersEdit: "Editar centros",
    centersEditHint:
      "Marca solo los centros donde se necesita este artículo. Si no marcas " +
      "ninguno, se usan todos los centros preferidos de la petición.",
    centersSave: "Guardar centros",
    centersCancel: "Cancelar",
    centersSaved: "¡Centros actualizados!",
    viewCampaign: "Ver la petición completa",
    viewPart: "Ver la pieza",
    requestedBy: "Solicitado por",
    communityRequest: "Solicitud de la comunidad",
    orgUnverified: "Organización no verificada",
    itemFulfilled: "Completada",
    itemClosed: "Cerrada",
    shareHint:
      "Comparte este enlace para que más gente vea el avance y pueda ayudar.",
    commitmentsTitle: "Compromisos",
    commitmentsSubtitle:
      "Personas que ya se comprometieron a imprimir esta pieza.",
    commitmentsEmpty: "Aún nadie se ha comprometido. ¡Sé la primera persona!",
    commitmentUnit: "piezas",
    commitmentStatus: {
      claimed: "Comprometida",
      prepared: "Impresa",
      delivered: "Entregada",
      received: "Recibida en el centro",
      released: "Liberada",
    },
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Coordina o comenta sobre esta pieza. Cualquiera puede seguir el avance.",
    filters: {
      all: "Todas",
      needs_help: "Necesitan ayuda",
      committed: "Comprometidas",
      completed: "Completadas",
    },
    helpState: {
      needs_help: "Necesita ayuda",
      committed: "Comprometida",
      completed: "Completada",
    },
    filterEmpty:
      "Parece que ahora mismo no hay piezas que necesiten ayuda en esta " +
      "petición. Síguela para recibir una notificación si se necesita más " +
      "ayuda.",
    filterEmptyLogin: "Inicia sesión para seguir esta petición",
  },
  itemDescription: {
    heading: "Detalles",
    add: "Añadir detalles",
    edit: "Editar detalles",
    save: "Guardar",
    cancel: "Cancelar",
    placeholder:
      "Documenta este artículo: por qué se necesita, quién lo recibirá, " +
      "requisitos especiales, etc. (admite Markdown).",
    emptyOwner: "Aún no hay detalles. Añádelos para informar a quien ayude.",
  },
  claim: {
    title: "Quiero ayudar con esto",
    heading: "¿Quieres contribuir?",
    subtitle: "Indica abajo con cuánto puedes ayudar.",
    stillHelpNote:
      "Este artículo ya está completo o cerrado, pero si ya tienes ayuda " +
      "lista para enviar, aún puedes comprometerte (menor prioridad).",
    quantity: "Cantidad",
    centerLater:
      "Elegirás el centro de acopio de entrega más tarde, desde «Mis " +
      "aportes», antes de marcarla como entregada.",
    submit: "Comprometerme",
    loginToClaim: "Inicia sesión para comprometerte.",
    success: "¡Listo! Tu compromiso aparece en «Mis aportes».",
  },
  myContributions: {
    title: "Mis aportes",
    subtitle:
      "Las piezas que te has comprometido a imprimir y su estado actual.",
    empty: "Todavía no te has comprometido a imprimir ninguna pieza.",
    fromRequest: "Petición:",
    quantity: "Cantidad",
    statusLabel: "Estado",
    filterByPart: "Pieza",
    allParts: "Todas las piezas",
    filterByRequest: "Petición",
    allRequests: "Todas las peticiones",
    allStatuses: "Todos los estados",
    filterByTag: "Etiqueta",
    allTags: "Todas las etiquetas",
    filteredEmpty: "Ningún aporte coincide con los filtros.",
    status: {
      claimed: "Comprometida",
      prepared: "Impresa",
      delivered: "Entregada",
      received: "Recibida",
      released: "Liberada",
    },
    statusFilter: {
      claimed: "Esperando impresión",
      prepared: "Esperando entrega",
      delivered: "Entregada",
      received: "Recibida",
      released: "Liberada",
    },
    markPrinted: "Marcar como impresa",
    markDelivered: "Marcar como entregada",
    confirmReceived: "Confirmar recepción",
    release: "Liberar",
    autoReceived: "Recibida automáticamente",
    dropOffAt: "Entrega en:",
    getDirections: "Ver ubicación",
    noCenterYet: "Sin centro de entrega todavía",
    noCentersYet: "Aún no hay centros verificados disponibles.",
    setCenterLabel: "Centro de acopio de entrega",
    setCenter: "Asignar centro",
    changeCenter: "Cambiar centro",
    changeCenterPrompt: "¿Cambiar centro de entrega?",
    centerUpdated: "¡Actualizado!",
    cancel: "Cancelar",
    tagsLabel: "Etiquetas",
    addTags: "Añadir etiquetas",
    editTags: "Editar etiquetas",
    saveTags: "Guardar etiquetas",
    tagsHelpLabel: "Acerca de las etiquetas",
    tagsHelp:
      "Las etiquetas son personales y únicas para ti: sirven para organizar y filtrar fácilmente tus aportes (por ejemplo, por material, urgencia o lote).",
    trackingSetup: "Configurar rastreo",
    trackingView: "Ver rastreo",
  },
  tracking: {
    pageTitle: "Rastreo de artículos",
    backToContributions: "Volver a mis aportes",
    summaryQuantity: "Cantidad",
    summaryStatus: "Estado",
    groupLabel: "Grupo",
    itemLabel: "Artículo",
    generateTitle: "Todavía no has generado el rastreo",
    generateDescription:
      "Genera un código QR para el grupo y uno por cada pieza. Podrás imprimirlos y pegarlos en cada artículo para que cualquiera pueda ver y añadir actualizaciones al escanearlos.",
    generateButton: "Generar códigos QR",
    settingsTitle: "Quién puede ver el rastreo",
    visibilityLabel: "Visibilidad",
    visibilityPrivate: "Privado (solo tú)",
    visibilityGroup: "Grupo de usuarios",
    visibilityPublic: "Público (cualquiera con el enlace)",
    visibilityHelp:
      "Privado: solo tú y los administradores. Grupo: además, las personas que agregues por nombre de usuario. Público: cualquiera con el enlace o el QR.",
    membersLabel: "Usuarios con acceso",
    membersHelp:
      "Busca y agrega los usuarios que podrán ver este rastreo cuando la visibilidad sea «Grupo de usuarios».",
    membersSearchPlaceholder: "Busca un usuario…",
    membersNoResults: "No se encontraron usuarios.",
    saveSettings: "Guardar cambios",
    settingsSaved: "¡Cambios guardados!",
    shareTitle: "Enlace para compartir",
    shareHintPublic:
      "Cualquiera con este enlace (o el QR del grupo) puede ver y añadir actualizaciones sin iniciar sesión.",
    shareHintGroup:
      "Solo los usuarios que agregaste pueden ver este enlace, e iniciando sesión.",
    sharePrivateNote:
      "Este rastreo es privado: solo tú y los administradores pueden verlo. Cambia la visibilidad a «Grupo» o «Público» para compartirlo.",
    shareCopy: "Copiar enlace",
    shareCopied: "¡Copiado!",
    messageLabel: "Mensaje del donante (opcional)",
    messagePlaceholder:
      "Escribe un mensaje para quien reciba la pieza, por ejemplo «Con " +
      "cariño, la comunidad de PrintForHelp».",
    messageHelp:
      "Si escribes un mensaje, se imprime encima de cada QR en la descarga " +
      "(máximo 100 caracteres). Si lo dejas vacío, no se incluye ningún " +
      "mensaje.",
    messageCharsLeft: "caracteres restantes",
    savedMessagesHint:
      "Haz clic en un mensaje que ya usaste para reutilizarlo aquí:",
    deleteMessageAria: "Eliminar mensaje guardado",
    rememberMessage: "Recordar mi mensaje",
    rememberMessageTooltip:
      "Guarda este mensaje en tu lista para reutilizarlo en cualquier " +
      "tracking. No hace falta guardarlo para incluirlo en esta descarga.",
    qrTitle: "Códigos QR",
    qrDescription:
      "Descarga todos los QR en un solo archivo para imprimirlos, o baja cada uno por separado.",
    includeLabel: "Incluir la etiqueta de la pieza",
    downloadPdf: "Descargar PDF con todos los QR",
    downloadPng: "Descargar PNG con todos los QR",
    downloadQr: "Descargar QR",
    openPublicPage: "Abrir página pública",
    timelineTitle: "Actualizaciones",
    timelineEmpty: "Todavía no hay actualizaciones.",
    copyUpdateLink: "Copiar enlace",
    updateLinkCopied: "Enlace copiado",
    showItemUpdates: "Mostrar también las actualizaciones de cada artículo",
    anonymous: "Anónimo",
    addUpdateTitle: "Añadir una actualización",
    descriptionLabel: "Descripción",
    descriptionPlaceholder: "¿Qué pasó con este artículo?",
    tagsLabel: "Etiquetas",
    postAnonymously: "Publicar de forma anónima",
    guestNote:
      "No has iniciado sesión: tu actualización aparecerá como anónima.",
    submitUpdate: "Publicar actualización",
    updatePosted: "¡Actualización publicada!",
    editTags: "Editar etiquetas",
    addTags: "Añadir etiquetas",
    saveTags: "Guardar",
    cancel: "Cancelar",
    privateTitle: "Este rastreo es privado",
    privateBody:
      "Quien creó este rastreo no lo ha hecho público. Inicia sesión si tienes acceso.",
    notFoundTitle: "Rastreo no encontrado",
    notFoundBody: "El enlace no corresponde a ningún artículo rastreado.",
    errorForbidden: "No tienes acceso a este rastreo.",
    errorAlreadyExists: "Este aporte ya tiene rastreo.",
    errorEditForbidden: "No puedes editar esta actualización.",
    errorDescriptionRequired: "Escribe una descripción.",
    errorValidation: "Revisa los datos e inténtalo de nuevo.",
    errorGeneric: "Ocurrió un error. Inténtalo de nuevo.",
  },
  tagInput: {
    placeholder: "Escribe y pulsa Enter…",
    removeLabel: "Quitar",
    createLabel: "Crear",
  },
  contributions: {
    errorRequired: "Indica una cantidad válida.",
    errorCenterUnavailable:
      "Ese centro debe estar verificado y activo para recibir piezas.",
    errorCenterRequired:
      "Añade un centro de acopio antes de marcar como entregada.",
    errorItemClosed: "Esta pieza ya no acepta nuevos compromisos.",
    errorInvalidTransition: "No se puede cambiar el estado desde el actual.",
    errorNotMaker: "Solo quien se comprometió puede avanzar esta pieza.",
    errorNotReceiver: "Solo el equipo del centro puede confirmar la recepción.",
    errorValidation: "Revisa los datos e inténtalo de nuevo.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  meta: {
    title: "PrintForHelp: Comunidad 3D al servicio de quien lo necesita",
    description:
      "Plataforma de coordinación para la comunidad de impresión 3D: centros " +
      "de acopio, peticiones y registro de piezas en producción.",
  },
  markdownEditor: {
    write: "Escribir",
    preview: "Vista previa",
    attach: "Adjuntar imágenes",
    attachHint: "Pega, arrastra o selecciona una imagen para subirla.",
    uploadingHint: "Subiendo imagen…",
    uploading: "Subiendo",
    previewEmpty: "No hay nada que previsualizar.",
    errors: {
      AUTH: "Debes iniciar sesión para subir imágenes.",
      NO_FILE: "No se seleccionó ninguna imagen.",
      INVALID_IMAGE: "El archivo no es una imagen válida.",
      IMAGE_TOO_LARGE: "La imagen es demasiado grande.",
      UPLOAD: "No se pudo subir la imagen.",
      default: "No se pudo subir la imagen.",
    },
  },
  notifications: {
    ariaLabel: "Notificaciones",
    title: "Notificaciones",
    empty: "No tienes notificaciones.",
    loading: "Cargando…",
    markAllRead: "Marcar todas como leídas",
    summary: {
      mentioned: "te mencionó",
      commented: "comentó",
      statusChanged: "cambió el estado",
      itemAdded: "añadió un artículo",
      trackingUpdate: "publicó una actualización de seguimiento",
      updated: "actualizó",
    },
  },
  watch: {
    watch: "Seguir",
    watching: "Siguiendo",
    watchAria: "Seguir para recibir notificaciones",
    unwatchAria: "Dejar de seguir",
    watchTooltip:
      "¿Te interesa este elemento? Síguelo para recibir notificaciones " +
      "sobre cambios, comentarios y más.",
    watchingTooltip:
      "Estás siguiendo este elemento. Haz clic para dejar de recibir " +
      "notificaciones sobre él.",
    error: "No se pudo actualizar. Intenta de nuevo.",
  },
  mentions: {
    loading: "Buscando…",
    empty: "Sin coincidencias",
  },
  notices: {
    // Banner
    showHidden: "Ver avisos ocultos",
    dismiss: "Descartar aviso",
    // Admin tab
    pageTitle: "Avisos del sitio",
    pageSubtitle:
      "Publica banners en las páginas y revisa las solicitudes de aviso " +
      "de los responsables de piezas, centros y peticiones.",
    queueTitle: "Solicitudes pendientes",
    queueDescription:
      "Avisos solicitados por responsables de un elemento. No se muestran " +
      "hasta que los apruebes.",
    queueEmpty: "No hay solicitudes pendientes.",
    createTitle: "Crear banner de página",
    createDescription:
      "Se muestra en las páginas que elijas. Redacta el mensaje en cada " +
      "idioma que necesites (el inglés es el predeterminado).",
    listTitle: "Avisos activos",
    listEmpty: "Aún no hay avisos.",
    severityLabel: "Severidad",
    severityInfo: "Información",
    severitySuccess: "Éxito",
    severityWarning: "Advertencia",
    severityCritical: "Crítico",
    scopesLabel: "Páginas",
    scopeAll: "Todas",
    scopeHome: "Inicio",
    scopeCenters: "Centros",
    scopeRequests: "Peticiones",
    scopeParts: "Piezas",
    scopeMyContributions: "Mis aportes",
    scopeAbout: "Nosotros",
    // Translations editor
    languageLabel: "Idioma",
    titleLabel: "Título (opcional)",
    messageLabel: "Mensaje",
    actionLabelLabel: "Texto del botón (opcional)",
    actionUrlLabel: "Enlace del botón (opcional)",
    messagePlaceholder: "Escribe el aviso…",
    markdownHint:
      "Admite Markdown: saltos de línea, **negrita** y enlaces " +
      "[texto](https://…).",
    actionUrlPlaceholder: "https://…",
    addLanguage: "Añadir idioma",
    removeLanguage: "Quitar idioma",
    // Table
    colMessage: "Aviso",
    colSeverity: "Severidad",
    colTarget: "Alcance",
    colStatus: "Estado",
    colLanguages: "Idiomas",
    colCreated: "Creado",
    colActions: "Acciones",
    statusPending: "Pendiente",
    statusApproved: "Aprobado",
    statusDeclined: "Rechazado",
    enabledOn: "Visible",
    enabledOff: "Oculto",
    enable: "Activar",
    disable: "Desactivar",
    approve: "Aprobar",
    decline: "Rechazar",
    edit: "Editar",
    editTitle: "Editar aviso",
    save: "Guardar cambios",
    updateSuccess: "Aviso actualizado.",
    delete: "Eliminar",
    targetPage: "Páginas",
    targetResource: "Pieza",
    targetCollectionCenter: "Centro",
    targetRequest: "Petición",
    requestedBy: "Solicitado por",
    // Entity request control
    requestTitle: "Solicitar un aviso",
    requestButton: "Solicitar aviso",
    requestDescriptionOwner:
      "Tu aviso se enviará a revisión y no se mostrará hasta que un " +
      "moderador lo apruebe.",
    requestDescriptionMaintainer:
      "Como moderador, tu aviso se publicará de inmediato en este elemento.",
    submit: "Enviar",
    cancel: "Cancelar",
    requestSuccessPending: "Aviso enviado. Quedó pendiente de aprobación.",
    requestSuccessApproved: "Aviso publicado.",
    createSuccess: "Banner creado.",
    // Errors
    errorMessageRequired: "Escribe el mensaje en cada idioma.",
    errorScopesRequired: "Elige al menos una página.",
    errorAuth: "Debes iniciar sesión para solicitar un aviso.",
    errorNotOwner:
      "Solo puedes solicitar un aviso en un elemento que gestionas.",
    errorNotFound: "El aviso ya no existe.",
    errorNotPending: "Este aviso ya fue revisado.",
    errorTranslationsRequired: "Añade al menos un idioma.",
    errorDuplicateLanguage: "Hay dos traducciones con el mismo idioma.",
    errorInvalidMode: "Configuración de aviso no válida.",
    errorValidation: "Revisa los datos e inténtalo de nuevo.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
};

export type Dictionary = typeof es;
