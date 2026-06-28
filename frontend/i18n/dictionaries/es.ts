/** Spanish message catalog. This object's shape defines `Dictionary`. */

export const es = {
  nav: {
    home: "Inicio",
    centers: "Centros",
    about: "Nosotros",
    users: "Usuarios",
    ariaLabel: "Navegación principal",
  },
  header: {
    greeting: "Hola,",
    logout: "Cerrar sesión",
    login: "Iniciar sesión",
    localeAriaLabel: "Cambiar idioma",
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
    footerNote:
      "Por ahora no admitimos el registro de nuevos usuarios. ¡Mantente " +
      "atento, pronto habilitaremos esta opción!",
    usernameLabel: "Usuario",
    usernamePlaceholder: "Tu usuario",
    passwordLabel: "Contraseña",
    passwordPlaceholder: "Tu contraseña",
    submit: "Iniciar sesión",
    submitting: "Entrando…",
    errorMissing: "Ingresa tu usuario y contraseña.",
    errorInactive: "Esta cuenta está inactiva.",
    errorInvalid: "Usuario o contraseña incorrectos.",
    errorGeneric: "No se pudo iniciar sesión. Inténtalo de nuevo.",
  },
  about: {
    title: "Sobre nosotros",
    intro:
      "PrintForHelp es una plataforma comunitaria sin fines de lucro que " +
      "conecta a quienes imprimen en 3D con quienes necesitan piezas de ayuda " +
      "humanitaria.",
    missionTitle: "Nuestra misión",
    missionTagline: "Coordinar ayuda, no duplicarla.",
    missionBody:
      "Centralizamos la información de centros de acopio, peticiones de piezas " +
      "y producción en curso para que la comunidad cubra mejor la demanda y " +
      "nadie imprima dos veces lo mismo.",
    focusTitle: "Enfoque inicial",
    focusTagline: "Férulas para Venezuela.",
    focusBody:
      "Comenzamos coordinando la impresión de férulas médicas para las personas " +
      "afectadas por el terremoto de junio de 2026 en Venezuela, con la mira " +
      "puesta en convertirnos en un hub general de ayuda impresa en 3D.",
    helpNote:
      "¿Quieres ayudar? Por ahora las cuentas las crea un administrador. Pronto " +
      "habilitaremos el registro abierto para makers y organizaciones.",
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
