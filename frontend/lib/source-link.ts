/**
 * Detect which external host a Resource's `source_url` points at, so the UI
 * can show a provider-aware call to action (e.g. "Take me to MakerWorld")
 * instead of a generic "Download" that implies we host the file.
 *
 * The returned key indexes `dict.partDetail.sourceLinks`.
 */

export type SourceProvider =
  | "self"
  | "makerworld"
  | "googledrive"
  | "thingiverse"
  | "printables"
  | "thangs"
  | "cults3d"
  | "github"
  | "dropbox"
  | "onedrive"
  | "default";

export function sourceProvider(url: string): SourceProvider {
  // Files uploaded to PrintForHelp are served under /media/files/ — these
  // are a genuine direct download from us, not an off-site link. The URL
  // may be relative (/media/files/...) or absolute, so match the string
  // before attempting to parse it as an absolute URL.
  if (url.includes("/media/files/")) {
    return "self";
  }
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return "default";
  }
  const host = parsed.hostname.toLowerCase();
  const has = (needle: string) =>
    host === needle || host.endsWith(`.${needle}`);
  if (has("makerworld.com")) return "makerworld";
  if (has("drive.google.com") || has("docs.google.com")) return "googledrive";
  if (has("thingiverse.com")) return "thingiverse";
  if (has("printables.com")) return "printables";
  if (has("thangs.com")) return "thangs";
  if (has("cults3d.com")) return "cults3d";
  if (has("github.com") || has("githubusercontent.com")) return "github";
  if (has("dropbox.com")) return "dropbox";
  if (has("1drv.ms") || has("onedrive.live.com")) return "onedrive";
  return "default";
}
