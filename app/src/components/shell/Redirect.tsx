"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Old links keep working: the page they named now lives somewhere else. */
export default function Redirect({ to }: { to: string }) {
  const router = useRouter();
  useEffect(() => {
    router.replace(to);
  }, [router, to]);
  return null;
}
