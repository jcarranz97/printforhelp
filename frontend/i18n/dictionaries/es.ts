/** Spanish message catalog. This object's shape defines `Dictionary`. */

export const es = {
  nav: {
    home: "Inicio",
    centers: "Centros",
    about: "Nosotros",
    users: "Usuarios",
    ariaLabel: "Navegación principal",
  },
  social: {
    githubAriaLabel: "PrintForHelp en GitHub",
    discordAriaLabel: "Únete a nuestro Discord",
  },
  header: {
    greeting: "Hola,",
    logout: "Cerrar sesión",
    login: "Iniciar sesión",
    localeAriaLabel: "Cambiar idioma",
    localeMenuHeading: "Elige un idioma",
    themeAriaLabel: "Cambiar tema",
    themeLight: "Claro",
    themeDark: "Oscuro",
    themeSystem: "Sistema",
  },
  localePrompt: {
    title: "Idioma",
    description: "Detectamos tu idioma automáticamente. ¿Prefieres cambiarlo?",
  },
  landing: {
    eyebrow: "Comunidad 3D",
    title: "PrintForHelp",
    subtitle:
      "Conectamos a quienes imprimen en 3D con quienes necesitan piezas — " +
      "empezando por férulas para los afectados por el terremoto en Venezuela.",
    howItWorks: "¿Cómo funciona?",
    wantToHelp: "Quiero ayudar",
    comingSoon: "Próximamente",
    featuresAriaLabel: "Funciones principales",
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
    filterByCity: "Filtrar por ciudad",
    allCountries: "Todos los países",
    allCities: "Todas las ciudades",
    countOne: "centro de acopio",
    countOther: "centros de acopio",
    empty: "No hay centros de acopio que coincidan con el filtro.",
    verified: "Verificado",
    unverified: "No verificado",
    viewDetails: "Ver detalles de",
    queueHeading: "Centros sin verificar",
    queueDescription:
      "Registrados por la comunidad y aún sin verificar. Verifícalos para " +
      "confirmarlos.",
  },
  centerDetail: {
    back: "← Volver a centros de acopio",
    verified: "Verificado",
    unverified: "No verificado",
    address: "Dirección",
    city: "Ciudad",
    contact: "Contacto",
    hours: "Horario",
    organization: "Organización",
    orgVerified: "Verificada",
    orgUnverified: "Organización sin verificar",
    management: "Gestión",
    managedIndividually: "Gestionado por un colaborador individual",
    notes: "Notas",
    feedTitle: "Comentarios y actividad",
    feedSubtitle:
      "Deja una nota para la comunidad o sigue la actividad de este centro.",
  },
  centerNew: {
    back: "← Volver a centros de acopio",
    title: "Registrar centro de acopio",
    subtitle:
      "Añade un punto de entrega para que la comunidad pueda llevar sus piezas " +
      "impresas. No necesitas cuenta: un mantenedor lo revisará antes de " +
      "marcarlo como verificado.",
  },
  centerForm: {
    title: "Registrar centro de acopio",
    description:
      "Tu centro aparecerá de inmediato en el directorio como «No verificado» " +
      "hasta que un mantenedor lo verifique.",
    name: "Nombre",
    namePlaceholder: "UCAB Lab — Caracas",
    country: "País",
    countryPlaceholder: "VE",
    city: "Ciudad",
    cityPlaceholder: "Caracas",
    address: "Dirección",
    addressPlaceholder: "Av. Teherán, Montalbán, Caracas",
    contact: "Contacto",
    contactPlaceholder: "Teléfono o correo",
    hours: "Horario (opcional)",
    hoursPlaceholder: "Lun-Vie 9-17",
    notes: "Notas (opcional)",
    notesPlaceholder: "Indicaciones de entrega, referencias, etc.",
    submit: "Registrar centro",
    errorRequired: "Completa todos los campos obligatorios.",
    errorOrgMembership: "No eres miembro activo de esa organización.",
    errorNotFound: "El centro de acopio ya no existe.",
    errorValidation: "Revisa los datos del formulario e inténtalo de nuevo.",
    errorGeneric: "No se pudo completar la acción. Inténtalo de nuevo.",
  },
  centerVerify: {
    verify: "Verificar",
    revoke: "Revocar verificación",
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
    actions: {
      created: "creó esto",
      updated: "actualizó esto",
      status_changed: "cambió el estado",
      deleted: "eliminó esto",
      commented: "comentó",
      comment_edited: "editó un comentario",
      comment_deleted: "eliminó un comentario",
    },
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
  meta: {
    title: "PrintForHelp — Comunidad 3D al servicio de quien lo necesita",
    description:
      "Plataforma de coordinación para la comunidad de impresión 3D: centros " +
      "de acopio, peticiones y registro de piezas en producción.",
  },
};

export type Dictionary = typeof es;
