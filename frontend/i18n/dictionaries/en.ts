/** English message catalog. Typed as `Dictionary` so the compiler flags
 * any key that is missing or extra relative to the Spanish source. */

import type { Dictionary } from "./es";

export const en: Dictionary = {
  nav: {
    home: "Home",
    centers: "Centers",
    requests: "Requests",
    parts: "Parts",
    supplies: "Supplies",
    myContributions: "My Contributions",
    about: "About",
    users: "Users",
    notices: "Notices",
    ariaLabel: "Main navigation",
  },
  social: {
    githubAriaLabel: "PrintForHelp on GitHub",
    discordAriaLabel: "Join our Discord",
  },
  header: {
    greeting: "Hi,",
    makerGreeting: "Hi, Maker",
    logout: "Log out",
    login: "Log in",
    localeAriaLabel: "Change language",
    localeMenuHeading: "Choose a language",
    themeAriaLabel: "Change theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
  },
  makerPrompt: {
    title: "Welcome!",
    question:
      "Do you 3D print to help? Marking yourself as a Maker personalizes " +
      "your experience.",
    yes: "Yes, I'm a Maker",
    no: "Not for now",
    later: "Ask later",
  },
  localePrompt: {
    title: "Language",
    description: "We detected your language automatically. Want to change it?",
  },
  description: {
    showMore: "Show more",
    showLess: "Show less",
  },
  landing: {
    eyebrow: "3D Community",
    title: "PrintForHelp",
    subtitle:
      "We connect 3D printers with people who need parts, starting with " +
      "splints for those affected by the earthquake in Venezuela.",
    howItWorks: "How does it work?",
    wantToHelp: "I want to help",
    comingSoon: "Coming soon",
    featuresAriaLabel: "Main features",
    announcementsAriaLabel: "Community announcements",
    announcement: {
      tag: "Official announcement",
      priority: "Important",
      permalinkLabel: "Copy link to this announcement",
      publishedLabel: "Published:",
      title: "Print standards for the Venezuela splints",
      summary:
        "Some parts are being printed without following the recommended " +
        "standards. To make sure every splint can actually be used, " +
        "please follow these material and print guidelines.",
      materialsHeading: "Materials to use",
      materialsUse: [
        {
          label: "PLA",
          value: "Normal, Tough, + or variations, Matte, Translucent",
        },
        { label: "PETG", value: "Normal, HF, Translucent" },
      ],
      avoidHeading: "Avoid cosmetic filaments or those with additives",
      materialsAvoid: [
        {
          label: "PLA",
          value:
            "CF, GF, HT, Wood, Fluorescent, Phosphorescent, Silk, " +
            "Metal, Granite",
        },
        { label: "PETG", value: "CF, GF" },
      ],
      settingsHeading: "Print settings",
      settings: [
        { label: "Nozzle diameter", value: "0.4 mm minimum" },
        { label: "Layer height", value: "As thick as possible" },
        { label: "Walls", value: "2 minimum, or solid" },
        { label: "Infill", value: "15% Cross Hatch, or solid" },
      ],
    },
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
    howItWorksHeading: "How does it work?",
    howItWorksIntro:
      "PrintForHelp connects people who need 3D-printed parts with people who " +
      "have a printer and want to help. Here's how the process flows:",
    step1Title: "1. Someone posts a request",
    step1Body:
      "A person or organization creates a campaign (e.g. “Splints for " +
      "Venezuela”) and lists the parts and quantities that are needed.",
    step2Title: "2. Makers commit to print",
    step2Body:
      "People with a 3D printer browse the requests, choose how many parts " +
      "they can print, and log their commitment. Progress updates live.",
    step3Title: "3. Drop-off & delivery",
    step3Body:
      "Printed parts are taken to a collection center, which gathers them and " +
      "ships them to where they are needed most.",
    help: {
      heading: "I want to help",
      intro:
        "Thank you for joining the international maker effort supporting " +
        "earthquake relief in Venezuela. This page is designed to help makers " +
        "around the world quickly join existing relief efforts.",
      quakeNote:
        "On June 24, at approximately 6:30 PM local time, Venezuela was " +
        "struck by two major earthquakes measuring 7.1 and 7.5 magnitude, " +
        "occurring just 39 seconds apart and lasting more than three minutes " +
        "combined.",

      stepsHeading: "How to help",
      stepsIntro:
        "If you have a 3D printer, here is how you can start contributing " +
        "today:",

      printTitle: "1. Choose what to print",
      printBody:
        "All approved files are currently needed. Start with the parts " +
        "marked high priority, and if you're looking for something specific, " +
        "browse by tag:",
      printTags: [
        { label: "Children", href: "/parts?tag=Children" },
        { label: "Pets", href: "/parts?tag=pets" },
      ],
      printCaution:
        "Parts tagged “⚠️ Only print on request” are printed only when " +
        "someone asks for them; please don't print them ahead of time.",
      printCautionCta: "View these parts",
      printCautionHref: "/parts?tag=%E2%9A%A0%EF%B8%8FOnly+print+on+request",
      printCta: "View high-priority parts",
      printCtaHref: "/parts?tag=High+Priority",

      qualityTitle: "2. Print what you can",
      qualityBody:
        "All approved files are needed. Follow the material and print " +
        "standards so every splint can actually be used.",
      qualityCta: "View print standards",

      packTitle: "3. Package your prints",
      packBody: "Before delivering, please make sure each printed item:",
      packChecklist: [
        "Is clean and individually bagged whenever possible.",
        "Includes an identifier indicating what the item is.",
        "Includes printed instructions when sending splints.",
      ],
      packNote:
        "Each part's page includes its own instructions and printable label: " +
        "print the label, attach it to the piece, and include it in the " +
        "package.",
      packAllCta: "Browse all parts",

      deliverTitle: "4. Deliver or ship your prints",
      deliverBody:
        "Collection points are being compiled across several platforms. Find " +
        "a donation center near you. Can't find one? Check all three maps and " +
        "ask in the community groups: new centers are added every day. We are " +
        "actively working to unify collection point information across " +
        "platforms.",
      deliverCentersCta: "Find a collection center",
      mapUshahidiLabel: "Ushahidi Venezuela map",
      mapDisainLabel: "Disain map",

      noPrinterTitle: "Don't have a printer?",
      noPrinterBody: "You can still help. Volunteers are needed to:",
      noPrinterList: [
        "Organize local collections",
        "Coordinate logistics",
        "Translate information",
        "Spread awareness",
        "Donate supplies or funds",
      ],
      noPrinterCta: "Join the community",

      aboutTitle: "About this effort",
      aboutBody:
        "Makers around the world have joined together to support relief " +
        "efforts in Venezuela. The first widely adopted medical prints were " +
        "splints designed by @ostec3d, which continue to be urgently needed. " +
        "As needs on the ground evolve, additional approved files and " +
        "resources will continue to be added. Because this is an evolving " +
        "emergency, information and priorities may change rapidly, so please " +
        "check back frequently for updates.",

      communityHeading: "Help & community",
      communityIntro:
        "Join the community if you have questions, need help choosing files, " +
        "or want to coordinate donations.",
      whatsappEsTitle: "WhatsApp group (Español)",
      whatsappEsBody:
        "Coordinate with Spanish-speaking makers and centers in real time.",
      whatsappEnTitle: "WhatsApp group (English)",
      whatsappEnBody:
        "Connect with the international maker community in English.",
      discordTitle: "Discord (English)",
      discordBody:
        "Conversations, support, and coordination for the English community.",
      communityJoinCta: "Join",
    },
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
      "is welcome: writing code, reporting problems or spreading the word.",
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
      "ways: tell us in the #support channel on Discord, or, if you can, " +
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
    filterByState: "Filter by state / province / region",
    filterByCity: "Filter by city",
    filterByTag: "Filter by tag",
    filterByStatus: "Filter by status",
    allCountries: "All countries",
    allStates: "All regions",
    allCities: "All cities",
    allTags: "All tags",
    allStatuses: "All centers",
    statusReceiving: "Receiving donations",
    countOne: "collection center",
    countOther: "collection centers",
    empty: "No collection centers match the filter.",
    verified: "Verified",
    unverified: "Not verified",
    notReceiving: "Not receiving donations",
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
    backToContributions: "← Back to my contributions",
    verified: "Verified",
    unverified: "Not verified",
    privateLocation: "Request location",
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
    description: "Description",
    tags: "Tags",
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
    namePlaceholder: "UCAB Lab - Caracas",
    country: "Country",
    countryPlaceholder: "VE",
    state: "State / Province / Region",
    statePlaceholder: "e.g. Miranda, California, Lima",
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
    descriptionLabel: "Description (optional, Markdown supported)",
    descriptionPlaceholder:
      "Drop-off instructions, landmarks, etc. Markdown supported.",
    tags: "Tags (optional)",
    submit: "Register center",
    editTitle: "Edit collection center",
    editDescription: "Update this center's contact and drop-off information.",
    editSubmit: "Save changes",
    errorRequired: "Fill in all required fields.",
    errorOrgMembership: "You are not an active member of that organization.",
    errorNotFound: "The collection center no longer exists.",
    errorNotOwner: "Only the center's owner can archive it.",
    errorNotMember: "You don't have permission to change this center's status.",
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
  resourceArchive: {
    heading: "Danger zone",
    hintPart: "Archiving removes the part from the catalog.",
    hintSupply: "Archiving removes the supply from the catalog.",
    archivePart: "Archive part",
    archiveSupply: "Archive supply",
    confirmPart: "Archive this part? It will stop appearing in the catalog.",
    confirmSupply:
      "Archive this supply? It will stop appearing in the catalog.",
    confirm: "Yes, archive",
    cancel: "Cancel",
    errorBlocked:
      "Can't archive: open requests still use it. Close them first.",
    errorGeneric: "Could not archive. Please try again.",
  },
  centerStatus: {
    markInactive: "Mark: not receiving donations",
    markActive: "Mark: receiving donations",
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
    copyLink: "Copy link",
    linkCopied: "Link copied",
    actions: {
      created: "created this",
      updated: "updated this",
      status_changed: "changed the status",
      item_added: "added an item",
      deleted: "deleted this",
      commented: "commented",
      comment_edited: "edited a comment",
      comment_deleted: "deleted a comment",
    },
    // Action labels for commitment events on a request item's timeline.
    itemActions: {
      created: "committed to print",
      status_changed: "updated their commitment",
    },
    commitmentStatus: {
      claimed: "Committed",
      prepared: "Printed",
      delivered: "Delivered",
      received: "Received at center",
      released: "Released",
    },
    commitmentUnit: "pcs",
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
  parts: {
    title: "Part catalog",
    subtitle:
      "Printable designs the community can use in aid campaigns. Each part " +
      "links to the file to download and print.",
    register: "Add part",
    empty: "There are no parts in the catalog yet.",
    search: "Search",
    searchPlaceholder: "Search by name…",
    filterByTag: "Filter by tag",
    allTags: "All tags",
    download: "Download file",
    discontinued: "Discontinued",
    viewDetails: "View details of",
  },
  partNew: {
    back: "← Back to the catalog",
    title: "Add a part",
    subtitle:
      "Register a printable design so it can be requested in aid campaigns.",
  },
  partDetail: {
    back: "← Back to the catalog",
    backToContributions: "← Back to my contributions",
    backToItem: "Back to",
    download: "Download file",
    descriptionHeading: "Description",
    edit: "Edit part",
    discontinued: "Discontinued",
    // Provider-aware call to action for the source link (the file lives on
    // an external site, not on PrintForHelp).
    sourceLinks: {
      self: "Download file",
      makerworld: "Take me to MakerWorld",
      googledrive: "Take me to Google Drive",
      thingiverse: "View on Thingiverse",
      printables: "View on Printables",
      thangs: "View on Thangs",
      cults3d: "View on Cults3D",
      github: "View on GitHub",
      dropbox: "Open in Dropbox",
      onedrive: "Open in OneDrive",
      default: "Open download link",
    },
    feedTitle: "Comments & activity",
    feedSubtitle:
      "Leave a note for the community or follow this part's activity.",
  },
  partEdit: {
    back: "← Back to the part",
    title: "Edit part",
    subtitle:
      "Update this part's name, links, description (Markdown), and tags.",
  },
  partForm: {
    title: "Add part",
    description: "The part becomes available in the catalog for requests.",
    name: "Name",
    namePlaceholder: "Wrist splint",
    chooseFile: "Choose file",
    noFile: "No file chosen",
    sourceFile: "Upload the file",
    sourceFileHint:
      "STL, 3MF, OBJ, STEP, ZIP… up to 100 MB. Hosted on PrintForHelp.",
    sourceUrl: "Or paste a link if the file is already hosted elsewhere",
    sourceUrlPlaceholder: "https://www.thingiverse.com/thing:123",
    currentFile: "Current file",
    imageUpload: "Upload image (optional)",
    imageUploadHint: "PNG, JPEG, or WebP, up to 5 MB.",
    currentImage: "Current image",
    image: "Or paste an image URL",
    imagePlaceholder: "https://…/photo.png",
    labelUpload: "Upload print label (optional)",
    labelUploadHint:
      'An image (e.g. a "Medical donation" banner) you can print above ' +
      "the QR. PNG, JPEG, or WebP, up to 5 MB.",
    currentLabel: "Current label",
    label: "Or paste a label URL",
    labelPlaceholder: "https://…/label.png",
    descriptionLabel: "Description (optional)",
    descriptionPlaceholder: "Suggested material, print notes, etc.",
    tags: "Tags (optional)",
    submit: "Add part",
    editTitle: "Edit part",
    editSubmit: "Save changes",
    errorRequired: "Provide a name and a download link or a file.",
    errorOrgMembership: "You are not an active member of that organization.",
    errorValidation: "Check the form fields and try again.",
    errorImageTooLarge: "The image exceeds the maximum allowed size (5 MB).",
    errorImageInvalid: "The file is not a valid image (PNG, JPEG, or WebP).",
    errorFileTooLarge: "The file exceeds the maximum allowed size (100 MB).",
    errorFileType: "Unsupported file type. Use STL, 3MF, OBJ, STEP, or ZIP.",
    errorGeneric: "The action could not be completed. Please try again.",
  },
  supplies: {
    title: "Supplies catalog",
    subtitle:
      "Non-printed items the community can contribute to relief campaigns: " +
      "medicine, water, food, and more.",
    register: "Add supply",
    empty: "No supplies in the catalog yet.",
    search: "Search",
    searchPlaceholder: "Search by name…",
    filterByTag: "Filter by tag",
    allTags: "All tags",
    units: "Units",
    discontinued: "Discontinued",
    viewDetails: "View details for",
  },
  supplyNew: {
    back: "← Back to the catalog",
    title: "Add a supply",
    subtitle:
      "Register a non-printed item so it can be requested in relief " +
      "campaigns.",
  },
  supplyDetail: {
    back: "← Back to the catalog",
    backToContributions: "← Back to my contributions",
    backToItem: "Back to",
    descriptionHeading: "Description",
    edit: "Edit supply",
    discontinued: "Discontinued",
    units: "Units",
    feedTitle: "Comments & activity",
    feedSubtitle:
      "Leave a note for the community or follow this supply's activity.",
  },
  supplyEdit: {
    back: "← Back to the supply",
    title: "Edit supply",
    subtitle: "Update this supply's name, unit, image, description, and tags.",
  },
  supplyForm: {
    title: "Add supply",
    description:
      "The supply will be available in the catalog to use in requests.",
    name: "Name",
    namePlaceholder: "Drinking water",
    units: "Units of measure (optional)",
    unitsHint:
      "Add the suggested units for this supply (e.g. liters, kg, boxes). " +
      "Whoever makes a request can pick one or add another.",
    chooseFile: "Choose file",
    noFile: "No file selected",
    imageUpload: "Upload image (optional)",
    imageUploadHint: "PNG, JPEG, or WebP, up to 5 MB.",
    currentImage: "Current image",
    image: "Or paste an image URL",
    imagePlaceholder: "https://…/photo.png",
    descriptionLabel: "Description (optional)",
    descriptionPlaceholder: "Presentation, suggested quantity, notes, etc.",
    tags: "Tags (optional)",
    submit: "Add supply",
    editTitle: "Edit supply",
    editSubmit: "Save changes",
    errorRequired: "Enter the supply name.",
    errorOrgMembership: "You are not an active member of that organization.",
    errorValidation: "Check the form fields and try again.",
    errorImageTooLarge: "The image exceeds the maximum allowed size (5 MB).",
    errorImageInvalid: "The file is not a valid image (PNG, JPEG, or WebP).",
    errorGeneric: "The action could not be completed. Please try again.",
  },
  requests: {
    title: "Requests",
    subtitle:
      "Campaigns for parts the community needs to print. Each campaign " +
      "groups several parts with their progress.",
    register: "Create request",
    empty: "There are no open requests right now.",
    status: {
      open: "Open",
      fulfilled: "Fulfilled",
      closed: "Closed",
    },
    itemsCount: "parts",
    viewDetails: "View details of",
    lastActivity: "Last activity",
    noActivity: "No recent activity",
  },
  requestNew: {
    back: "← Back to requests",
    title: "Create a request",
    subtitle:
      "Create a campaign and add the parts that are needed, with a target " +
      "quantity for each one.",
  },
  requestForm: {
    title: "New request",
    description: "Group one or more parts into an aid campaign.",
    campaignTitle: "Campaign title",
    campaignTitlePlaceholder: "Splints for Venezuela 2026",
    descriptionLabel: "Description (optional)",
    descriptionPlaceholder: "Campaign context (Markdown supported).",
    imageUpload: "Upload image (optional)",
    imageUploadHint: "PNG, JPEG, or WebP, up to 5 MB.",
    currentImage: "Current image",
    imageUrl: "Or paste an image URL",
    imageUrlPlaceholder: "https://…/photo.png",
    deadline: "Deadline (optional)",
    afterCreateHint:
      "After creating the request you can add the parts and supplies that " +
      "are needed.",
    itemsHeading: "Parts (optional)",
    itemsHint: "Add them now or add them to the request later.",
    itemPart: "Part",
    itemKind: "Type",
    itemKindBoth: "Parts and supplies",
    itemKindParts: "Parts only",
    itemKindSupplies: "Supplies only",
    itemResource: "Item",
    itemUnit: "Unit",
    itemUnitPlaceholder: "e.g. liters",
    preferredCenters: "Preferred drop-off centers (optional)",
    preferredCentersHint:
      "If you pick one or more, helpers will only see these centers when " +
      "delivering their contributions.",
    preferredCentersEmpty: "No verified centers are available yet.",
    privateCenterTag: "private",
    addLocation: "+ Add a private location",
    addLocationHint:
      "Register a drop-off point just for this request. It won't appear in " +
      "the Collection Centers directory, but it will be visible to people " +
      "helping with this request.",
    addLocationSubmit: "Add location",
    locationName: "Name",
    locationContact: "Contact",
    locationAddress: "Address",
    locationCity: "City",
    locationCountry: "Country",
    locationMapUrl: "Location link (optional)",
    locationHours: "Hours (optional)",
    locationErrorRequired:
      "Enter the location's name, address, country, city, and contact.",
    cancel: "Cancel",
    itemQuantity: "Quantity (optional)",
    addItem: "Add another part",
    addItemSubmit: "Add part",
    removeItem: "Remove",
    noParts:
      "No parts in the catalog yet. Create the request and add them later.",
    submit: "Create request",
    editTitle: "Edit request",
    editSubmit: "Save changes",
    alreadyAdded: "already added",
    errorRequired: "Provide a title for the request.",
    errorDuplicatePart: "That part is already in the request.",
    errorPartDiscontinued: "One of the parts is no longer available.",
    errorPartNotFound: "One of the selected parts no longer exists.",
    errorValidation: "Check the form fields and try again.",
    errorImageTooLarge: "The image exceeds the maximum allowed size (5 MB).",
    errorImageInvalid: "The file is not a valid image (PNG, JPEG, or WebP).",
    errorGeneric: "The action could not be completed. Please try again.",
  },
  requestEdit: {
    back: "← Back to the request",
    title: "Edit request",
    subtitle:
      "Update the campaign's title, description (Markdown), and deadline.",
  },
  requestDetail: {
    back: "← Back to requests",
    backToContributions: "← Back to my contributions",
    backToItem: "Back to",
    deadline: "Deadline",
    noDeadline: "No deadline",
    edit: "Edit",
    close: "Close request",
    closeItem: "Close",
    removeItem: "Remove",
    editTargetLabel: "Target",
    saveTarget: "Save target",
    addPartHeading: "Add an item",
    itemsHeading: "Requested items",
    progressClaimed: "Claimed",
    progressAtCenter: "At center",
    progressRemaining: "Remaining",
    created: "Created",
    target: "Target",
    openEnded: "No fixed target",
    itemClosed: "Closed",
    itemFulfilled: "Fulfilled",
    viewItem: "View details & comments →",
    feedTitle: "Comments & activity",
    feedSubtitle:
      "Leave a note for the community or follow this request's activity.",
  },
  requestItem: {
    back: "← Back to the request",
    target: "Target",
    openEnded: "No fixed target",
    progressClaimed: "Claimed",
    progressAtCenter: "At center",
    progressRemaining: "Remaining",
    created: "Created",
    lastActivity: "Last activity",
    whoHeading: "Who is making the request?",
    whatHeading: "What are they requesting?",
    centersHeading: "Drop-off centers for this item",
    centersDirections: "Get directions",
    centersEdit: "Edit centers",
    centersEditHint:
      "Check only the centers where this item is needed. If you check none, " +
      "all of the request's preferred centers are used.",
    centersSave: "Save centers",
    centersCancel: "Cancel",
    centersSaved: "Centers updated!",
    viewCampaign: "View the full request",
    viewPart: "View the part",
    requestedBy: "Requested by",
    communityRequest: "Community request",
    orgUnverified: "Unverified organization",
    itemFulfilled: "Fulfilled",
    itemClosed: "Closed",
    shareHint:
      "Share this link so more people can see the progress and help out.",
    commitmentsTitle: "Commitments",
    commitmentsSubtitle:
      "People who have already committed to print this part.",
    commitmentsEmpty: "No one has committed yet. Be the first!",
    commitmentUnit: "pcs",
    commitmentStatus: {
      claimed: "Committed",
      prepared: "Printed",
      delivered: "Delivered",
      received: "Received at center",
      released: "Released",
    },
    feedTitle: "Comments & activity",
    feedSubtitle:
      "Coordinate or comment on this part. Anyone can follow the progress.",
    filters: {
      all: "All",
      needs_help: "Needs help",
      committed: "Committed",
      completed: "Completed",
    },
    helpState: {
      needs_help: "Needs help",
      committed: "Committed",
      completed: "Completed",
    },
    filterEmpty:
      "It looks like nothing needs help on this request right now. Watch it " +
      "to get notified if more help is needed.",
    filterEmptyLogin: "Log in to watch this request",
  },
  claim: {
    title: "I want to print this part",
    heading: "Would you like to contribute?",
    subtitle: "Enter below how many parts you can print.",
    quantity: "Quantity",
    centerLater:
      "You'll pick the drop-off collection center later, from “My " +
      "Contributions”, before marking it delivered.",
    submit: "Commit to print",
    loginToClaim: "Log in to commit to printing.",
    success: "Done! Your commitment shows up under “My Contributions”.",
  },
  myContributions: {
    title: "My Contributions",
    subtitle: "The parts you committed to print and their current status.",
    empty: "You haven't committed to print any part yet.",
    fromRequest: "Request:",
    quantity: "Quantity",
    statusLabel: "Status",
    filterByPart: "Part",
    allParts: "All parts",
    filterByRequest: "Request",
    allRequests: "All requests",
    allStatuses: "All statuses",
    filterByTag: "Tag",
    allTags: "All tags",
    filteredEmpty: "No contributions match the filters.",
    status: {
      claimed: "Claimed",
      prepared: "Printed",
      delivered: "Delivered",
      received: "Received",
      released: "Released",
    },
    statusFilter: {
      claimed: "Waiting for print",
      prepared: "Waiting for drop-off",
      delivered: "Delivered",
      received: "Received",
      released: "Released",
    },
    markPrinted: "Mark as printed",
    markDelivered: "Mark as delivered",
    confirmReceived: "Confirm receipt",
    release: "Release",
    autoReceived: "Auto-received",
    dropOffAt: "Drop-off:",
    getDirections: "Get directions",
    noCenterYet: "No drop-off center yet",
    noCentersYet: "No verified centers available yet.",
    setCenterLabel: "Drop-off collection center",
    setCenter: "Set center",
    changeCenter: "Change center",
    changeCenterPrompt: "Change drop-off center?",
    centerUpdated: "Updated!",
    cancel: "Cancel",
    tagsLabel: "Tags",
    addTags: "Add tags",
    editTags: "Edit tags",
    saveTags: "Save tags",
    tagsHelpLabel: "About tags",
    tagsHelp:
      "Tags are personal and unique to you: use them to organize and easily filter your contributions (e.g. by material, urgency, or batch).",
    trackingSetup: "Set up tracking",
    trackingView: "View tracking",
  },
  tracking: {
    pageTitle: "Item tracking",
    backToContributions: "Back to my contributions",
    summaryQuantity: "Quantity",
    summaryStatus: "Status",
    groupLabel: "Group",
    itemLabel: "Item",
    generateTitle: "You haven't generated tracking yet",
    generateDescription:
      "Generate one QR code for the group and one per part. Print them and stick them on each item so anyone can view and add updates by scanning.",
    generateButton: "Generate QR codes",
    settingsTitle: "Who can see this tracking",
    visibilityLabel: "Visibility",
    visibilityPrivate: "Private (only you)",
    visibilityGroup: "Group of users",
    visibilityPublic: "Public (anyone with the link)",
    visibilityHelp:
      "Private: only you and admins. Group: also the users you add by username. Public: anyone with the link or QR.",
    membersLabel: "Users with access",
    membersHelp:
      "Search and add the users allowed to view this tracking when visibility is “Group of users”.",
    membersSearchPlaceholder: "Search for a user…",
    membersNoResults: "No users found.",
    saveSettings: "Save changes",
    settingsSaved: "Changes saved!",
    shareTitle: "Shareable link",
    shareHintPublic:
      "Anyone with this link (or the group QR) can view and add updates without logging in.",
    shareHintGroup:
      "Only the users you added can open this link, and only while logged in.",
    sharePrivateNote:
      "This tracking is private: only you and admins can see it. Switch visibility to “Group” or “Public” to share it.",
    shareCopy: "Copy link",
    shareCopied: "Copied!",
    messageLabel: "Message from contributor (optional)",
    messagePlaceholder:
      'Write a message for whoever receives the part, e.g. "With love, the ' +
      'PrintForHelp community".',
    messageHelp:
      "If you write a message it is printed above each QR in the download " +
      "(max 100 characters). Leave it empty and no message is included.",
    messageCharsLeft: "characters left",
    savedMessagesHint: "Click a message you've used before to reuse it here:",
    deleteMessageAria: "Delete saved message",
    rememberMessage: "Remember my message",
    rememberMessageTooltip:
      "Save this message to your list to reuse on any tracking. You don't " +
      "need to save it to include it in this download.",
    qrTitle: "QR codes",
    qrDescription:
      "Download every QR in a single file to print, or grab each one individually.",
    includeLabel: "Include the part label",
    downloadPdf: "Download PDF with all QRs",
    downloadPng: "Download PNG with all QRs",
    downloadQr: "Download QR",
    openPublicPage: "Open public page",
    timelineTitle: "Updates",
    timelineEmpty: "No updates yet.",
    copyUpdateLink: "Copy link",
    updateLinkCopied: "Link copied",
    showItemUpdates: "Also show updates for each individual item",
    anonymous: "Anonymous",
    addUpdateTitle: "Add an update",
    descriptionLabel: "Description",
    descriptionPlaceholder: "What happened to this item?",
    tagsLabel: "Tags",
    postAnonymously: "Post anonymously",
    guestNote: "You are not logged in: your update will show as anonymous.",
    submitUpdate: "Post update",
    updatePosted: "Update posted!",
    editTags: "Edit tags",
    addTags: "Add tags",
    saveTags: "Save",
    cancel: "Cancel",
    privateTitle: "This tracking is private",
    privateBody:
      "Whoever created this tracking hasn't made it public. Log in if you have access.",
    notFoundTitle: "Tracking not found",
    notFoundBody: "This link doesn't match any tracked item.",
    errorForbidden: "You don't have access to this tracking.",
    errorAlreadyExists: "This contribution already has tracking.",
    errorEditForbidden: "You can't edit this update.",
    errorDescriptionRequired: "Write a description.",
    errorValidation: "Check the details and try again.",
    errorGeneric: "Something went wrong. Please try again.",
  },
  tagInput: {
    placeholder: "Type and press Enter…",
    removeLabel: "Remove",
    createLabel: "Create",
  },
  contributions: {
    errorRequired: "Enter a valid quantity.",
    errorCenterUnavailable:
      "That center must be verified and active to receive parts.",
    errorCenterRequired: "Add a drop-off center before marking as delivered.",
    errorItemClosed: "This part no longer accepts new commitments.",
    errorInvalidTransition: "The status cannot change from its current value.",
    errorNotMaker: "Only the person who committed can advance this part.",
    errorNotReceiver: "Only the center team can confirm receipt.",
    errorValidation: "Check the fields and try again.",
    errorGeneric: "The action could not be completed. Please try again.",
  },
  meta: {
    title: "PrintForHelp: A 3D community serving those in need",
    description:
      "A coordination platform for the 3D-printing community: collection " +
      "centers, requests and tracking of parts in production.",
  },
  markdownEditor: {
    write: "Write",
    preview: "Preview",
    attach: "Attach images",
    attachHint: "Paste, drop, or select an image to upload.",
    uploadingHint: "Uploading image…",
    uploading: "Uploading",
    previewEmpty: "Nothing to preview.",
    errors: {
      AUTH: "You must be signed in to upload images.",
      NO_FILE: "No image selected.",
      INVALID_IMAGE: "That file isn't a valid image.",
      IMAGE_TOO_LARGE: "The image is too large.",
      UPLOAD: "Couldn't upload the image.",
      default: "Couldn't upload the image.",
    },
  },
  notifications: {
    ariaLabel: "Notifications",
    title: "Notifications",
    empty: "You have no notifications.",
    loading: "Loading…",
    markAllRead: "Mark all as read",
    summary: {
      mentioned: "mentioned you",
      commented: "commented",
      statusChanged: "changed the status",
      itemAdded: "added an item",
      trackingUpdate: "posted a tracking update",
      updated: "updated",
    },
  },
  watch: {
    watch: "Watch",
    watching: "Watching",
    watchAria: "Watch to receive notifications",
    unwatchAria: "Stop watching",
    watchTooltip:
      "Interested in this item? Start watching it to get notifications " +
      "about changes, comments, and more.",
    watchingTooltip:
      "You're watching this item. Click to stop getting notifications " +
      "about it.",
    error: "Couldn't update. Please try again.",
  },
  mentions: {
    loading: "Searching…",
    empty: "No matches",
  },
  notices: {
    // Banner
    showHidden: "Show hidden notices",
    dismiss: "Dismiss notice",
    // Admin tab
    pageTitle: "Site notices",
    pageSubtitle:
      "Publish page banners and review notice requests from the owners of " +
      "parts, centers, and requests.",
    queueTitle: "Pending requests",
    queueDescription:
      "Notices requested by an item's owner. They stay hidden until you " +
      "approve them.",
    queueEmpty: "No pending requests.",
    createTitle: "Create page banner",
    createDescription:
      "Shows on the pages you pick. Write the message in every language you " +
      "need (English is the default).",
    listTitle: "Active notices",
    listEmpty: "No notices yet.",
    severityLabel: "Severity",
    severityInfo: "Information",
    severitySuccess: "Success",
    severityWarning: "Warning",
    severityCritical: "Critical",
    scopesLabel: "Pages",
    scopeAll: "All",
    scopeHome: "Home",
    scopeCenters: "Centers",
    scopeRequests: "Requests",
    scopeParts: "Parts",
    scopeMyContributions: "My Contributions",
    scopeAbout: "About",
    // Translations editor
    languageLabel: "Language",
    titleLabel: "Title (optional)",
    messageLabel: "Message",
    actionLabelLabel: "Button text (optional)",
    actionUrlLabel: "Button link (optional)",
    messagePlaceholder: "Write the notice (plain text).",
    actionUrlPlaceholder: "https://…",
    addLanguage: "Add language",
    removeLanguage: "Remove language",
    // Table
    colMessage: "Notice",
    colSeverity: "Severity",
    colTarget: "Scope",
    colStatus: "Status",
    colLanguages: "Languages",
    colCreated: "Created",
    colActions: "Actions",
    statusPending: "Pending",
    statusApproved: "Approved",
    statusDeclined: "Declined",
    enabledOn: "Visible",
    enabledOff: "Hidden",
    enable: "Enable",
    disable: "Disable",
    approve: "Approve",
    decline: "Decline",
    edit: "Edit",
    editTitle: "Edit notice",
    save: "Save changes",
    updateSuccess: "Notice updated.",
    delete: "Delete",
    targetPage: "Pages",
    targetResource: "Part",
    targetCollectionCenter: "Center",
    targetRequest: "Request",
    requestedBy: "Requested by",
    // Entity request control
    requestTitle: "Request a notice",
    requestButton: "Request notice",
    requestDescriptionOwner:
      "Your notice will be sent for review and stays hidden until a " +
      "moderator approves it.",
    requestDescriptionMaintainer:
      "As a moderator, your notice is published on this item right away.",
    submit: "Submit",
    cancel: "Cancel",
    requestSuccessPending: "Notice submitted. It is pending approval.",
    requestSuccessApproved: "Notice published.",
    createSuccess: "Banner created.",
    // Errors
    errorMessageRequired: "Write the message in every language.",
    errorScopesRequired: "Pick at least one page.",
    errorAuth: "You must be signed in to request a notice.",
    errorNotOwner: "You can only request a notice on an item you manage.",
    errorNotFound: "The notice no longer exists.",
    errorNotPending: "This notice has already been reviewed.",
    errorTranslationsRequired: "Add at least one language.",
    errorDuplicateLanguage: "Two translations share the same language.",
    errorInvalidMode: "Invalid notice configuration.",
    errorValidation: "Check the form and try again.",
    errorGeneric: "Couldn't complete the action. Try again.",
  },
};
