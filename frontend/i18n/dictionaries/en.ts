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
  header: {
    greeting: "Hi,",
    logout: "Log out",
    login: "Log in",
    localeAriaLabel: "Change language",
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
    footerNote:
      "We don't support new-user registration yet. Stay tuned — we'll enable " +
      "this option soon!",
    usernameLabel: "Username",
    usernamePlaceholder: "Your username",
    passwordLabel: "Password",
    passwordPlaceholder: "Your password",
    submit: "Log in",
    submitting: "Signing in…",
    errorMissing: "Enter your username and password.",
    errorInactive: "This account is inactive.",
    errorInvalid: "Incorrect username or password.",
    errorGeneric: "Could not log in. Please try again.",
  },
  about: {
    title: "About us",
    intro:
      "PrintForHelp is a non-profit community platform that connects 3D " +
      "printers with people who need humanitarian-aid parts.",
    missionTitle: "Our mission",
    missionTagline: "Coordinate aid, don't duplicate it.",
    missionBody:
      "We centralize information about collection centers, part requests and " +
      "in-progress production so the community covers demand better and nobody " +
      "prints the same thing twice.",
    focusTitle: "Initial focus",
    focusTagline: "Splints for Venezuela.",
    focusBody:
      "We're starting by coordinating the printing of medical splints for the " +
      "people affected by the June 2026 earthquake in Venezuela, aiming to " +
      "become a general hub for 3D-printed aid.",
    helpNote:
      "Want to help? For now, accounts are created by an administrator. We'll " +
      "soon enable open registration for makers and organizations.",
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
  },
  centerDetail: {
    back: "← Back to collection centers",
    verified: "Verified",
    unverified: "Not verified",
    address: "Address",
    city: "City",
    contact: "Contact",
    hours: "Hours",
    organization: "Organization",
    orgVerified: "Verified",
    orgUnverified: "Unverified organization",
    management: "Management",
    managedIndividually: "Managed by an individual contributor",
    notes: "Notes",
  },
  centerNew: {
    back: "← Back to collection centers",
    title: "Register a collection center",
    subtitle:
      "Add a drop-off point so the community can bring their printed parts. " +
      "No account needed: a maintainer will review it before marking it as " +
      "verified.",
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
    contact: "Contact",
    contactPlaceholder: "Phone or email",
    hours: "Hours (optional)",
    hoursPlaceholder: "Mon-Fri 9-17",
    notes: "Notes (optional)",
    notesPlaceholder: "Drop-off instructions, landmarks, etc.",
    submit: "Register center",
    errorRequired: "Fill in all required fields.",
    errorOrgMembership: "You are not an active member of that organization.",
    errorNotFound: "The collection center no longer exists.",
    errorValidation: "Check the form data and try again.",
    errorGeneric: "Could not complete the action. Please try again.",
  },
  centerVerify: {
    verify: "Verify",
    revoke: "Revoke verification",
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
