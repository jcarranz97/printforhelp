/** English message catalog. Typed as `Dictionary` so the compiler flags
 * any key that is missing or extra relative to the Spanish source. */

import type { Dictionary } from "./es";

export const en: Dictionary = {
  nav: {
    home: "Home",
    centers: "Centers",
    about: "About",
    users: "Users",
    ariaLabel: "Main navigation",
  },
  social: {
    githubAriaLabel: "PrintForHelp on GitHub",
    discordAriaLabel: "Join our Discord",
  },
  header: {
    greeting: "Hi,",
    logout: "Log out",
    login: "Log in",
    localeAriaLabel: "Change language",
    localeMenuHeading: "Choose a language",
    themeAriaLabel: "Change theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
  },
  localePrompt: {
    title: "Language",
    description: "We detected your language automatically. Want to change it?",
  },
  landing: {
    eyebrow: "3D Community",
    title: "PrintForHelp",
    subtitle:
      "We connect 3D printers with people who need parts — starting with " +
      "splints for those affected by the earthquake in Venezuela.",
    howItWorks: "How does it work?",
    wantToHelp: "I want to help",
    comingSoon: "Coming soon",
    featuresAriaLabel: "Main features",
    centersTitle: "Collection centers",
    centersDescription:
      "A directory of drop-off points where you can take your printed parts " +
      "so they reach the people who need them.",
    requestsTitle: "Part requests",
    requestsDescription:
      "Anyone who needs a splint or another part can request it here, with " +
      "details and urgency.",
    printingTitle: "What are you printing?",
    printingDescription:
      "Report what you have queued so the community doesn't duplicate work " +
      "and covers demand better.",
    footer: "PrintForHelp · Non-profit community project · MIT License",
  },
  login: {
    title: "Log in",
    description: "Log in to help coordinate aid.",
    noAccountPrompt: "Don't have an account?",
    registerLink: "Sign up",
    usernameLabel: "Email or username",
    usernamePlaceholder: "you@email.com",
    passwordLabel: "Password",
    passwordPlaceholder: "Your password",
    submit: "Log in",
    submitting: "Signing in…",
    errorMissing: "Enter your email or username and your password.",
    errorInactive: "This account is inactive.",
    errorInvalid: "Incorrect email/username or password.",
    errorGeneric: "Could not log in. Please try again.",
  },
  register: {
    title: "Create account",
    description: "Sign up to help coordinate aid.",
    haveAccountPrompt: "Already have an account?",
    loginLink: "Log in",
    nameLabel: "Name",
    namePlaceholder: "Your name",
    usernameLabel: "Username",
    usernamePlaceholder: "Your username",
    emailLabel: "Email",
    emailPlaceholder: "you@email.com",
    passwordLabel: "Password",
    passwordPlaceholder: "Min. 8, with a letter and a number",
    submit: "Create account",
    submitting: "Creating account…",
    errorRequired: "This field is required.",
    errorUsernameTaken: "That username is already taken.",
    errorEmailTaken: "An account with that email already exists.",
    errorInvalidEmail: "Enter a valid email.",
    errorWeakPassword:
      "The password must be at least 8 characters, with a letter and a number.",
    errorGeneric: "Could not create the account. Please try again.",
  },
  about: {
    title: "About us",
    intro:
      "PrintForHelp is a non-profit community platform that connects 3D " +
      "printers with people who need humanitarian-aid parts.",
    missionTitle: "Our mission",
    missionTagline: "Coordinate aid, openly.",
    missionBody:
      "We centralize information about collection centers, part requests and " +
      "in-progress production and make it publicly available to everyone, " +
      "everywhere, so the community can coordinate and help where it's needed " +
      "most.",
    focusTitle: "Initial focus",
    focusTagline: "Splints for Venezuela.",
    focusBody:
      "We're starting by coordinating the printing of medical splints for the " +
      "people affected by the June 2026 earthquake in Venezuela, aiming to " +
      "become a general hub for 3D-printed aid.",
    helpNote:
      "Want to help? For now, accounts are created by an administrator. We'll " +
      "soon enable open registration for makers and organizations.",
    contributeTitle: "How to contribute",
  },
  contribute: {
    title: "Contribute",
    intro:
      "PrintForHelp is an open-source community project. Every kind of help " +
      "is welcome — writing code, reporting problems or spreading the word.",
    repoTitle: "Open source",
    repoBody:
      "The code lives on GitHub under the MIT license. Clone it, review it " +
      "and send your improvements through a pull request.",
    repoCta: "View on GitHub",
    apiTitle: "Open API",
    apiBody:
      "PrintForHelp runs on a FastAPI backend, and its API is open so other " +
      "developers can build on top of it and make the contribution even " +
      "bigger. The goal is always to share information about the people who " +
      "need help: many endpoints are public and need no authentication, while " +
      "others do require it. The API is available at {apiUrl} and its " +
      "interactive documentation (auto-generated by FastAPI) at {docsUrl}.",
    apiCta: "Explore the API docs",
    issuesTitle: "Requests, enhancements and bugs",
    issuesBody:
      "For now, you can report any request, enhancement idea or bug in two " +
      "ways: tell us in the #support channel on Discord, or — if you can — " +
      "open an issue directly on GitHub. Either way the team will see it and " +
      "follow up.",
    issuesCta: "Open an issue",
    issuesDiscordCta: "Report on Discord",
    discordTitle: "Join the community",
    discordBody:
      "We set up a Discord server to coordinate, answer questions and meet " +
      "other makers. We'd love to have you!",
    discordCta: "Join Discord",
  },
  centers: {
    title: "Collection centers",
    subtitle:
      "Drop-off points where you can take your printed parts so they reach " +
      "the people who need them.",
    register: "Register a center",
    filterByCountry: "Filter by country",
    filterByCity: "Filter by city",
    allCountries: "All countries",
    allCities: "All cities",
    countOne: "collection center",
    countOther: "collection centers",
    empty: "No collection centers match the filter.",
    verified: "Verified",
    unverified: "Not verified",
    viewDetails: "View details for",
    queueHeading: "Centers awaiting verification",
    queueDescription:
      "Registered by the community and not yet verified. Verify them to " +
      "confirm them.",
    archivedHeading: "Archived centers",
    archivedDescription:
      "Centers removed from the directory. Restore them to return them to " +
      "the public list.",
    archivedBadge: "Archived",
  },
  centerDetail: {
    back: "← Back to collection centers",
    verified: "Verified",
    unverified: "Not verified",
    address: "Address",
    viewOnMap: "View on map",
    noMapLink: "No location link",
    noMapLinkHint:
      "This center hasn't added a location link yet. Edit it to add one.",
    city: "City",
    contact: "Contact",
    hours: "Hours",
    organization: "Organization",
    orgVerified: "Verified",
    orgUnverified: "Unverified organization",
    management: "Management",
    managedIndividually: "Managed by an individual contributor",
    notes: "Notes",
    edit: "Edit center",
    clone: "Clone center",
    feedTitle: "Comments & activity",
    feedSubtitle:
      "Leave a note for the community or follow this center's activity.",
  },
  centerEdit: {
    back: "← Back to the collection center",
    title: "Edit collection center",
    subtitle:
      "Update this center's details. Changes are reflected in the " +
      "directory immediately.",
  },
  centerNew: {
    back: "← Back to collection centers",
    title: "Register a collection center",
    subtitle:
      "Add a drop-off point so the community can bring their printed parts. " +
      "No account needed: a maintainer will review it before marking it as " +
      "verified.",
    cloneTitle: "Clone a collection center",
    cloneSubtitle:
      "We start from an existing center's details. Tweak whatever differs " +
      "and register it: it is created as a brand-new, unverified center.",
  },
  centerForm: {
    title: "Register a collection center",
    description:
      'Your center will appear in the directory immediately as "Not verified" ' +
      "until a maintainer verifies it.",
    name: "Name",
    namePlaceholder: "UCAB Lab — Caracas",
    country: "Country",
    countryPlaceholder: "VE",
    city: "City",
    cityPlaceholder: "Caracas",
    address: "Address",
    addressPlaceholder: "Av. Teherán, Montalbán, Caracas",
    locationUrl: "Location link (optional)",
    locationUrlPlaceholder: "https://maps.google.com/...",
    contact: "Contact",
    contactPlaceholder: "Phone or email",
    hours: "Hours (optional)",
    hoursPlaceholder: "Mon-Fri 9-17",
    notes: "Notes (optional)",
    notesPlaceholder: "Drop-off instructions, landmarks, etc.",
    submit: "Register center",
    editTitle: "Edit collection center",
    editDescription: "Update this center's contact and drop-off information.",
    editSubmit: "Save changes",
    errorRequired: "Fill in all required fields.",
    errorOrgMembership: "You are not an active member of that organization.",
    errorNotFound: "The collection center no longer exists.",
    errorNotOwner: "Only the center's owner can archive it.",
    errorArchiveBlocked:
      "This center has open contributions and can't be archived yet.",
    errorValidation: "Check the form data and try again.",
    errorGeneric: "Could not complete the action. Please try again.",
  },
  centerVerify: {
    verify: "Verify",
    revoke: "Revoke verification",
  },
  centerArchive: {
    archive: "Archive center",
    forceArchive: "Archive center",
    confirmQuestion:
      "Archive this center? It will stop appearing in the public directory.",
    confirm: "Yes, archive",
    cancel: "Cancel",
    restore: "Restore",
  },
  shipments: {
    title: "Shipments",
    subtitle:
      "Dates on which this center dispatches the aid to where it is needed.",
    addShipment: "Add shipment",
    empty: "This center has no scheduled shipments yet.",
    noOpen: "No open shipments right now.",
    archivedHeading: "Closed or cancelled",
    date: "Shipment date",
    statusLabel: "Status",
    status: {
      receiving: "Receiving packages",
      closed: "Closed",
      cancelled: "Cancelled",
    },
    destination: "Destination",
    destinationPlaceholder: "Caracas, Venezuela",
    description: "Details",
    descriptionPlaceholder: "Shipment details (Markdown supported).",
    create: "Create shipment",
    saveChanges: "Save changes",
    cancel: "Cancel",
    edit: "Edit",
    delete: "Delete",
    viewDetails: "View shipment",
    detailBack: "← Back to",
    commentsTitle: "Comments & activity",
    commentsSubtitle:
      "Coordinate the drop-off or follow this shipment's activity.",
    errorDateRequired: "Please provide the shipment date.",
    errorNotMember: "Only the center's team can manage shipments.",
    errorNotFound: "The shipment or center no longer exists.",
    errorValidation: "Check the form and try again.",
    errorAuth: "You must be logged in to manage shipments.",
    errorGeneric: "Could not complete the action. Please try again.",
  },
  feed: {
    composerPlaceholder: "Write a comment… Markdown supported.",
    markdownHint: "Markdown supported",
    post: "Comment",
    loginToComment: "Log in to leave a comment.",
    empty: "No activity yet.",
    edited: "edited",
    save: "Save",
    cancel: "Cancel",
    edit: "Edit",
    delete: "Delete",
    actions: {
      created: "created this",
      updated: "updated this",
      status_changed: "changed the status",
      deleted: "deleted this",
      commented: "commented",
      comment_edited: "edited a comment",
      comment_deleted: "deleted a comment",
    },
    errorNotAuthor: "Only the author can edit this comment.",
    errorDeleteForbidden:
      "Only the author or a maintainer/admin can delete it.",
    errorNotFound: "The comment or target no longer exists.",
    errorEmpty: "The comment cannot be empty.",
    errorAuth: "You must be logged in to comment.",
    errorGeneric: "Could not complete the action. Please try again.",
  },
  admin: {
    pageTitle: "User management",
    pageSubtitle: "Create accounts, change roles and reset passwords.",
    createTitle: "Create account",
    createDescription: "Provision an account for a trusted contributor.",
    username: "Username",
    usernamePlaceholder: "username",
    password: "Password",
    passwordPlaceholder: "Min. 8, a letter and a number",
    role: "Role",
    rolePlaceholder: "Select a role",
    roleUser: "User",
    roleMaintainer: "Maintainer",
    roleAdmin: "Administrator",
    createSubmit: "Create account",
    createSuccess: "Account created successfully.",
    tableAriaLabel: "Users",
    colUser: "User",
    colRole: "Role",
    colStatus: "Status",
    colActions: "Actions",
    you: "(you)",
    statusActive: "Active",
    statusInactive: "Inactive",
    passwordButton: "Password",
    deactivate: "Deactivate",
    activate: "Activate",
    resetTitle: "Change password for",
    resetNewPassword: "New password",
    resetSave: "Save",
    resetClose: "Close",
    resetSuccess: "Password updated.",
    roleAriaLabel: "Role for",
    errorUsernameTaken: "That username is already taken.",
    errorWeakPassword:
      "The password must be at least 8 characters, with a letter and a number.",
    errorLockout:
      "You can't demote or deactivate the last active administrator.",
    errorUserNotFound: "The user no longer exists.",
    errorMissingCreate: "Fill in the username and password.",
    errorMissingPassword: "Enter the new password.",
    errorGeneric: "Could not complete the action. Please try again.",
  },
  meta: {
    title: "PrintForHelp — A 3D community serving those in need",
    description:
      "A coordination platform for the 3D-printing community: collection " +
      "centers, requests and tracking of parts in production.",
  },
};
