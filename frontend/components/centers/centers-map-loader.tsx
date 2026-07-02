"use client";

import dynamic from "next/dynamic";

// ssr: false is only allowed inside a Client Component. This file's
// only job is to be that boundary: page.tsx (a Server Component) can
// import this normally, and this file handles the client-only load.
const CentersMap = dynamic(
  () => import("@/components/centers/centers-map").then((m) => m.CentersMap),
  {
    ssr: false,
    loading: () => (
      <div className="mb-8 h-[400px] w-full animate-pulse rounded-lg border bg-muted/10" />
    ),
  },
);

export default CentersMap;